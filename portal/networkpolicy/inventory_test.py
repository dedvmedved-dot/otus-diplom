#!/usr/bin/env python3
"""Offline mock tests for inventory.py typed-output contract.

No kubectl, no cluster. Verifies: (a) per-kind allowlist projection + typed leaf
validation across all six projectors; (b) malformed scalar/container values fail
closed (PARSE_ERROR, empty output, nonzero exit, no raw content); (c) strict URL
sanitizer (origin-only, IPv6, invalid authority/type/scheme omitted); (d) exact
argv, distinct error categories, no-kubectl-before-output, no-overwrite.
"""
import copy
import importlib.util
import json
import os
from pathlib import Path
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
BAD = {"unexpected": CANARY}

KIND_BY_RESOURCE = inv.KIND_BY_RESOURCE

SPECS = {
    "NetworkPolicy": {"podSelector": {}, "policyTypes": ["Ingress"],
                      "ingress": [{"from": [{"ipBlock": {"cidr": "10.0.0.0/24", "except": []}}],
                                   "ports": [{"port": 8000, "protocol": "TCP", "endPort": 8010}]}]},
    "GatewayClass": {"controllerName": "gateway.envoyproxy.io/gatewayclass-controller"},
    "Gateway": {"gatewayClassName": "eg", "listeners": [{"name": "http", "port": 80, "protocol": "HTTP"}]},
    "EnvoyProxy": {},
    "Cluster": {"instances": 3, "storage": {"size": "10Gi"}, "walStorage": {"size": "1Gi"},
                "monitoring": {"enablePodMonitor": True}},
    "ObjectStore": {"data": {"endpointURL": "https://s3.example.invalid:9000", "destinationPath": "s3://bucket",
                             "s3Credentials": {"name": "ref"}}},
}


def fixture(kind):
    return {"apiVersion": "fixture/v1", "kind": kind,
            "metadata": {"name": "example", "namespace": "portal", "labels": {"app": "portal"}},
            "spec": copy.deepcopy(SPECS[kind]),
            "status": {"phase": "Ready", "readyInstances": 3,
                       "conditions": [{"type": "Ready", "status": "True", "reason": "Ready"}]}}


def assign(obj, path, value):
    parts = path.split(".")
    cur = obj
    for part in parts[:-1]:
        key = int(part) if isinstance(cur, list) else part
        if isinstance(cur, dict) and key not in cur:
            cur[key] = {}
        cur = cur[key]
    cur[int(parts[-1]) if isinstance(cur, list) else parts[-1]] = copy.deepcopy(value)


def project(resource, item):
    return json.loads(inv.project_list(resource, json.dumps({"items": [item]})))


class TestURL(unittest.TestCase):
    def test_origin_only(self):
        self.assertEqual(inv.sanitize_url(f"https://user:{CANARY}@h:443/p?q={CANARY}#f"), "https://h:443")
    def test_not_url_none(self):
        self.assertIsNone(inv.sanitize_url("not-a-url"))
    def test_malformed_port_none(self):
        self.assertIsNone(inv.sanitize_url(f"https://user:{CANARY}@host.invalid:bad/?token={CANARY}"))
    def test_uppercase_scheme(self):
        self.assertEqual(inv.sanitize_url(f"HTTPS://user:{CANARY}@host.invalid/?token={CANARY}"), "https://host.invalid")
    def test_unsupported_scheme_none(self):
        self.assertIsNone(inv.sanitize_url(f"ftp://user:{CANARY}@host.invalid/?token={CANARY}"))
    def test_wrong_type_none(self):
        self.assertIsNone(inv.sanitize_url({"credential": CANARY}))
    def test_path_dropped(self):
        self.assertEqual(inv.sanitize_url(f"https://host.invalid/{CANARY}"), "https://host.invalid")
    def test_ipv6(self):
        self.assertEqual(inv.sanitize_url("https://[2001:db8::1]:9000/"), "https://[2001:db8::1]:9000")
    def test_whitespace_authority_none(self):
        self.assertIsNone(inv.sanitize_url("https://bad host.invalid/path"))


