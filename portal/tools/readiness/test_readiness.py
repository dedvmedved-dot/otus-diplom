#!/usr/bin/env python3
"""Offline tests for the readiness wrapper (no live cluster/SSH).

Injected transport is a fake kubectl serving realistic per-read fixtures;
injected clock covers gate expiry. Predicates assert exact verdicts (PASS/FAIL/
INCONCLUSIVE), not a loose PASS-or-INCONCLUSIVE. No live network/clock/WAL.
"""
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import wrapper  # noqa: E402


def fake_kubectl(fixtures):
    """Fake kubectl that maps `get --raw <path>` to a fixture file (argv-only, no shell)."""
    d = tempfile.mkdtemp()
    script = os.path.join(d, "kubectl")
    with open(script, "w") as f:
        f.write("#!/usr/bin/env python3\nimport sys, json\n")
        f.write("path = sys.argv[sys.argv.index('--raw')+1]\n")
        f.write("fix = %r\n" % fixtures)
        f.write("if path in fix:\n  print(json.dumps(fix[path]))\n  sys.exit(0)\n")
        f.write("sys.exit(1)\n")
    os.chmod(script, 0o755)
    return script


def gate(**kw):
    g = {"mode": "LIVE", "context": wrapper.CONTEXT, "source_sha": "a" * 40,
         "package_sha256": wrapper.package_hash(), "issued_at_utc": "2026-11-04T00:00:00Z",
         "expiry_hours": 24, "run_budget_consumed": False}
    g.update(kw)
    return g


def epoc():
    import calendar
    return calendar.timegm((2026, 11, 4, 0, 0, 0))


class TestGate(unittest.TestCase):
    def test_valid(self):
        ok, err = wrapper.validate_gate(gate(), epoc() + 60)
        self.assertTrue(ok, err)

    def test_hash_mismatch(self):
        ok, _ = wrapper.validate_gate(gate(package_sha256="0" * 64), epoc() + 60)
        self.assertFalse(ok)

    def test_future(self):
        ok, _ = wrapper.validate_gate(gate(issued_at_utc="2026-11-05T00:00:00Z"), epoc() + 60)
        self.assertFalse(ok)

    def test_expired(self):
        ok, _ = wrapper.validate_gate(gate(), epoc() + 25 * 3600)
        self.assertFalse(ok)

    def test_expiry_over_24(self):
        ok, _ = wrapper.validate_gate(gate(expiry_hours=48), epoc() + 60)
        self.assertFalse(ok)

    def test_bad_mode(self):
        ok, _ = wrapper.validate_gate(gate(mode="TEST_ONLY"), epoc() + 60)
        self.assertFalse(ok)


class TestPredicates(unittest.TestCase):
    def test_hc_db_ready(self):
        d = {"kind": "Cluster", "spec": {"instances": 3}, "status": {"instances": 3, "readyInstances": 3,
             "conditions": [{"type": "Ready", "status": "True"}]}}
        self.assertEqual(wrapper.pred_hc_db(d), (wrapper.PASS, "3/3/3 Ready"))

    def test_hc_db_fail(self):
        d = {"kind": "Cluster", "spec": {"instances": 3}, "status": {"instances": 3, "readyInstances": 1,
             "conditions": [{"type": "Ready", "status": "True"}]}}
        self.assertEqual(wrapper.pred_hc_db(d)[0], wrapper.FAIL)

    def test_hc_db_missing(self):
        d = {"kind": "Cluster", "spec": {}, "status": {}}
        self.assertEqual(wrapper.pred_hc_db(d)[0], wrapper.INCONCLUSIVE)

    def test_hc_gw_programmed(self):
        d = {"metadata": {"generation": 1}, "status": {"conditions": [
            {"type": "Accepted", "status": "True", "observedGeneration": 1},
            {"type": "Programmed", "status": "True", "observedGeneration": 1}]}}
        self.assertEqual(wrapper.pred_hc_gw(d)[0], wrapper.PASS)

    def test_hc_gw_false(self):
        d = {"metadata": {"generation": 1}, "status": {"conditions": [
            {"type": "Programmed", "status": "False", "observedGeneration": 1}]}}
        self.assertEqual(wrapper.pred_hc_gw(d)[0], wrapper.FAIL)

    def test_pr5_two_items_fail(self):
        d = {"items": [{"spec": {"type": "LoadBalancer", "externalTrafficPolicy": "Local",
             "ports": [{"port": 443, "targetPort": 10443, "protocol": "TCP"}]},
             "status": {"loadBalancer": {"ingress": [{"ip": "1.2.3.4"}]}}},
             {"spec": {"type": "ClusterIP", "ports": []}, "status": {}}]}
        self.assertEqual(wrapper.pred_pr5(d)[0], wrapper.FAIL)

    def test_pr3_empty_inconclusive(self):
        d = {"kind": "EndpointSliceList", "apiVersion": "discovery.k8s.io/v1", "items": []}
        self.assertEqual(wrapper.pred_pr3(d)[0], wrapper.INCONCLUSIVE)


class TestReservation(unittest.TestCase):
    def test_rerun_blocked(self):
        d = tempfile.mkdtemp()
        p = os.path.join(d, "run.reserved")
        self.assertIsNotNone(wrapper.atomic_reserve(p))
        self.assertIsNone(wrapper.atomic_reserve(p))


