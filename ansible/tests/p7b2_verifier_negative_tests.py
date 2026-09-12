#!/usr/bin/env python3
"""
TASK-P7B2-R1 — P7B2 verifier negative tests (offline).
Uses the SAME shared validation logic as the real verifier
(ansible/tools/p7b2_verify_logic.py). No parallel implementation.
"""

import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import p7b2_verify_logic as V

D = V.EXPECTED_DIGEST
GOOD_ARGS = ["--cert-dir=/tmp", "--secure-port=10250",
             "--kubelet-preferred-address-types=InternalIP,ExternalIP,Hostname",
             "--kubelet-use-node-status-port", "--metric-resolution=15s",
             "--kubelet-certificate-authority=/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"]
GOOD_REQ = f"registry.k8s.io/metrics-server/metrics-server:v0.8.1@{D}"
GOOD_IID = f"registry.k8s.io/metrics-server/metrics-server@{D}"


def nm(items):
    return {"kind": "NodeMetricsList", "items": items}


def item(name, cpu="1n", mem="1Ki", ts="2026-09-11T23:00:00Z", window="20s"):
    return {"metadata": {"name": name}, "usage": {"cpu": cpu, "memory": mem},
            "timestamp": ts, "window": window}


GOOD_ITEMS = [item("node-01"), item("node-02"), item("node-03")]

T = []
def t(name, expect_fail, fn):
    T.append((name, expect_fail, fn))

t("insecure kubelet flag", True, lambda: V.validate_args(["--kubelet-insecure-tls"]))
t("deprecated insecure flag", True, lambda: V.validate_args(["--deprecated-kubelet-completely-insecure"]))
t("kubelet CA absent", True, lambda: V.validate_args(["--secure-port=10250"]))
t("wrong image version", True, lambda: V.validate_image(f"registry.k8s.io/metrics-server/metrics-server@{D}", GOOD_IID))
t("wrong image digest", True, lambda: V.validate_image(GOOD_REQ, "registry.k8s.io/metrics-server/metrics-server@sha256:deadbeef"))
t("deployment unavailable", True, lambda: V.validate_deploy(0, 1))
t("apiservice unavailable", True, lambda: V.validate_apiservice("False"))
t("nodemetrics count=2", True, lambda: V.validate_nodemetrics(nm(GOOD_ITEMS[:2])))
t("node-01 missing", True, lambda: V.validate_nodemetrics(nm([i for i in GOOD_ITEMS if i["metadata"]["name"] != "node-01"])))
t("node-02 missing", True, lambda: V.validate_nodemetrics(nm([i for i in GOOD_ITEMS if i["metadata"]["name"] != "node-02"])))
t("node-03 missing", True, lambda: V.validate_nodemetrics(nm([i for i in GOOD_ITEMS if i["metadata"]["name"] != "node-03"])))
t("cpu empty", True, lambda: V.validate_nodemetrics(nm([item("node-01", cpu=""), item("node-02"), item("node-03")])))
t("memory empty", True, lambda: V.validate_nodemetrics(nm([item("node-01", mem=""), item("node-02"), item("node-03")])))
t("timestamp missing", True, lambda: V.validate_nodemetrics(nm([item("node-01", ts=""), item("node-02"), item("node-03")])))
t("malformed timestamp", True, lambda: V.validate_freshness(nm([item("node-01", ts="not-a-time"), item("node-02"), item("node-03")])))
t("stale timestamp >120s", True, lambda: V.validate_freshness(nm([item("node-01", ts="2026-09-11T20:00:00Z"), item("node-02"), item("node-03")]), now=datetime(2026,9,11,20,3,0,tzinfo=timezone.utc)))
t("timestamp >10s future", True, lambda: V.validate_freshness(nm([item("node-01", ts="2026-09-11T20:00:30Z"), item("node-02"), item("node-03")]), now=datetime(2026,9,11,20,0,0,tzinfo=timezone.utc)))
t("window missing", True, lambda: V.validate_nodemetrics(nm([item("node-01", window=""), item("node-02"), item("node-03")])))
t("window zero/invalid", True, lambda: V.validate_freshness(nm([item("node-01", window="0s"), item("node-02"), item("node-03")])))
t("kubectl top pods empty", True, lambda: V.validate_top_pods("NAMESPACE   NAME   CPU   MEMORY\n"))
t("kubectl top nodes missing node", True, lambda: V.validate_top_nodes("node-01\nnode-02\n"))
t("pending serving CSR", True, lambda: V.validate_csr([{"spec":{"signerName":"kubernetes.io/kubelet-serving"},"status":{"conditions":[]}}]))
t("serverTLSBootstrap false", True, lambda: V.validate_kubelet_cfg("rotateCertificates: true"))
t("cluster-CA trust failure", True, lambda: V.validate_ca_trust(1))
t("P6D route missing", True, lambda: V.validate_route("default via 192.168.194.1"))
t("VLAN143 missing", True, lambda: V.validate_vlan143("bond0.140"))
t("Velero present", True, lambda: V.validate_velero(["velero"]))
t("recovery old UID missing", True, lambda: V.validate_recovery("", "uid2", "YES", "YES", "node-01\nnode-02\nnode-03"))
t("recovery new UID missing", True, lambda: V.validate_recovery("uid1", "", "YES", "YES", "node-01\nnode-02\nnode-03"))
t("recovery UID unchanged", True, lambda: V.validate_recovery("uid1", "uid1", "YES", "YES", "node-01\nnode-02\nnode-03"))
t("recovery APIService marker missing", True, lambda: V.validate_recovery("uid1", "uid2", "NO", "YES", "node-01\nnode-02\nnode-03"))
t("recovery NodeMetrics marker missing", True, lambda: V.validate_recovery("uid1", "uid2", "YES", "NO", "node-01\nnode-02\nnode-03"))
t("recovery top-nodes partial", True, lambda: V.validate_recovery("uid1", "uid2", "YES", "YES", "node-01\nnode-02\n"))
t("README falsely P7B2 FINAL ACCEPTED", True, lambda: V.validate_readme("P7B1 FINAL ACCEPTED\nP7B2 FINAL ACCEPTED\nP7C NOT AUTHORIZED\nP8 NOT AUTHORIZED"))
t("README authorizes P7C", True, lambda: V.validate_readme("P7B1 FINAL ACCEPTED\nP7B2 IN PROGRESS\nP7C AUTHORIZED\nP8 NOT AUTHORIZED"))
t("final PASS before gates", True, lambda: V.validate_gate_order(["FINAL", "K8S", "NODES"]))