class TestProjection(unittest.TestCase):
    def test_networkpolicy_allowlist(self):
        item = fixture("NetworkPolicy")
        item["spec"]["unneededField"] = CANARY
        item["metadata"]["annotations"] = {"secret": CANARY}
        item["metadata"]["managedFields"] = [CANARY]
        out = project("networkpolicies.networking.k8s.io", item)
        blob = json.dumps(out)
        self.assertNotIn(CANARY, blob)
        self.assertNotIn("unneededField", blob)
        self.assertNotIn("annotations", blob)
        self.assertNotIn("managedFields", blob)
        # needed facts retained
        self.assertEqual(out[0]["spec"]["ingress"][0]["ports"][0]["endPort"], 8010)
        self.assertEqual(out[0]["spec"]["ingress"][0]["from"][0]["ipBlock"]["cidr"], "10.0.0.0/24")

    def test_destination_path_sanitized(self):
        item = fixture("ObjectStore")
        item["spec"]["data"]["destinationPath"] = f"s3://user:{CANARY}@bucket.invalid/path?token={CANARY}"
        out = project("objectstores.barmancloud.cnpg.io", item)
        self.assertEqual(out[0]["spec"]["data"]["destinationPath"], "s3://bucket.invalid")

    def test_match_expressions_unknown_member_dropped(self):
        item = fixture("NetworkPolicy")
        item["spec"]["podSelector"] = {"matchExpressions": [{"key": "app", "operator": "In",
                                                             "values": ["portal"], "unexpected": CANARY}]}
        out = project("networkpolicies.networking.k8s.io", item)
        self.assertNotIn(CANARY, json.dumps(out))
        self.assertEqual(out[0]["spec"]["podSelector"]["matchExpressions"][0]["key"], "app")
        self.assertNotIn("unexpected", out[0]["spec"]["podSelector"]["matchExpressions"][0])

    def test_empty_object_rejected(self):
        with self.assertRaises(ValueError):
            inv.project_list("networkpolicies.networking.k8s.io", "{}")

    def test_empty_items_list_ok(self):
        self.assertEqual(project("networkpolicies.networking.k8s.io", None) if False else
                         json.loads(inv.project_list("networkpolicies.networking.k8s.io", json.dumps({"items": []}))), [])

    def test_missing_kind_rejected(self):
        item = fixture("NetworkPolicy")
        del item["kind"]
        with self.assertRaises(ValueError):
            inv.project_list("networkpolicies.networking.k8s.io", json.dumps({"items": [item]}))

    def test_wrong_kind_rejected(self):
        item = fixture("NetworkPolicy")
        item["kind"] = "Secret"
        with self.assertRaises(ValueError):
            inv.project_list("networkpolicies.networking.k8s.io", json.dumps({"items": [item]}))

    def test_missing_name_rejected(self):
        item = fixture("NetworkPolicy")
        item["metadata"] = {}
        with self.assertRaises(ValueError):
            inv.project_list("networkpolicies.networking.k8s.io", json.dumps({"items": [item]}))

    def test_valid_fixture_every_projector(self):
        for resource, kind in KIND_BY_RESOURCE.items():
            out = project(resource, fixture(kind))
            self.assertIsInstance(out, list)
            self.assertEqual(out[0]["metadata"]["name"], "example")
            self.assertNotIn(CANARY, json.dumps(out))


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
    def test_deadline_timeout(self):
        self.assertEqual(inv.classify(1, "context deadline exceeded", False), "TIMEOUT")
    def test_generic(self):
        self.assertEqual(inv.classify(1, "x", False), "GET_FAILED")
    def test_success(self):
        self.assertIsNone(inv.classify(0, "", False))