class TestWAL(unittest.TestCase):
    def _docs(self):
        cluster = {"metadata": {"name": "portal-db", "uid": "c-uid"}, "status": {"currentPrimary": "portal-db-1"}}
        pod = {"metadata": {"name": "portal-db-1", "uid": "p-uid",
                            "labels": {"cnpg.io/instanceRole": "primary"},
                            "ownerReferences": [{"uid": "c-uid", "kind": "Cluster", "name": "portal-db"}]},
               "spec": {"nodeName": "node-01"},
               "status": {"podIP": "10.244.1.2", "containerStatuses": [{"name": "postgres", "restartCount": 0}]}}
        return cluster, pod

    def _clock(self):
        return {"bound": 5, "source": "ntp", "provenance_sha256": "a" * 64, "node": "node-01",
                "backend": "exporter", "observed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "validity_hours": 24}

    def test_clock_missing(self):
        c, p = self._docs()
        disp, m, d = wrapper.wal.wal_sample(c, p, "", c, p, None)
        self.assertEqual(disp, wrapper.INCONCLUSIVE)
        self.assertIn("clock", d)

    def test_clock_bare_number_rejected(self):
        ok, _ = wrapper.wal.validate_clock(5)
        self.assertFalse(ok)

    def test_clock_trusted_flag_rejected(self):
        ok, _ = wrapper.wal.validate_clock({"trusted": True, "bound": 5})
        self.assertFalse(ok)

    def test_clock_nan_rejected(self):
        ev = self._clock(); ev["bound"] = float("nan")
        ok, _ = wrapper.wal.validate_clock(ev)
        self.assertFalse(ok)

    def test_identity_swap(self):
        c, p = self._docs()
        p2 = {"metadata": {"name": "portal-db-1", "uid": "other"}, "status": {"podIP": "10.244.1.2"}}
        disp, _, _ = wrapper.wal.wal_sample(c, p, "", c, p2, self._clock())
        self.assertEqual(disp, wrapper.INCONCLUSIVE)

    def test_failure_growth_wins(self):
        c, p = self._docs()
        metrics = "cnpg_pg_stat_archiver_failed_count 1\ncnpg_pg_stat_archiver_archived_count 10\ncnpg_pg_stat_archiver_last_archived_time 100\ncnpg_pg_stat_archiver_last_failed_time 99\ncnpg_pg_stat_archiver_stats_reset_time 1\n"
        baseline = {"cnpg_pg_stat_archiver_failed_count": 0, "cnpg_pg_stat_archiver_archived_count": 5,
                    "cnpg_pg_stat_archiver_last_archived_time": 50, "cnpg_pg_stat_archiver_last_failed_time": 0,
                    "cnpg_pg_stat_archiver_stats_reset_time": 1}
        disp, _, _ = wrapper.wal.wal_sample(c, p, metrics, c, p, self._clock(), baseline=baseline, op_end_utc=60)
        self.assertEqual(disp, wrapper.FAIL)

    def test_missing_series(self):
        c, p = self._docs()
        disp, _, _ = wrapper.wal.wal_sample(c, p, "", c, p, self._clock())
        self.assertEqual(disp, wrapper.INCONCLUSIVE)


class TestMain(unittest.TestCase):
    def _run(self, stage, fixtures, gate_override=None):
        d = tempfile.mkdtemp()
        g = os.path.join(d, "gate.json")
        json.dump(gate(**(gate_override or {})), open(g, "w"))
        with patch.object(wrapper.time, "time", return_value=epoc() + 60), \
             patch.object(wrapper.time, "sleep", return_value=None), \
             patch.object(wrapper.time, "monotonic", return_value=1.0):
            rc = wrapper.main(["--gate", g, "--out", os.path.join(d, "out.json"),
                               "--state-dir", os.path.join(d, "state"), "--stage", stage,
                               "--kubectl", fake_kubectl(fixtures), "--now", str(epoc() + 60)])
        out = os.path.join(d, "out.json")
        j = json.load(open(out)) if os.path.exists(out) else None
        return rc, j

    def test_unknown_stage_nonzero(self):
        rc, _ = self._run("TYPO", {})
        self.assertEqual(rc, 2)

    def test_s0_fail_closed_without_wal(self):
        # Good HC-DB/ARCH-STATE fixtures, but WAL has no live transport -> aggregate INCONCLUSIVE, exit 1.
        fixtures = {
            "/apis/postgresql.cnpg.io/v1/namespaces/portal/clusters/portal-db":
                {"spec": {"instances": 3}, "status": {"instances": 3, "readyInstances": 3,
                 "conditions": [{"type": "Ready", "status": "True"}, {"type": "ContinuousArchiving", "status": "True"}]}},
            "/api/v1/namespaces/cnpg-system/pods?labelSelector=app.kubernetes.io%2Fname%3Dcloudnative-pg&limit=200":
                {"apiVersion": "v1", "kind": "PodList", "items": [{"status": {"phase": "Running"}}]},
            "/apis/discovery.k8s.io/v1/namespaces/kube-system/endpointslices?labelSelector=kubernetes.io%2Fservice-name%3Dkube-dns&limit=200":
                {"apiVersion": "discovery.k8s.io/v1", "kind": "EndpointSliceList", "items": [{"endpoints": [{"conditions": {"ready": True}, "addresses": ["10.0.0.1"]}]}]},
            "/apis/discovery.k8s.io/v1/namespaces/default/endpointslices?labelSelector=kubernetes.io%2Fservice-name%3Dkubernetes&limit=200":
                {"apiVersion": "discovery.k8s.io/v1", "kind": "EndpointSliceList", "items": [{"endpoints": [{"addresses": ["172.30.140.101", "172.30.140.102", "172.30.140.103"], "conditions": {"ready": True}}], "ports": [{"port": 6443}]}]},
        }
        rc, j = self._run("S0", fixtures)
        self.assertEqual(rc, 1, j)
        self.assertEqual(j["aggregate"], wrapper.INCONCLUSIVE, j)


if __name__ == "__main__":
    unittest.main(verbosity=2)