# ── R2 static zero-mutation cases ──────────────────────────────────────────────
_VERIFIER = os.path.join(os.path.dirname(__file__), "..", "playbooks", "p7b2-final-readonly-verify.yml")
def _vtext():
    return open(_VERIFIER).read()

def _no_copy():
    if "ansible.builtin.copy" in _vtext():
        raise AssertionError("verifier contains ansible.builtin.copy")

def _no_tmp_dest():
    if "dest: /tmp/p7b2_verify_logic.py" in _vtext():
        raise AssertionError("verifier writes /tmp/p7b2_verify_logic.py")

def _no_tmp_import():
    if "/tmp/p7b2_verify_logic.py" in _vtext():
        raise AssertionError("verifier imports /tmp/p7b2_verify_logic.py")

def _controller_imports_repo():
    txt = _vtext()
    if "sys.path.insert" not in txt or "p7b2_verify_logic" not in txt:
        raise AssertionError("controller-side validation does not import repo shared logic")

def _changed_when_false():
    if "changed_when: false" not in _vtext():
        raise AssertionError("verifier read-only tasks missing changed_when: false")

t("verifier has no ansible.builtin.copy", False, _no_copy)
t("verifier has no dest /tmp/p7b2_verify_logic.py", False, _no_tmp_dest)
t("verifier does not import /tmp/p7b2_verify_logic.py", False, _no_tmp_import)
t("controller-side validation imports repo shared logic", False, _controller_imports_repo)
t("verifier read-only tasks use changed_when: false", False, _changed_when_false)

# ── R3 source ordering / control-flow tests ───────────────────────────────────
FINAL_MARKER = "P7B2_FINAL_READONLY_VERIFIER_PASS"
HOST_TASK = "Node kubelet TLS + P6D route + P7A VLAN143"
FINAL_TASK = "P7B2 final PASS gate after all host-level checks"
CONTROLLER_TASK = "Controller-side validation via shared logic"

def _positions(text):
    return {
        "final": text.find(FINAL_MARKER),
        "host": text.find(HOST_TASK),
        "final_task": text.find(FINAL_TASK),
        "controller": text.find(CONTROLLER_TASK),
    }