class _FakeResult:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class TestMain(unittest.TestCase):
    def _run(self, outputs, which="/usr/bin/kubectl"):
        tmp = tempfile.mkdtemp()
        outdir = os.path.join(tmp, "inv")
        seen = []
        def fake_run(argv, **kw):
            seen.append(argv)
            return outputs.pop(0)
        with mock.patch.object(shutil, "which", return_value=which), \
             mock.patch.object(subprocess, "run", side_effect=fake_run), \
             mock.patch.object(inv.sys, "argv", ["inventory.py", "--context", "ctx", "--output", outdir]):
            code = inv.main()
        return code, outdir, seen

    def _run_single(self, resource, item, completed=None):
        tmp = tempfile.mkdtemp()
        outdir = os.path.join(tmp, "out")
        command = (["get", resource, "-A", "-o", "json"], resource)
        result = completed or subprocess.CompletedProcess([], 0, json.dumps({"items": [item]}), "")
        with mock.patch.object(inv, "COMMANDS", [command]), \
             mock.patch.object(shutil, "which", return_value="/mock/kubectl"), \
             mock.patch.object(subprocess, "run", return_value=result), \
             mock.patch.object(inv.sys, "argv", ["inventory.py", "--context", "mock", "--output", outdir]):
            code = inv.main()
        rows = [json.loads(s) for s in (Path(outdir) / "inventory.jsonl").read_text().splitlines()]
        return code, rows

    def test_valid_full_object_exit0(self):
        outputs = []
        for argv_tail, resource in inv.COMMANDS:
            if resource is not None:
                kind = KIND_BY_RESOURCE[resource]
                outputs.append(_FakeResult(0, json.dumps({"items": [fixture(kind)]}), ""))
            else:
                outputs.append(_FakeResult(0, "", ""))
        code, _, _ = self._run(outputs)
        self.assertEqual(code, 0)

    def test_malformed_json_fails_closed(self):
        outputs = []
        for argv_tail, resource in inv.COMMANDS:
            if resource is not None:
                outputs.append(_FakeResult(0, "not-json " + CANARY, ""))
            else:
                outputs.append(_FakeResult(0, "", ""))
        code, outdir, _ = self._run(outputs)
        self.assertNotEqual(code, 0)
        self.assertNotIn(CANARY, open(os.path.join(outdir, "inventory.jsonl")).read())

    def test_argv_preserves_raw(self):
        outputs = []
        for argv_tail, resource in inv.COMMANDS:
            if resource is not None:
                outputs.append(_FakeResult(0, json.dumps({"items": [fixture(KIND_BY_RESOURCE[resource])]}), ""))
            else:
                outputs.append(_FakeResult(0, "", ""))
        code, outdir, seen = self._run(outputs)
        self.assertEqual(code, 0)
        rows = [json.loads(x) for x in open(os.path.join(outdir, "inventory.jsonl"))]
        disc = [r for r in rows if '/apis/monitoring.coreos.com/v1' in r['argv']]
        self.assertTrue(disc)
        self.assertIn('--raw', disc[0]['argv'])
        self.assertEqual(seen[0], rows[0]['argv'])

    def test_no_direct_stdout_collects_annotations_or_secrets(self):
        for argv_tail, resource in inv.COMMANDS:
            jp = ' '.join(argv_tail)
            if resource is None:
                self.assertNotIn('.metadata.annotations', jp)
                self.assertNotIn('.spec.template', jp)
                self.assertNotIn('env', jp)

    def test_subprocess_timeout_via_main(self):
        tmp = tempfile.mkdtemp()
        outdir = os.path.join(tmp, "inv")
        def fake_run(argv, **kw):
            raise subprocess.TimeoutExpired(argv, 20)
        with mock.patch.object(shutil, "which", return_value="/usr/bin/kubectl"), \
             mock.patch.object(subprocess, "run", side_effect=fake_run), \
             mock.patch.object(inv.sys, "argv", ["inventory.py", "--context", "c", "--output", outdir]):
            code = inv.main()
        self.assertNotEqual(code, 0)
        rows = [json.loads(x) for x in open(os.path.join(outdir, "inventory.jsonl"))]
        self.assertTrue(all(r["category"] == "TIMEOUT" for r in rows))
        self.assertTrue(all(r["output"] == "" for r in rows))

    def test_subprocess_oserror_via_main(self):
        tmp = tempfile.mkdtemp()
        outdir = os.path.join(tmp, "inv")
        def fake_run(argv, **kw):
            raise OSError("boom")
        with mock.patch.object(shutil, "which", return_value="/usr/bin/kubectl"), \
             mock.patch.object(subprocess, "run", side_effect=fake_run), \
             mock.patch.object(inv.sys, "argv", ["inventory.py", "--context", "c", "--output", outdir]):
            code = inv.main()
        self.assertNotEqual(code, 0)
        rows = [json.loads(x) for x in open(os.path.join(outdir, "inventory.jsonl"))]
        self.assertTrue(all(r["category"] == "GET_FAILED" for r in rows))
        self.assertTrue(all(r["output"] == "" for r in rows))

    def test_error_paths_suppress_output(self):
        for category, stderr in [("FORBIDDEN", "Forbidden " + CANARY),
                                 ("TIMEOUT", "context deadline exceeded " + CANARY),
                                 ("CONNECTION", "connection refused " + CANARY)]:
            code, rows = self._run_single("networkpolicies.networking.k8s.io",
                                          fixture("NetworkPolicy"),
                                          subprocess.CompletedProcess([], 1, CANARY, stderr))
            self.assertNotEqual(code, 0)
            self.assertEqual(rows[0]["category"], category)
            self.assertEqual(rows[0]["output"], "")
            self.assertNotIn(CANARY, rows[0]["output"])

    def test_no_overwrite(self):
        tmp = tempfile.mkdtemp()
        dest = os.path.join(tmp, "existing")
        os.mkdir(dest)
        f = os.path.join(dest, "inventory.jsonl")
        open(f, "w").write("KEEP")
        with mock.patch.object(shutil, "which", return_value="/mock/kubectl"), \
             mock.patch.object(subprocess, "run") as execute, \
             mock.patch.object(inv.sys, "argv", ["inventory.py", "--context", "mock", "--output", dest]):
            with self.assertRaises(FileExistsError):
                inv.main()
        self.assertEqual(execute.call_count, 0)
        self.assertEqual(open(f).read(), "KEEP")

    def test_no_kubectl_blocks_no_output(self):
        tmp = tempfile.mkdtemp()
        outdir = os.path.join(tmp, "novel")
        with mock.patch.object(shutil, "which", return_value=None), \
             mock.patch.object(inv.sys, "argv", ["inventory.py", "--context", "c", "--output", outdir]):
            with self.assertRaises(SystemExit) as cm:
                inv.main()
        self.assertIn("BLOCKED", str(cm.exception))
        self.assertFalse(os.path.exists(outdir))


