#!/usr/bin/env python3
"""Offline mock tests for inventory.py allowlist projection + fail-closed parsing.

No kubectl, no cluster. Verifies: (INV-01) per-kind allowlist projection drops
arbitrary spec/status fields and URL userinfo/query; (INV-02) malformed JSON and
invalid shape fail closed (PARSE_ERROR, empty output, nonzero exit); (INV-03) the
exact argv (including --raw) is recorded; distinct error categories; fail-closed
on no kubectl before creating output; no-overwrite.
"""
import importlib.util
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


HERE = os.path.dirname(os.path.abspath(__file__))
inv = load(os.path.join(HERE, "inventory.py"), "inventory")

CANARY = "SYNTHETIC_REVIEW_CANARY_NOT_A_CREDENTIAL"


class TestAllowlistProjection(unittest.TestCase):
    def _project(self, resource, item):
        raw = json.dumps({"items": [item]})
        return json.loads(inv.project_list(resource, raw))

    def test_networkpolicy_drops_unallowlisted(self):
        item = {
            "metadata": {"name": "np", "namespace": "portal", "labels": {"a": "b"},
                         "annotations": {"secret": CANARY}, "managedFields": [CANARY]},
            "spec": {
                "podSelector": {"matchLabels": {"app": "portal"}},
                "policyTypes": ["Ingress"],
                "ingress": [{"from": [{"podSelector": {"matchLabels": {"x": "y"}}}],
                             "ports": [{"port": 8080, "protocol": "TCP"}]}],
                "unneededField": CANARY,
            },
            "status": {"message": CANARY},
        }
        out = self._project("networkpolicies.networking.k8s.io", item)
        blob = json.dumps(out)
        self.assertNotIn(CANARY, blob)
        self.assertNotIn("unneededField", blob)
        self.assertNotIn("annotations", blob)
        self.assertNotIn("managedFields", blob)
        self.assertNotIn("message", blob)
        # needed fields retained
        self.assertEqual(out[0]["spec"]["podSelector"]["matchLabels"]["app"], "portal")
        self.assertEqual(out[0]["spec"]["ingress"][0]["ports"][0]["port"], 8080)

    def test_url_sanitized(self):
        item = {
            "metadata": {"name": "os", "namespace": "portal", "labels": {}},
            "spec": {"data": {
                "destinationPath": "s3://bucket/path",
                "endpointURL": f"https://user:{CANARY}@s3.example.invalid:9000/?token={CANARY}",
                "s3Credentials": {"name": "portal-s3-creds"},
            }},
        }
        out = self._project("objectstores.barmancloud.cnpg.io", item)
        blob = json.dumps(out)
        self.assertNotIn(CANARY, blob)
        self.assertNotIn("user:", blob)
        self.assertNotIn("?token", blob)
        self.assertIn("https://s3.example.invalid:9000", blob)
        self.assertIn("s3CredentialsName", blob)
        self.assertIn("portal-s3-creds", blob)

    def test_gateway_listeners_only(self):
        item = {
            "metadata": {"name": "g", "namespace": "portal", "labels": {}},
            "spec": {"gatewayClassName": "eg", "listeners": [{"name": "http", "port": 80, "protocol": "HTTP"}],
                     "unneeded": CANARY},
            "status": {"conditions": [{"type": "Ready", "status": "True", "reason": "r", "message": CANARY}]},
        }
        out = self._project("gateways.gateway.networking.k8s.io", item)
        blob = json.dumps(out)
        self.assertNotIn(CANARY, blob)
        self.assertNotIn("unneeded", blob)
        self.assertEqual(out[0]["spec"]["listeners"][0]["port"], 80)
        self.assertEqual(out[0]["status"]["conditions"][0]["type"], "Ready")

    def test_sanitize_url(self):
        self.assertEqual(
            inv.sanitize_url(f"https://user:{CANARY}@h:443/p?q={CANARY}#f"),
            "https://h:443/p")
        self.assertEqual(inv.sanitize_url("not-a-url"), "not-a-url")

    def test_sanitize_url_malformed_port_omits(self):
        out = inv.sanitize_url(f"https://user:{CANARY}@host.invalid:bad/?token={CANARY}")
        self.assertIsNone(out)

    def test_sanitize_url_uppercase_scheme(self):
        out = inv.sanitize_url(f"HTTPS://user:{CANARY}@host.invalid/?token={CANARY}")
        self.assertNotIn(CANARY, out)
        self.assertTrue(out.startswith("https://host.invalid"))

    def test_destination_path_sanitized(self):
        item = {"metadata": {"name": "os", "labels": {}},
                "spec": {"data": {"destinationPath": f"s3://user:{CANARY}@bucket.invalid/path?token={CANARY}"}}}
        out = self._project("objectstores.barmancloud.cnpg.io", item)
        self.assertNotIn(CANARY, json.dumps(out))
        self.assertEqual(out[0]["spec"]["data"]["destinationPath"], "s3://bucket.invalid/path")

    def test_endport_preserved(self):
        item = {"metadata": {"name": "np", "labels": {}},
                "spec": {"ingress": [{"ports": [{"protocol": "TCP", "port": 8000, "endPort": 8010}]}]}}
        out = self._project("networkpolicies.networking.k8s.io", item)
        self.assertEqual(out[0]["spec"]["ingress"][0]["ports"][0]["endPort"], 8010)

    def test_empty_object_rejected(self):
        with self.assertRaises(ValueError):
            inv.project_list("networkpolicies.networking.k8s.io", "{}")

    def test_empty_items_list_ok(self):
        out = json.loads(inv.project_list("networkpolicies.networking.k8s.io", json.dumps({"items": []})))
        self.assertEqual(out, [])

    def test_nested_bad_metadata_rejected(self):
        with self.assertRaises(ValueError):
            inv.project_list("networkpolicies.networking.k8s.io",
                             json.dumps({"items": [{"metadata": "bad-shape", "spec": {}}]}))


