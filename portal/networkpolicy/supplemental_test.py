#!/usr/bin/env python3
"""Offline tests for supplemental.py (SP-01..04). Mocked kubectl only."""
import importlib.util
import copy
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

CANARY = "SYNTHETIC_PHASE2_CANARY_NOT_A_SECRET"


def enc(item):
    return json.dumps({"items": [item]})


def single(item):
    return json.dumps(item)


CALICO_DISC = {"kind": "APIResourceList", "groupVersion": "crd.projectcalico.org/v1",
               "resources": [{"name": "networkpolicies", "namespaced": True, "verbs": ["get", "list"]},
                             {"name": "globalnetworkpolicies", "namespaced": False, "verbs": ["get", "list"]},
                             {"name": "felixconfigurations", "namespaced": False, "verbs": ["get"]}]}
POLICY_DISC = {"kind": "APIResourceList", "groupVersion": "policy.networking.k8s.io/v1alpha2",
               "resources": [{"name": "adminnetworkpolicies", "namespaced": True, "verbs": ["get", "list"]}]}

OS = {"apiVersion": "barmancloud.cnpg.io/v1", "kind": "ObjectStore",
      "metadata": {"name": "portal-db-backup", "namespace": "portal"},
      "spec": {"configuration": {"endpointURL": "https://s3.example.test", "destinationPath": "s3://backup/",
              "s3Credentials": {"accessKeyId": {"name": "creds", "key": "ACCESS_KEY_ID"}}}}}
CL = {"apiVersion": "postgresql.cnpg.io/v1", "kind": "Cluster",
      "metadata": {"name": "portal-db", "namespace": "portal"},
      "spec": {"plugins": [{"name": "barman-cloud.cloudnative-pg.io", "isWALArchiver": True,
              "parameters": {"barmanObjectName": "portal-db-backup"}}]}}
NP = {"apiVersion": "crd.projectcalico.org/v1", "kind": "NetworkPolicy",
      "metadata": {"name": "n", "namespace": "portal"},
      "spec": {"selector": "all()", "ingress": [{"action": "Allow", "source": {"selector": "x"}}],
               "egress": [], "types": ["Ingress"]}}
GNP = {"apiVersion": "crd.projectcalico.org/v1", "kind": "GlobalNetworkPolicy",
       "metadata": {"name": "gnp"}, "spec": {"selector": "all()", "order": 10, "applyOnForward": True}}
FELIX = {"apiVersion": "crd.projectcalico.org/v1", "kind": "FelixConfiguration",
         "metadata": {"name": "default"}, "spec": {"bpfEnabled": False, "dataplane": "linux"}}
POD = {"apiVersion": "v1", "metadata": {"name": "portal-db-1", "namespace": "portal"},
       "spec": {"initContainers": [{"name": "bootstrap", "image": "img:1", "ports": [{"containerPort": 5432}]}],
                "containers": [{"name": "postgres", "image": "pg:17", "ports": [{"containerPort": 5432, "name": "postgresql"}]}]}}


def project(resource_key, raw):
    return json.loads(inv.project_config(resource_key, raw))


class TestDiscoveryGate(unittest.TestCase):
    def _run(self, first_output, first_exc=None, first_rc=0, first_err=""):
        calls = []
        tmp = tempfile.mkdtemp()
        outdir = os.path.join(tmp, "out")
        def fake_run(argv, **kw):
            idx = len(calls)
            calls.append(argv)
            if idx == 0:
                if first_exc:
                    raise first_exc
                return SimpleR(first_rc, first_output, first_err)
            # subsequent reads: discovery D2 + config
            key = inv.READ_CONTRACT[idx][3]
            if key == "policy_discovery":
                return SimpleR(0, json.dumps(POLICY_DISC), "")
            if key == "objectstore":
                return SimpleR(0, single(OS), "")
            if key == "cluster":
                return SimpleR(0, single(CL), "")
            if key == "calico_np":
                return SimpleR(0, enc(NP), "")
            if key == "calico_gnp":
                return SimpleR(0, enc(GNP), "")
            if key == "felix":
                return SimpleR(0, single(FELIX), "")
            if key == "sidecar":
                return SimpleR(0, enc(POD), "")
            if key == "plugin":
                return SimpleR(0, enc(POD), "")
            return SimpleR(0, "{}", "")
        with mock.patch.object(shutil, "which", return_value="/mock/kubectl"), \
             mock.patch.object(subprocess, "run", side_effect=fake_run), \
             mock.patch.object(inv.sys, "argv", ["supplemental.py", "--context", "c", "--output", outdir]):
            rc = inv.main()
        rows = [json.loads(l) for l in open(os.path.join(outdir, "supplemental.jsonl"))]
        return rc, calls, rows

    def test_wrong_discovery_blocks_dependents(self):
        rc, calls, rows = self._run(json.dumps({"kind": "APIResourceList", "groupVersion": "wrong.invalid/v9", "resources": []}))
        self.assertNotEqual(rc, 0)
        # D1 wrong -> C3/C4/C5 (deps D1) blocked: only C1,C2,S1,S2 run = 4 config calls
        config_calls = [a for a in calls if "--raw" not in a]
        self.assertEqual(len(config_calls), 4)
        blocked = [r for r in rows if r["category"] == "BLOCKED_NOT_EXECUTED"]
        self.assertEqual(len(blocked), 3)

    def test_discovery_forbidden_blocks(self):
        rc, calls, rows = self._run("", first_rc=1, first_err="Forbidden " + CANARY)
        self.assertNotEqual(rc, 0)
        self.assertNotIn(CANARY, json.dumps(rows))
        config_calls = [a for a in calls if "--raw" not in a]
        self.assertEqual(len(config_calls), 4)

    def test_discovery_timeout_blocks(self):
        rc, calls, rows = self._run("", first_exc=subprocess.TimeoutExpired(["kubectl"], 20))
        self.assertNotEqual(rc, 0)
        self.assertEqual(rows[0]["category"], "TIMEOUT")
        config_calls = [a for a in calls if "--raw" not in a]
        self.assertEqual(len(config_calls), 4)

    def test_non_json_discovery_rejected(self):
        rc, calls, rows = self._run("not JSON " + CANARY)
        self.assertNotEqual(rc, 0)
        self.assertNotIn(CANARY, json.dumps(rows))

    def test_extra_discovery_member_dropped(self):
        rc, calls, rows = self._run(json.dumps({"kind": "APIResourceList", "groupVersion": "crd.projectcalico.org/v1",
                                                "resources": CALICO_DISC["resources"], "unexpected": CANARY}))
        self.assertNotIn(CANARY, json.dumps(rows))

    def test_valid_discovery_runs_all(self):
        rc, calls, rows = self._run(json.dumps(CALICO_DISC))
        self.assertEqual(rc, 0)
        self.assertEqual(len(calls), len(inv.READ_CONTRACT))
        self.assertNotIn(CANARY, json.dumps(rows))


