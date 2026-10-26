#!/usr/bin/env python3
"""Offline tests for supplemental.py (Phase-2, NOT approved to run live).

Verifies the LI-01..04 corrections on source-version fixtures:
  - ObjectStore spec.configuration (NOT spec.data) projected; secret refs are
    name+key only, values never emitted; endpointURL origin-only.
  - CNPG spec.plugins[] name/barmanObjectName/isWALArchiver projected.
  - Calico/policy selector-only projection drops annotations/env/extra fields.
  - strict URL origin + error categories + no-overwrite + no-kubectl.
"""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("supplemental", os.path.join(HERE, "supplemental.py"))
inv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inv)

CANARY = "SYNTHETIC_REVIEW_CANARY_NOT_A_CREDENTIAL"

OBJSTORE = {
    "apiVersion": "barmancloud.cnpg.io/v1", "kind": "ObjectStore",
    "metadata": {"name": "portal-db-backup", "namespace": "portal"},
    "spec": {
        "retentionPolicy": "14d",
        "configuration": {
            "destinationPath": f"s3://portal-postgres-backup/",
            "endpointURL": f"https://user:{CANARY}@s3-backup.demo-pak.test/?token={CANARY}",
            "endpointCA": {"name": "portal-barman-s3-ca", "key": "ca.crt"},
            "s3Credentials": {
                "accessKeyId": {"name": "portal-barman-s3-credentials", "key": "ACCESS_KEY_ID"},
                "secretAccessKey": {"name": "portal-barman-s3-credentials", "key": "ACCESS_SECRET_KEY"},
                "region": {"name": "portal-barman-s3-credentials", "key": "AWS_REGION"},
            },
        },
    },
}

CLUSTER = {
    "apiVersion": "postgresql.cnpg.io/v1", "kind": "Cluster",
    "metadata": {"name": "portal-db", "namespace": "portal"},
    "spec": {
        "instances": 3,
        "imageName": "ghcr.io/cloudnative-pg/postgresql:17.10@sha256:ba9e49...",
        "plugins": [{"name": "barman-cloud.cloudnative-pg.io", "isWALArchiver": True,
                     "parameters": {"barmanObjectName": "portal-db-backup"}}],
    },
}


def project(resource_key, item):
    return json.loads(inv.project_list(resource_key, json.dumps({"items": [item]})))[0]


class TestObjectStoreConfiguration(unittest.TestCase):
    def test_configuration_path(self):
        out = project("objectstore_configuration", OBJSTORE)
        cfg = out["spec"]["configuration"]
        self.assertNotIn(CANARY, json.dumps(out))          # credentials never emitted
        self.assertEqual(cfg["endpointURL"], "https://s3-backup.demo-pak.test")
        self.assertEqual(cfg["destinationPath"], "s3://portal-postgres-backup")
        self.assertEqual(cfg["endpointCAName"], "portal-barman-s3-ca")
        self.assertEqual(cfg["s3AccessKeyIdRef"], {"name": "portal-barman-s3-credentials", "key": "ACCESS_KEY_ID"})
        self.assertEqual(cfg["s3SecretAccessKeyRef"]["name"], "portal-barman-s3-credentials")
        # spec.data is NOT read (old wrong path absent from output)
        self.assertNotIn("data", out["spec"])

    def test_spec_data_path_ignored(self):
        item = dict(OBJSTORE)
        item["spec"]["data"] = {"endpointURL": "https://wrong.invalid", "extra": CANARY}
        out = project("objectstore_configuration", item)
        self.assertNotIn(CANARY, json.dumps(out))
        self.assertNotIn("data", out["spec"])


class TestClusterPlugins(unittest.TestCase):
    def test_plugin_mapping(self):
        out = project("cluster_plugins", CLUSTER)
        pl = out["spec"]["plugins"][0]
        self.assertEqual(pl["name"], "barman-cloud.cloudnative-pg.io")
        self.assertEqual(pl["isWALArchiver"], True)
        self.assertEqual(pl["barmanObjectName"], "portal-db-backup")
        self.assertNotIn("backup", out["spec"])  # old wrong path not used