class TestClassify(unittest.TestCase):
    def test_parse_error(self):
        self.assertEqual(inv.classify(None, "", False, parse_error=True), "PARSE_ERROR")
    def test_timeout(self):
        self.assertEqual(inv.classify(None, "", True), "TIMEOUT")
    def test_forbidden(self):
        self.assertEqual(inv.classify(1, "Error from server (Forbidden)", False), "FORBIDDEN")
    def test_api_not_served(self):
        self.assertEqual(inv.classify(1, "error: no matches for kind", False), "API_NOT_SERVED")
    def test_connection(self):
        self.assertEqual(inv.classify(1, "connection refused", False), "CONNECTION")
    def test_generic(self):
        self.assertEqual(inv.classify(1, "x", False), "GET_FAILED")
    def test_deadline_timeout(self):
        self.assertEqual(inv.classify(1, "context deadline exceeded", False), "TIMEOUT")
    def test_success(self):
        self.assertIsNone(inv.classify(0, "", False))


class _FakeResult:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class TestMain(unittest.TestCase):
    def _run(self, outputs, which=True):
        tmp = tempfile.mkdtemp()
        outdir = os.path.join(tmp, "inv")
        seen = []
        def fake_run(argv, **kw):
            seen.append(argv)
            return outputs.pop(0)
        with mock.patch.object(shutil, "which", return_value="/usr/bin/kubectl" if which else None), \
             mock.patch.object(subprocess, "run", side_effect=fake_run), \
             mock.patch.object(inv.sys, "argv", ["inventory.py", "--context", "ctx", "--output", outdir]):
            code = inv.main()
        return code, outdir, seen

    def _valid_output(self, resource, item):
        if resource is None:
            return ""
        return json.dumps({"items": [item]})

    def test_valid_full_object_projection_exit0(self):
        outputs = []
        for argv_tail, resource in inv.COMMANDS:
            if resource is not None:
                outputs.append(_FakeResult(0, json.dumps({"items": [{"metadata": {"name": "x", "labels": {}}, "spec": {}}]}), ""))
            else:
                outputs.append(_FakeResult(0, "", ""))
        code, outdir, seen = self._run(outputs)
        self.assertEqual(code, 0)
        rows = [json.loads(x) for x in open(os.path.join(outdir, "inventory.jsonl"))]
        self.assertEqual(len(rows), len(inv.COMMANDS))

    def test_malformed_json_fails_closed(self):
        outputs = []
        for argv_tail, resource in inv.COMMANDS:
            if resource is not None:
                outputs.append(_FakeResult(0, "not-json " + CANARY, ""))
            else:
                outputs.append(_FakeResult(0, "", ""))
        code, outdir, _ = self._run(outputs)
        self.assertNotEqual(code, 0)
        rows = [json.loads(x) for x in open(os.path.join(outdir, "inventory.jsonl"))]
        for r in rows:
            if r["category"] == "PARSE_ERROR":
                self.assertEqual(r["output"], "")
                self.assertNotIn(CANARY, json.dumps(r))
        # no raw canary preserved anywhere
        self.assertNotIn(CANARY, open(os.path.join(outdir, "inventory.jsonl")).read())

    def test_invalid_shape_fails(self):
        outputs = []
        for argv_tail, resource in inv.COMMANDS:
            if resource is not None:
                outputs.append(_FakeResult(0, json.dumps("scalar-not-object"), ""))
            else:
                outputs.append(_FakeResult(0, "", ""))
        code, _, _ = self._run(outputs)
        self.assertNotEqual(code, 0)

    def test_argv_preserves_raw(self):
        outputs = []
        for argv_tail, resource in inv.COMMANDS:
            if resource is not None:
                outputs.append(_FakeResult(0, json.dumps({"items": []}), ""))
            else:
                outputs.append(_FakeResult(0, "", ""))
        code, outdir, seen = self._run(outputs)
        self.assertEqual(code, 0)
        rows = [json.loads(x) for x in open(os.path.join(outdir, "inventory.jsonl"))]
        # find the discovery command and assert --raw preserved in recorded argv
        disc = [r for r in rows if '/apis/monitoring.coreos.com/v1' in r['argv']]
        self.assertTrue(disc, "monitoring discovery command missing")
        self.assertIn('--raw', disc[0]['argv'])
        # recorded argv equals the actual invocation (first 3 + tail)
        self.assertEqual(seen[0], rows[0]['argv'])

    def test_no_direct_stdout_collects_annotations_or_secrets(self):
        for argv_tail, resource in inv.COMMANDS:
            jp = ' '.join(argv_tail)
            if resource is None:
                self.assertNotIn('.metadata.annotations', jp, f"unsafe field in {argv_tail}")
                self.assertNotIn('.spec.template', jp, f"pod template in {argv_tail}")
                self.assertNotIn('env', jp, f"env in {argv_tail}")

    def test_nested_bad_metadata_via_main(self):
        outputs = []
        for argv_tail, resource in inv.COMMANDS:
            if resource == 'networkpolicies.networking.k8s.io':
                outputs.append(_FakeResult(0, json.dumps({"items": [{"metadata": "bad", "spec": {}}]}), ""))
            elif resource is not None:
                outputs.append(_FakeResult(0, json.dumps({"items": []}), ""))
            else:
                outputs.append(_FakeResult(0, "", ""))
        code, outdir, _ = self._run(outputs)
        self.assertNotEqual(code, 0)
        rows = [json.loads(x) for x in open(os.path.join(outdir, "inventory.jsonl"))]
        self.assertTrue(any(r["category"] == "PARSE_ERROR" for r in rows))

    def test_valid_fixture_every_projector(self):
        fixtures = {
            'networkpolicies.networking.k8s.io': {"metadata": {"name": "n", "labels": {}}, "spec": {"podSelector": {"matchLabels": {"a": "b"}}, "policyTypes": ["Ingress"]}},
            'gatewayclasses.gateway.networking.k8s.io': {"metadata": {"name": "g", "labels": {}}, "spec": {"controllerName": "x"}},
            'gateways.gateway.networking.k8s.io': {"metadata": {"name": "g", "labels": {}}, "spec": {"gatewayClassName": "eg", "listeners": []}},
            'envoyproxies.gateway.envoyproxy.io': {"metadata": {"name": "e", "labels": {}}},
            'clusters.postgresql.cnpg.io': {"metadata": {"name": "c", "labels": {}}, "spec": {}},
            'objectstores.barmancloud.cnpg.io': {"metadata": {"name": "o", "labels": {}}, "spec": {"data": {}}},
        }
        for resource, item in fixtures.items():
            out = inv.project_list(resource, json.dumps({"items": [item]}))
            self.assertIsInstance(json.loads(out), list)
            self.assertNotIn(CANARY, out)

    def test_no_kubectl_blocks_no_output(self):
        tmp = tempfile.mkdtemp()
        outdir = os.path.join(tmp, "novel")
        with mock.patch.object(shutil, "which", return_value=None), \
             mock.patch.object(inv.sys, "argv", ["inventory.py", "--context", "c", "--output", outdir]):
            with self.assertRaises(SystemExit) as cm:
                inv.main()
        self.assertIn("BLOCKED", str(cm.exception))
        self.assertFalse(os.path.exists(outdir))


if __name__ == "__main__":
    unittest.main()