class SimpleR:
    def __init__(self, returncode, stdout, stderr):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class TestProjectors(unittest.TestCase):
    def test_objectstore_configuration(self):
        out = project("objectstore", single(OS))[0]
        self.assertEqual(out["spec"]["configuration"]["endpointURL"], "https://s3.example.test")
        self.assertEqual(out["spec"]["configuration"]["s3AccessKeyIdRef"], {"name": "creds", "key": "ACCESS_KEY_ID"})

    def test_wrong_api_version_rejected(self):
        bad = copy.deepcopy(OS); bad["apiVersion"] = "wrong.invalid/v99"
        with self.assertRaises(ValueError):
            project("objectstore", single(bad))

    def test_false_secret_ref_rejected(self):
        bad = copy.deepcopy(OS); bad["spec"]["configuration"]["s3Credentials"] = {"accessKeyId": False}
        with self.assertRaises(ValueError):
            project("objectstore", single(bad))

    def test_missing_spec_rejected(self):
        bad = copy.deepcopy(OS); del bad["spec"]
        with self.assertRaises(ValueError):
            project("objectstore", single(bad))

    def test_empty_namespace_rejected(self):
        bad = copy.deepcopy(OS); bad["metadata"]["namespace"] = ""
        with self.assertRaises(ValueError):
            project("objectstore", single(bad))

    def test_cluster_plugins(self):
        out = project("cluster", single(CL))[0]
        self.assertEqual(out["spec"]["plugins"][0]["barmanObjectName"], "portal-db-backup")

    def test_policy_scalar_canary_rejected(self):
        for field, val in {"selector": {"password": CANARY}, "order": {"v": CANARY},
                           "types": [{"v": CANARY}]}.items():
            obj = copy.deepcopy(NP); obj["spec"][field] = val
            with self.assertRaises(ValueError):
                project("calico_np", enc(obj))

    def test_policy_nested_metadata_dropped(self):
        obj = copy.deepcopy(NP)
        obj["spec"]["ingress"] = [{"action": "Allow", "metadata": {"annotations": {"n": CANARY}},
                                   "unexpected": {"t": CANARY}}]
        out = project("calico_np", enc(obj))[0]
        self.assertNotIn(CANARY, json.dumps(out))
        self.assertEqual(out["spec"]["ingress"][0]["action"], "Allow")

    def test_policy_valid(self):
        out = project("calico_np", enc(NP))[0]
        self.assertEqual(out["spec"]["ingress"][0]["action"], "Allow")
        self.assertNotIn(CANARY, json.dumps(out))

    def test_gnp_cluster_scoped_valid(self):
        out = project("calico_gnp", enc(GNP))[0]
        self.assertIsNone(out["metadata"]["namespace"])
        self.assertEqual(out["spec"]["applyOnForward"], True)

    def test_malformed_items_rejected(self):
        with self.assertRaises(ValueError):
            project("calico_np", json.dumps({"items": [None, 7, "bad"]}))

    def test_felix(self):
        out = project("felix", single(FELIX))[0]
        self.assertEqual(out["spec"]["bpfEnabled"], False)

    def test_pod_identity(self):
        out = project("sidecar", enc(POD))[0]
        self.assertEqual(out["containers"][0]["name"], "postgres")
        self.assertEqual(out["initContainers"][0]["name"], "bootstrap")


class TestNoOverwriteNoKubectl(unittest.TestCase):
    def test_no_overwrite(self):
        tmp = tempfile.mkdtemp()
        dest = os.path.join(tmp, "exists")
        os.mkdir(dest)
        open(os.path.join(dest, "supplemental.jsonl"), "w").write("KEEP")
        with mock.patch.object(shutil, "which", return_value="/mock/kubectl"), \
             mock.patch.object(subprocess, "run") as ex, \
             mock.patch.object(inv.sys, "argv", ["supplemental.py", "--context", "c", "--output", dest]):
            with self.assertRaises(FileExistsError):
                inv.main()
        self.assertEqual(ex.call_count, 0)

    def test_no_kubectl(self):
        tmp = tempfile.mkdtemp()
        outdir = os.path.join(tmp, "novel")
        with mock.patch.object(shutil, "which", return_value=None), \
             mock.patch.object(inv.sys, "argv", ["supplemental.py", "--context", "c", "--output", outdir]):
            with self.assertRaises(SystemExit):
                inv.main()
        self.assertFalse(os.path.exists(outdir))


if __name__ == "__main__":
    unittest.main()
