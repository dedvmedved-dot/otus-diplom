#!/usr/bin/env python3
"""Offline tests for supplemental.py (SP-01..05). Mocked kubectl, argv-routed."""
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

CANARY = "SYNTHETIC_SP_REVIEW_CANARY_NOT_A_SECRET"


def enc(item):
    return json.dumps({"items": [item]})


def single(item):
    return json.dumps(item)


CALICO_DISC = {"kind": "APIResourceList", "groupVersion": "crd.projectcalico.org/v1",
               "resources": [
                   {"name": "networkpolicies", "kind": "NetworkPolicy", "namespaced": True, "verbs": ["get", "list"]},
                   {"name": "globalnetworkpolicies", "kind": "GlobalNetworkPolicy", "namespaced": False, "verbs": ["get", "list"]},
                   {"name": "felixconfigurations", "kind": "FelixConfiguration", "namespaced": False, "verbs": ["get"]}]}
POLICY_DISC = {"kind": "APIResourceList", "groupVersion": "policy.networking.k8s.io/v1alpha2", "resources": []}

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
         "metadata": {"name": "default"}, "spec": {"bpfEnabled": False, "nftablesMode": "Auto"}}
POD = {"apiVersion": "v1", "kind": "Pod", "metadata": {"name": "calico-node-abc", "namespace": "kube-system"},
       "spec": {"initContainers": [], "containers": [{"name": "calico-node", "image": "calico/node:v3.32.0",
               "ports": [{"containerPort": 9090, "name": "calico-typha"}]}]},
       "status": {"containerStatuses": [{"name": "calico-node", "imageID": "containerd://sha256:" + "a" * 64}]}}

CMDS = {tuple(tail): rid for rid, _, tail, _, _, _, _ in inv.READ_CONTRACT}


class R:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def run(overrides=None):
    overrides = overrides or {}
    calls = []
    defaults = {
        "D1": R(0, json.dumps(CALICO_DISC)), "D2": R(0, json.dumps(POLICY_DISC)),
        "I1": R(0, enc(POD)), "C1": R(0, single(OS)), "C2": R(0, single(CL)),
        "C3": R(0, enc(NP)), "C4": R(0, enc(GNP)), "C5": R(0, single(FELIX)),
        "S1": R(0, enc(POD)), "S2": R(0, enc(POD)),
    }
    tmp = tempfile.mkdtemp()
    outdir = os.path.join(tmp, "out")
    def fake(argv, **kw):
        rid = CMDS[tuple(argv[4:])]
        calls.append(rid)
        ans = overrides.get(rid, defaults[rid])
        if isinstance(ans, BaseException):
            raise ans
        return ans
    with mock.patch.object(shutil, "which", return_value="/mock/kubectl"), \
         mock.patch.object(subprocess, "run", side_effect=fake), \
         mock.patch.object(inv.sys, "argv", ["supplemental.py", "--context", "c", "--output", outdir]):
        rc = inv.main()
    rows = [json.loads(l) for l in open(os.path.join(outdir, "supplemental.jsonl"))]
    return rc, calls, rows


class TestDiscoveryGate(unittest.TestCase):
    def test_wrong_group_blocks(self):
        rc, calls, _ = run({"D1": R(0, json.dumps({"kind": "APIResourceList", "groupVersion": "wrong/v9", "resources": []}))})
        self.assertNotEqual(rc, 0)
        self.assertNotIn("C3", calls); self.assertNotIn("C4", calls); self.assertNotIn("C5", calls)

    def test_scope_verb_kind_missing_felix(self):
        for change in [
            lambda d: d["resources"][0].update(namespaced=False),
            lambda d: d["resources"][0].update(verbs=["get"]),
            lambda d: d["resources"][0].update(kind="WrongKind"),
            lambda d: d.update(resources=d["resources"][:2]),  # missing felixconfigurations
        ]:
            disc = copy.deepcopy(CALICO_DISC); change(disc)
            rc, calls, _ = run({"D1": R(0, json.dumps(disc))})
            self.assertNotEqual(rc, 0, f"change {change} should fail")
            self.assertNotIn("C5", calls)

    def test_policy_api_unsupported(self):
        pd = {"kind": "APIResourceList", "groupVersion": "policy.networking.k8s.io/v1alpha2",
              "resources": [{"name": "adminnetworkpolicies", "kind": "AdminNetworkPolicy", "namespaced": False, "verbs": ["get", "list"]}]}
        rc, calls, rows = run({"D2": R(0, json.dumps(pd))})
        self.assertNotEqual(rc, 0)

    def test_calico_identity_present(self):
        rc, calls, _ = run()
        self.assertEqual(rc, 0)
        self.assertIn("I1", calls)

    def test_valid(self):
        rc, calls, rows = run()
        self.assertEqual(rc, 0)
        self.assertNotIn(CANARY, json.dumps(rows))