def _order_pass(text):
    p = _positions(text)
    assert all(v >= 0 for v in p.values()), f"missing section: {p}"
    assert text.count(FINAL_MARKER) == 1, f"final marker count != 1: {text.count(FINAL_MARKER)}"
    assert p["final"] > p["host"], "final marker before host-level task"
    assert p["final"] > p["final_task"], "final marker before final task"
    assert p["final_task"] > p["host"], "final task before host-level task"
    assert p["final"] > p["controller"], "final marker inside/before controller task"
    assert "any_errors_fatal: true" in text, "any_errors_fatal missing/false"

def _order_uniq(text):
    assert text.count(FINAL_MARKER) == 1, f"final marker count != 1"

def _order_host_before_final(text):
    p = _positions(text)
    assert p["host"] >= 0, "host-level task missing"
    assert p["final"] > p["host"], "final marker before host-level task"

def _order_not_in_controller(text):
    p = _positions(text)
    assert p["final"] > p["controller"], "final marker in controller task"

def _order_final_task_after_host(text):
    p = _positions(text)
    assert p["final_task"] > p["host"], "final task before host-level task"

def _order_any_errors_fatal(text):
    assert "any_errors_fatal: true" in text, "any_errors_fatal missing/false"

def _order_zero_mutation(text):
    if "ansible.builtin.copy" in text or "ansible.builtin.template" in text:
        raise AssertionError("mutating ansible file task present")

t("ordering: final marker unique (==1)", False, lambda: _order_uniq(_vtext()))
t("ordering: final marker after host-level task", False, lambda: _order_host_before_final(_vtext()))
t("ordering: final marker not in controller task", False, lambda: _order_not_in_controller(_vtext()))
t("ordering: final task after host-level task", False, lambda: _order_final_task_after_host(_vtext()))
t("ordering: any_errors_fatal true", False, lambda: _order_any_errors_fatal(_vtext()))
t("ordering: no mutating ansible file tasks", False, lambda: _order_zero_mutation(_vtext()))

# broken-order fixture tests (synthetic source)
t("fixture: final marker before host-level -> FAIL", True, lambda: _order_host_before_final("P7B2_FINAL_READONLY_VERIFIER_PASS\n" + HOST_TASK))
t("fixture: duplicate final markers -> FAIL", True, lambda: _order_uniq(FINAL_MARKER + "\n" + FINAL_MARKER))
t("fixture: host-level task missing -> FAIL", True, lambda: _order_host_before_final("x\n" + FINAL_MARKER))

t("clean fixture", False, lambda: (
    V.validate_args(GOOD_ARGS),
    V.validate_image(GOOD_REQ, GOOD_IID),
    V.validate_deploy(1, 1),
    V.validate_apiservice("True"),
    V.validate_nodemetrics(nm(GOOD_ITEMS)),
    V.validate_freshness(nm(GOOD_ITEMS), now=datetime(2026, 9, 11, 23, 0, 5, tzinfo=timezone.utc)),
    V.validate_top_nodes("node-01\nnode-02\nnode-03\n"),
    V.validate_top_pods("NAMESPACE NAME CPU MEMORY\nkube-system metrics-server 5m 32Mi\n"),
    V.validate_csr([]),
    V.validate_kubelet_cfg("serverTLSBootstrap: true\nrotateCertificates: true\n"),
    V.validate_ca_trust(0),
    V.validate_route("172.30.20.0/24 via 172.30.140.1 dev bond0.140"),
    V.validate_vlan143("bond0.143 172.30.143.1"),
    V.validate_velero([]),
    V.validate_readme("P7B1 FINAL ACCEPTED\nP7B2 IN PROGRESS\nP7C NOT AUTHORIZED\nP8 NOT AUTHORIZED"),
    V.validate_recovery("uid1", "uid2", "YES", "YES", "node-01\nnode-02\nnode-03"),
    V.validate_gate_order(["K8S","NODES","METRICS_SERVER","APISERVICE","NODE_METRICS","FRESHNESS","TOP_NODES","TOP_PODS","RECOVERY","FINAL"]),
))


def main():
    total = 0
    failed = 0
    for name, expect_fail, fn in T:
        total += 1
        actual = "PASS"
        try:
            fn()
        except Exception:
            actual = "FAIL"
        expect = "FAIL" if expect_fail else "PASS"
        ok = actual == expect
        print(f"--- {name} --- expected={expect} actual={actual} {'OK' if ok else 'MISMATCH'}")
        if not ok:
            failed += 1
    print(f"\nNEGATIVE_TESTS_TOTAL={total}")
    print(f"NEGATIVE_TESTS_FAILED={failed}")
    print(f"HARNESS_EXIT={0 if failed == 0 else 1}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