class TestPolicySelectorOnly(unittest.TestCase):
    def test_no_annotations_env(self):
        item = {"apiVersion": "crd.projectcalico.org/v1", "kind": "NetworkPolicy",
                "metadata": {"name": "np", "namespace": "portal", "annotations": {"x": CANARY}},
                "spec": {"selector": "app == 'x'", "ingress": [], "env": {"k": CANARY}, "order": 100}}
        out = project("calico_np", item)
        self.assertNotIn(CANARY, json.dumps(out))
        self.assertNotIn("env", out["spec"])
        self.assertNotIn("annotations", out["metadata"])
        self.assertEqual(out["spec"]["selector"], "app == 'x'")


class TestOriginOnly(unittest.TestCase):
    def test_strict(self):
        self.assertEqual(inv.origin_only("https://h:9000/p?q=1"), "https://h:9000")
        self.assertIsNone(inv.origin_only(f"ftp://u:{CANARY}@h/"))
        self.assertIsNone(inv.origin_only({"x": CANARY}))
        self.assertIsNone(inv.origin_only("https://bad host/"))
        self.assertEqual(inv.origin_only("https://[2001:db8::1]:9000/"), "https://[2001:db8::1]:9000")


class TestClassify(unittest.TestCase):
    def test_categories(self):
        self.assertEqual(inv.classify(None, "", False, parse_error=True), "PARSE_ERROR")
        self.assertEqual(inv.classify(None, "", True), "TIMEOUT")
        self.assertEqual(inv.classify(1, "Forbidden", False), "FORBIDDEN")
        self.assertEqual(inv.classify(1, "no matches for kind", False), "API_NOT_SERVED")
        self.assertEqual(inv.classify(1, "connection refused", False), "CONNECTION")
        self.assertEqual(inv.classify(0, "", False), None)


class TestMain(unittest.TestCase):
    def _run(self, outputs):
        tmp = tempfile.mkdtemp()
        outdir = os.path.join(tmp, "out")
        def fake_run(argv, **kw):
            return outputs.pop(0)
        with mock.patch.object(shutil, "which", return_value="/usr/bin/kubectl"), \
             mock.patch.object(subprocess, "run", side_effect=fake_run), \
             mock.patch.object(inv.sys, "argv", ["supplemental.py", "--context", "c", "--output", outdir]):
            code = inv.main()
        rows = [json.loads(l) for l in open(os.path.join(outdir, "supplemental.jsonl"))]
        return code, rows

    def _out(self, phase, rid, body):
        class R:
            returncode = 0
            stdout = body
            stderr = ""
        return R()

    def test_valid_and_malformed(self):
        outputs = []
        for phase, rid, _, rk in inv.READ_CONTRACT:
            if phase == "config" and rk == "objectstore_configuration":
                outputs.append(self._out(phase, rid, "not-json " + CANARY))
            elif phase == "config":
                outputs.append(self._out(phase, rid, json.dumps({"items": [OBJSTORE if 'ObjectStore' in str(rk) else CLUSTER]})))
            else:
                outputs.append(self._out(phase, rid, '{"groups":[]}'))
        code, rows = self._run(outputs)
        self.assertNotEqual(code, 0)
        self.assertNotIn(CANARY, json.dumps(rows))
        self.assertTrue(any(r["category"] == "PARSE_ERROR" for r in rows))

    def test_no_kubectl(self):
        tmp = tempfile.mkdtemp()
        outdir = os.path.join(tmp, "novel")
        with mock.patch.object(shutil, "which", return_value=None), \
             mock.patch.object(inv.sys, "argv", ["supplemental.py", "--context", "c", "--output", outdir]):
            with self.assertRaises(SystemExit):
                inv.main()
        self.assertFalse(os.path.exists(outdir))

    def test_no_overwrite(self):
        tmp = tempfile.mkdtemp()
        dest = os.path.join(tmp, "exists")
        os.mkdir(dest)
        open(os.path.join(dest, "supplemental.jsonl"), "w").write("KEEP")
        with mock.patch.object(shutil, "which", return_value="/usr/bin/kubectl"), \
             mock.patch.object(subprocess, "run") as execute, \
             mock.patch.object(inv.sys, "argv", ["supplemental.py", "--context", "c", "--output", dest]):
            with self.assertRaises(FileExistsError):
                inv.main()
        self.assertEqual(execute.call_count, 0)
        self.assertEqual(open(os.path.join(dest, "supplemental.jsonl")).read(), "KEEP")


if __name__ == "__main__":
    unittest.main()