class TestProjectors(unittest.TestCase):
    def test_service_accounts_typed(self):
        obj = copy.deepcopy(NP)
        obj["spec"]["ingress"][0]["source"]["serviceAccounts"] = {"names": ["default"], "extra": {"token": CANARY}}
        out = json.loads(inv.project_config("calico_np", enc(obj), "list", None))
        self.assertNotIn(CANARY, json.dumps(out))
        self.assertEqual(out[0]["spec"]["ingress"][0]["source"]["serviceAccounts"]["names"], ["default"])

    def test_tier_notSelector_preserved(self):
        base = copy.deepcopy(NP)
        base["spec"]["ingress"][0]["source"] = {"selector": "all()"}
        restrict = copy.deepcopy(base)
        restrict["spec"]["tier"] = "security"
        restrict["spec"]["ingress"][0]["source"]["notSelector"] = "app == 'excluded'"
        a = json.loads(inv.project_config("calico_np", enc(base), "list", None))[0]
        b = json.loads(inv.project_config("calico_np", enc(restrict), "list", None))[0]
        self.assertNotEqual(json.dumps(a, sort_keys=True), json.dumps(b, sort_keys=True))
        self.assertEqual(b["spec"]["tier"], "security")
        self.assertEqual(b["spec"]["ingress"][0]["source"]["notSelector"], "app == 'excluded'")

    def test_numeric_protocol_accepted(self):
        obj = copy.deepcopy(NP)
        obj["spec"]["ingress"][0]["protocol"] = 17
        out = json.loads(inv.project_config("calico_np", enc(obj), "list", None))[0]
        self.assertEqual(out["spec"]["ingress"][0]["protocol"], 17)

    def test_pod_port_leaf_typed(self):
        bad = copy.deepcopy(POD)
        bad["spec"]["containers"][0]["ports"] = [{"containerPort": {"token": CANARY}, "name": {"p": CANARY}}]
        with self.assertRaises(ValueError):
            inv.project_config("identity", enc(bad), "list", None)

    def test_pod_imageID_from_status(self):
        out = json.loads(inv.project_config("identity", enc(POD), "list", None))[0]
        self.assertTrue(out["containers"][0]["imageID"].startswith("containerd://sha256:"))

    def test_pod_wrong_kind_rejected(self):
        bad = copy.deepcopy(POD); bad["kind"] = "Service"
        with self.assertRaises(ValueError):
            inv.project_config("identity", enc(bad), "list", None)

    def test_malformed_containers_rejected(self):
        bad = copy.deepcopy(POD); bad["spec"]["containers"] = [None, 7]
        with self.assertRaises(ValueError):
            inv.project_config("identity", enc(bad), "list", None)

    def test_named_get_bound(self):
        bad = copy.deepcopy(OS); bad["metadata"]["name"] = "different-object"
        with self.assertRaises(ValueError):
            inv.project_config("objectstore", single(bad), "single", "portal-db-backup")

    def test_gnp_cluster_scoped(self):
        out = json.loads(inv.project_config("calico_gnp", enc(GNP), "list", None))[0]
        self.assertIsNone(out["metadata"]["namespace"])


class TestNoOverwriteNoKubectl(unittest.TestCase):
    def test_no_overwrite(self):
        tmp = tempfile.mkdtemp(); dest = os.path.join(tmp, "e"); os.mkdir(dest)
        open(os.path.join(dest, "supplemental.jsonl"), "w").write("KEEP")
        with mock.patch.object(shutil, "which", return_value="/m"), mock.patch.object(subprocess, "run") as ex, \
             mock.patch.object(inv.sys, "argv", ["supplemental.py", "--context", "c", "--output", dest]):
            with self.assertRaises(FileExistsError):
                inv.main()
        self.assertEqual(ex.call_count, 0)

    def test_no_kubectl(self):
        tmp = tempfile.mkdtemp(); outdir = os.path.join(tmp, "n")
        with mock.patch.object(shutil, "which", return_value=None), \
             mock.patch.object(inv.sys, "argv", ["supplemental.py", "--context", "c", "--output", outdir]):
            with self.assertRaises(SystemExit):
                inv.main()
        self.assertFalse(os.path.exists(outdir))


if __name__ == "__main__":
    unittest.main()
