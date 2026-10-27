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
PINNED_HEX = "f4fafd8ba641d96c5a91b01e5a519117d77d55dee789a3562ba3ad4aa125b36a"
AMD64_CONFIG_HEX = "6bc9fa4dc2b10ca1d4b97a1cd570036651898cea8b3c3bcbb1d55cf813e43f65"


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
       "spec": {"initContainers": [], "containers": [{"name": "calico-node", "image": "quay.io/calico/node:v3.32.0",
               "ports": [{"containerPort": 9090, "name": "calico-typha"}]}]},
       "status": {"containerStatuses": [{"name": "calico-node", "imageID": "containerd://sha256:" + PINNED_HEX}]}}
POD_PORTAL = {"apiVersion": "v1", "kind": "Pod", "metadata": {"name": "portal-db-1", "namespace": "portal"},
       "spec": {"initContainers": [], "containers": [{"name": "postgres", "image": "ghcr.io/cloudnative-pg/postgresql:17.4",
               "ports": [{"containerPort": 5432, "name": "postgresql"}]}]},
       "status": {"containerStatuses": [{"name": "postgres", "imageID": "containerd://sha256:" + "d" * 64}]}}
POD_CNPG = {"apiVersion": "v1", "kind": "Pod", "metadata": {"name": "barman-cloud-xyz", "namespace": "cnpg-system"},
       "spec": {"initContainers": [], "containers": [{"name": "barman-cloud", "image": "ghcr.io/cloudnative-pg/barman-cloud:0.13.0",
               "ports": [{"containerPort": 9090, "name": "http"}]}]},
       "status": {"containerStatuses": [{"name": "barman-cloud", "imageID": "containerd://sha256:" + "e" * 64}]}}

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
        "S1": R(0, enc(POD_PORTAL)), "S2": R(0, enc(POD_CNPG)),
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
        obj["spec"]["ingress"][0]["source"]["serviceAccounts"] = {"names": ["default"], "selector": "x"}
        out = json.loads(inv.project_config("calico_np", enc(obj), "list", None))
        self.assertEqual(out[0]["spec"]["ingress"][0]["source"]["serviceAccounts"]["names"], ["default"])
        bad = copy.deepcopy(NP)
        bad["spec"]["ingress"][0]["source"]["serviceAccounts"] = {"names": ["default"], "extra": {"token": CANARY}}
        with self.assertRaises(inv.UnsupportedField):
            inv.project_config("calico_np", enc(bad), "list", None)

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