# Table-driven malformed leaf cases (from the review reproducer).
MALFORMED_REJECT = [
    ("networkpolicies.networking.k8s.io", "metadata.namespace", BAD),
    ("networkpolicies.networking.k8s.io", "metadata.labels.app", BAD),
    ("networkpolicies.networking.k8s.io", "spec.podSelector.matchLabels.app", BAD),
    ("networkpolicies.networking.k8s.io", "spec.policyTypes", BAD),
    ("networkpolicies.networking.k8s.io", "spec.ingress.0.from.0.ipBlock.cidr", BAD),
    ("networkpolicies.networking.k8s.io", "spec.ingress.0.from.0.ipBlock.except", BAD),
    ("networkpolicies.networking.k8s.io", "spec.ingress.0.ports.0.port", BAD),
    ("networkpolicies.networking.k8s.io", "spec.ingress.0.ports.0.protocol", BAD),
    ("networkpolicies.networking.k8s.io", "spec.ingress.0.ports.0.endPort", -1),
    ("gatewayclasses.gateway.networking.k8s.io", "spec.controllerName", BAD),
    ("gateways.gateway.networking.k8s.io", "spec.gatewayClassName", BAD),
    ("gateways.gateway.networking.k8s.io", "spec.listeners.0.name", BAD),
    ("gateways.gateway.networking.k8s.io", "spec.listeners.0.port", BAD),
    ("gateways.gateway.networking.k8s.io", "spec.listeners.0.protocol", BAD),
    ("envoyproxies.gateway.envoyproxy.io", "status.conditions.0.type", BAD),
    ("envoyproxies.gateway.envoyproxy.io", "status.conditions.0.status", BAD),
    ("envoyproxies.gateway.envoyproxy.io", "status.conditions.0.reason", BAD),
    ("clusters.postgresql.cnpg.io", "spec.instances", BAD),
    ("clusters.postgresql.cnpg.io", "spec.storage.size", BAD),
    ("clusters.postgresql.cnpg.io", "spec.monitoring.enablePodMonitor", BAD),
    ("clusters.postgresql.cnpg.io", "status.phase", BAD),
    ("clusters.postgresql.cnpg.io", "status.readyInstances", BAD),
    ("objectstores.barmancloud.cnpg.io", "spec.data.s3Credentials.name", BAD),
]


class TestMalformedLeaves(unittest.TestCase):
    def _run_case(self, resource, path, value):
        kind = KIND_BY_RESOURCE[resource]
        item = fixture(kind)
        assign(item, path, value)
        tmp = tempfile.mkdtemp()
        outdir = os.path.join(tmp, "out")
        command = (["get", resource, "-A", "-o", "json"], resource)
        result = subprocess.CompletedProcess([], 0, json.dumps({"items": [item]}), "")
        with mock.patch.object(inv, "COMMANDS", [command]), \
             mock.patch.object(shutil, "which", return_value="/mock/kubectl"), \
             mock.patch.object(subprocess, "run", return_value=result), \
             mock.patch.object(inv.sys, "argv", ["inventory.py", "--context", "mock", "--output", outdir]):
            code = inv.main()
        rows = [json.loads(s) for s in (Path(outdir) / "inventory.jsonl").read_text().splitlines()]
        return code, rows

    def test_malformed_leaves_rejected(self):
        for resource, path, value in MALFORMED_REJECT:
            code, rows = self._run_case(resource, path, value)
            self.assertNotEqual(code, 0, f"{resource}:{path} should fail")
            self.assertEqual(rows[0]["category"], "PARSE_ERROR", f"{resource}:{path}")
            self.assertEqual(rows[0]["output"], "", f"{resource}:{path}")
            self.assertNotIn(CANARY, rows[0]["output"], f"{resource}:{path}")


if __name__ == "__main__":
    unittest.main()