class TestRemainingSP(unittest.TestCase):
    def _run_rid(self, rid, body):
        return run({rid: R(0, body if isinstance(body, str) else json.dumps(body))})

    def test_identity_gate_negatives(self):
        bad = copy.deepcopy(POD)
        bad["spec"]["containers"][0]["image"] = "other.example/unreviewed:v999"
        bad["status"]["containerStatuses"][0]["imageID"] = "containerd://sha256:" + "b" * 64
        nostatus = copy.deepcopy(POD); nostatus.pop("status")
        for name, body in {"empty": {"items": []}, "unreviewed": {"items": [bad]},
                           "missing_image_id": {"items": [nostatus]},
                           "mixed": {"items": [POD, bad]}}.items():
            rc, calls, _ = run({"I1": R(0, json.dumps(body))})
            self.assertNotEqual(rc, 0, name)
            self.assertNotIn("C3", calls, name); self.assertNotIn("C4", calls, name); self.assertNotIn("C5", calls, name)

    def test_missing_discovery_scope_rejected(self):
        d = copy.deepcopy(CALICO_DISC)
        for r in d["resources"]:
            r.pop("namespaced")
        rc, calls, _ = run({"D1": R(0, json.dumps(d))})
        self.assertNotEqual(rc, 0)
        self.assertNotIn("C5", calls)

    def test_unsupported_discovery(self):
        pd = {"kind": "APIResourceList", "groupVersion": "policy.networking.k8s.io/v1alpha2",
              "resources": [{"name": "adminnetworkpolicies", "kind": "AdminNetworkPolicy", "namespaced": False, "verbs": ["get", "list"]}]}
        rc, calls, rows = run({"D2": R(0, json.dumps(pd))})
        self.assertNotEqual(rc, 0)
        d2 = [r for r in rows if r["id"] == "D2"][0]
        self.assertEqual(d2["category"], "UNSUPPORTED")
        self.assertIn("AdminNetworkPolicy", d2["output"])

    def test_semantic_fields_preserved(self):
        base = copy.deepcopy(NP)
        base["spec"]["ingress"][0]["source"] = {"selector": "all()"}
        obj = copy.deepcopy(base)
        obj["spec"]["ingress"][0].update(notProtocol="UDP", ipVersion=6, http={"methods": ["GET"]})
        obj["spec"]["serviceAccountSelector"] = "role == 'reader'"
        obj["spec"]["ingress"][0]["source"]["services"] = {"name": "svc", "namespace": "portal"}
        a = json.loads(inv.project_config("calico_np", enc(base), "list", None))[0]
        b = json.loads(inv.project_config("calico_np", enc(obj), "list", None))[0]
        self.assertNotEqual(json.dumps(a, sort_keys=True), json.dumps(b, sort_keys=True))
        self.assertEqual(b["spec"]["ingress"][0]["notProtocol"], "UDP")
        self.assertEqual(b["spec"]["ingress"][0]["ipVersion"], 6)
        self.assertEqual(b["spec"]["serviceAccountSelector"], "role == 'reader'")
        self.assertEqual(b["spec"]["ingress"][0]["source"]["services"]["name"], "svc")

    def test_wrong_binding(self):
        os_bad = copy.deepcopy(OS); os_bad["metadata"]["namespace"] = "other"
        rc, _, _ = run({"C1": R(0, single(os_bad))})
        self.assertNotEqual(rc, 0)
        cl_bad = copy.deepcopy(CL); cl_bad["metadata"]["namespace"] = "other"
        rc, _, _ = run({"C2": R(0, single(cl_bad))})
        self.assertNotEqual(rc, 0)
        felix_bad = copy.deepcopy(FELIX); felix_bad["metadata"]["name"] = "other"
        rc, _, _ = run({"C5": R(0, single(felix_bad))})
        self.assertNotEqual(rc, 0)

    def test_string_container_port_rejected(self):
        bad = copy.deepcopy(POD)
        bad["spec"]["containers"][0]["ports"] = [{"containerPort": "not-numeric", "name": "p"}]
        with self.assertRaises(ValueError):
            inv.project_config("identity", enc(bad), "list", None)

    def test_invalid_status_rejected(self):
        bad = copy.deepcopy(POD)
        bad["status"]["containerStatuses"] = False
        rc, calls, _ = run({"I1": R(0, enc(bad))})
        self.assertNotEqual(rc, 0)
        self.assertNotIn("C3", calls)


    def test_identity_exact_contract(self):
        pin = "quay.io/calico/node@sha256:" + PINNED_HEX
        p = copy.deepcopy(POD); p["spec"]["containers"][0]["image"] = pin
        rc, calls, _ = run({"I1": R(0, enc(p))})
        self.assertEqual(rc, 0); self.assertIn("C3", calls)
        p2 = copy.deepcopy(POD); p2["spec"]["containers"][0]["image"] = "unreviewed.example/calico/node:v3.32.0"
        rc, calls, _ = run({"I1": R(0, enc(p2))})
        self.assertNotEqual(rc, 0); self.assertNotIn("C3", calls)
        p3 = copy.deepcopy(POD); p3["spec"]["containers"][0]["image"] = "calico/node:v3.320.999"
        rc, _, _ = run({"I1": R(0, enc(p3))}); self.assertNotEqual(rc, 0)
        p4 = copy.deepcopy(POD); p4["status"]["containerStatuses"][0]["imageID"] = "not-a-runtime-digest"
        rc, _, _ = run({"I1": R(0, enc(p4))}); self.assertNotEqual(rc, 0)
        # unbound (arbitrary) runtime digest rejected even when consistent across pods
        p5 = copy.deepcopy(POD); p5["status"]["containerStatuses"][0]["imageID"] = "containerd://sha256:" + "b" * 64
        rc, _, _ = run({"I1": R(0, json.dumps({"items": [p5, copy.deepcopy(p5)]}))}); self.assertNotEqual(rc, 0)
        p6 = copy.deepcopy(POD); p6["metadata"]["namespace"] = "other"
        rc, _, _ = run({"I1": R(0, enc(p6))}); self.assertNotEqual(rc, 0)
        other = copy.deepcopy(POD); other["spec"]["containers"] = [{"name": "other", "image": "unreviewed.example/other:v1"}]
        other.pop("status")
        rc, _, _ = run({"I1": R(0, json.dumps({"items": [POD, other]}))}); self.assertNotEqual(rc, 0)

    def test_unsupported_field_rejected(self):
        for label, path in [("spec", ["spec"]), ("rule", ["spec", "ingress", 0]),
                            ("entity", ["spec", "ingress", 0, "source"]),
                            ("http", ["spec", "ingress", 0, "http"]),
                            ("icmp", ["spec", "ingress", 0, "icmp"])]:
            b = copy.deepcopy(NP)
            rule = b["spec"]["ingress"][0]
            rule["http"] = {"methods": ["GET"], "paths": [{"exact": "/health"}]}
            rule["icmp"] = {"type": 8}
            rule["source"]["serviceAccounts"] = {"names": ["reader"]}
            rule["source"]["services"] = {"name": "service", "namespace": "portal"}
            node = b
            for k in path:
                node = node[k]
            node["futureSemanticRestriction"] = "x"
            rc, _, rows = run({"C3": R(0, enc(b))})
            self.assertNotEqual(rc, 0, label)
            c3 = [r for r in rows if r["id"] == "C3"][0]
            self.assertEqual(c3["category"], "UNSUPPORTED", label)

    def test_namespaced_policy_rejects_global_only_fields(self):
        for key, val in [("namespaceSelector", "team == 'restricted'"), ("applyOnForward", True),
                         ("doNotTrack", True), ("preDNAT", True)]:
            p = copy.deepcopy(NP); p["spec"][key] = val
            rc, _, rows = run({"C3": R(0, enc(p))})
            self.assertNotEqual(rc, 0, key)
            c3 = [r for r in rows if r["id"] == "C3"][0]
            self.assertEqual(c3["category"], "UNSUPPORTED", key)

    def test_unsupported_identity_diagnostic(self):
        # valid but unbound digest -> UNSUPPORTED (not PARSE_ERROR), safe identity retained
        p = copy.deepcopy(POD); p["status"]["containerStatuses"][0]["imageID"] = "containerd://sha256:" + "b" * 64
        rc, calls, rows = run({"I1": R(0, enc(p))})
        self.assertNotEqual(rc, 0)
        self.assertNotIn("C3", calls); self.assertNotIn("C4", calls); self.assertNotIn("C5", calls)
        i1 = [r for r in rows if r["id"] == "I1"][0]
        self.assertEqual(i1["category"], "UNSUPPORTED")
        self.assertIn("calico-node", i1["output"])
        self.assertNotIn(CANARY, i1["output"])
        # malformed -> PARSE_ERROR, empty output
        bad = copy.deepcopy(POD); bad["spec"]["containers"] = [None, 7]
        rc, _, rows = run({"I1": R(0, enc(bad))})
        self.assertNotEqual(rc, 0)
        i1 = [r for r in rows if r["id"] == "I1"][0]
        self.assertEqual(i1["category"], "PARSE_ERROR")
        self.assertEqual(i1["output"], "")

    def test_identity_config_digest_accepted(self):
        p = copy.deepcopy(POD)
        p["status"]["containerStatuses"][0]["imageID"] = "sha256:" + AMD64_CONFIG_HEX
        rc, calls, _ = run({"I1": R(0, enc(p))})
        self.assertEqual(rc, 0)
        self.assertIn("C3", calls)

    def test_identity_config_digest_prefix_rejected(self):
        p = copy.deepcopy(POD)
        p["status"]["containerStatuses"][0]["imageID"] = "containerd://sha256:" + AMD64_CONFIG_HEX
        rc, calls, _ = run({"I1": R(0, enc(p))})
        self.assertNotEqual(rc, 0)
        self.assertNotIn("C3", calls)

    def test_identity_bare_index_rejected(self):
        p = copy.deepcopy(POD)
        p["status"]["containerStatuses"][0]["imageID"] = "sha256:" + PINNED_HEX  # bare index, not prefixed
        rc, calls, _ = run({"I1": R(0, enc(p))})
        self.assertNotEqual(rc, 0)
        self.assertNotIn("C3", calls)

    def test_literal_api_paths(self):
        expected = {
            'C1': ['get', '--raw', '/apis/barmancloud.cnpg.io/v1/namespaces/portal/objectstores/portal-db-backup'],
            'C2': ['get', '--raw', '/apis/postgresql.cnpg.io/v1/namespaces/portal/clusters/portal-db'],
            'C3': ['get', '--raw', '/apis/crd.projectcalico.org/v1/networkpolicies'],
            'C4': ['get', '--raw', '/apis/crd.projectcalico.org/v1/globalnetworkpolicies'],
            'C5': ['get', '--raw', '/apis/crd.projectcalico.org/v1/felixconfigurations/default'],
        }
        contract = {rid: tail for rid, _, tail, _, _, _, _ in inv.READ_CONTRACT}
        for rid, tail in expected.items():
            self.assertEqual(contract[rid], tail, rid)

    def test_global_policy_fields_preserved(self):
        g = copy.deepcopy(GNP)
        g["spec"].update(namespaceSelector="team == 'restricted'", applyOnForward=True, doNotTrack=True, preDNAT=True)
        rc, _, _ = run({"C4": R(0, enc(g))})
        self.assertEqual(rc, 0)
        out = json.loads(inv.project_config("calico_gnp", enc(g), "list", None))[0]
        self.assertEqual(out["spec"]["namespaceSelector"], "team == 'restricted'")
        self.assertTrue(out["spec"]["applyOnForward"])

    def test_icmp_namespace_selector_preserved(self):
        base = copy.deepcopy(NP); base["spec"]["ingress"][0]["protocol"] = "ICMP"
        changed = copy.deepcopy(base); changed["spec"]["ingress"][0]["icmp"] = {"type": 8}
        a = json.loads(inv.project_config("calico_np", enc(base), "list", None))[0]
        b = json.loads(inv.project_config("calico_np", enc(changed), "list", None))[0]
        self.assertNotEqual(json.dumps(a, sort_keys=True), json.dumps(b, sort_keys=True))
        self.assertEqual(b["spec"]["ingress"][0]["icmp"]["type"], 8)
        gnp = copy.deepcopy(GNP); gnp["spec"]["namespaceSelector"] = "team == 'restricted'"
        g = json.loads(inv.project_config("calico_gnp", enc(gnp), "list", None))[0]
        self.assertEqual(g["spec"]["namespaceSelector"], "team == 'restricted'")

    def test_scoped_list_namespace_rejected(self):
        for rid in ("S1", "S2"):
            bad = copy.deepcopy(POD); bad["metadata"]["namespace"] = "other"
            rc, _, _ = run({rid: R(0, enc(bad))})
            self.assertNotEqual(rc, 0, rid)

    def test_http_paths_malformed_rejected(self):
        for val in (False, 0, {}, [None]):
            bad = copy.deepcopy(NP); bad["spec"]["ingress"][0]["http"] = {"paths": val}
            with self.assertRaises(ValueError):
                inv.project_config("calico_np", enc(bad), "list", None)

    def test_container_port_range_rejected(self):
        for val in (-1, 65536):
            bad = copy.deepcopy(POD); bad["spec"]["containers"][0]["ports"][0]["containerPort"] = val
            with self.assertRaises(ValueError):
                inv.project_config("identity", enc(bad), "list", None)


if __name__ == "__main__":
    unittest.main()
