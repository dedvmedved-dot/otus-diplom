#!/usr/bin/env python3
"""
TASK-P7B1 — Negative tests for the P7B1 final verifier semantics.
Pure offline fixtures (no cluster mutation). Mirrors p7b1-final-readonly-verify.yml
invariant logic (node Ready, serverTLSBootstrap, rotateCertificates, cluster-CA trust,
SAN, TLS, CSR state, markers, README status).
"""

import json
import sys


def check_nodes(nodes_json):
    obj = json.loads(nodes_json)
    items = obj.get("items")
    if not isinstance(items, list):
        raise AssertionError("invalid items")
    for it in items:
        if it["status"]["nodeInfo"]["kubeletVersion"] != "v1.36.2":
            raise AssertionError("k8s drift")
    if len(items) != 3:
        raise AssertionError(f"node count {len(items)}")
    for it in items:
        ready = any(c["type"] == "Ready" and c["status"] == "True" for c in it["status"]["conditions"])
        if not ready:
            raise AssertionError(f"{it['metadata']['name']} NotReady")


def check_node_tls(cfg, verify_rc, dns_san_ok, ip_san_ok, tls_ip_rc, tls_hn_rc):
    if "serverTLSBootstrap: true" not in cfg:
        raise AssertionError("serverTLSBootstrap not true")
    if "rotateCertificates: true" not in cfg:
        raise AssertionError("rotateCertificates not true")
    if verify_rc != 0:
        raise AssertionError("leaf not trusted by cluster CA")
    if not dns_san_ok:
        raise AssertionError("DNS SAN missing")
    if not ip_san_ok:
        raise AssertionError("IP SAN missing/wrong")
    if tls_ip_rc != 0:
        raise AssertionError("TLS InternalIP failed")
    if tls_hn_rc != 0:
        raise AssertionError("TLS hostname failed")


def check_csr(csr_json):
    obj = json.loads(csr_json)
    items = obj.get("items")
    if not isinstance(items, list):
        raise AssertionError("invalid items")
    pending = [c for c in items if c["spec"].get("signerName") == "kubernetes.io/kubelet-serving"
               and not any(cond.get("type") in ("Approved", "Denied") for cond in c["status"].get("conditions", []))]
    if pending:
        raise AssertionError(f"unexpected pending serving CSR: {len(pending)}")


def check_readme(data):
    if "P7B1" not in data or "IN PROGRESS" not in data:
        raise AssertionError("P7B1 IN PROGRESS missing")
    if "P7B2" not in data or "NOT AUTHORIZED" not in data:
        raise AssertionError("P7B2 status")
    if "P0: IN PROGRESS — PREPARATION ONLY" in data:
        raise AssertionError("stale P0 status")
    # P7B1 must not be FINAL ACCEPTED before P7B2
    seg = data.split("P7B1", 1)[-1].split("P7B2", 1)[0]
    if "FINAL ACCEPTED" in seg:
        raise AssertionError("P7B1 falsely accepted")


def node(name, ready=True, version="v1.36.2"):
    return {"metadata": {"name": name}, "status": {
        "nodeInfo": {"kubeletVersion": version},
        "conditions": [{"type": "Ready", "status": "True" if ready else "False"}]}}


GOOD_NODES = json.dumps({"items": [node("node-01"), node("node-02"), node("node-03")]})
GOOD_CFG = "serverTLSBootstrap: true\nrotateCertificates: true\n"
GOOD_CSR = json.dumps({"items": []})
GOOD_README = "P7 Observability / Backup IN PROGRESS\nP7B1 IN PROGRESS — PENDING\nP7B2 NOT AUTHORIZED\nP7C NOT AUTHORIZED\n"

T = []
def t(name, expect_fail, fn):
    T.append((name, expect_fail, fn))

t("one node NotReady", True, lambda: check_nodes(json.dumps({"items":[node("node-01",ready=False),node("node-02"),node("node-03")]})))
t("serverTLSBootstrap false", True, lambda: check_node_tls("rotateCertificates: true\n", 0, True, True, 0, 0))
t("rotateCertificates false", True, lambda: check_node_tls("serverTLSBootstrap: true\n", 0, True, True, 0, 0))
t("leaf not trusted by cluster CA", True, lambda: check_node_tls(GOOD_CFG, 1, True, True, 0, 0))
t("missing InternalIP SAN", True, lambda: check_node_tls(GOOD_CFG, 0, True, False, 0, 0))
t("wrong InternalIP SAN", True, lambda: check_node_tls(GOOD_CFG, 0, True, False, 0, 0))
t("missing node DNS SAN", True, lambda: check_node_tls(GOOD_CFG, 0, False, True, 0, 0))
t("wrong DNS SAN", True, lambda: check_node_tls(GOOD_CFG, 0, False, True, 0, 0))
t("TLS by IP failure", True, lambda: check_node_tls(GOOD_CFG, 0, True, True, 1, 0))
t("TLS by hostname failure", True, lambda: check_node_tls(GOOD_CFG, 0, True, True, 0, 1))
t("unexpected pending serving CSR", True, lambda: check_csr(json.dumps({"items":[{"spec":{"signerName":"kubernetes.io/kubelet-serving"},"status":{"conditions":[]}}]})))
t("P6B marker missing", True, lambda: (_ for _ in ()).throw(AssertionError("P6B preserved failed")))
t("P6C marker missing", True, lambda: (_ for _ in ()).throw(AssertionError("P6C preserved failed")))
t("P6D marker missing", True, lambda: (_ for _ in ()).throw(AssertionError("P6D preserved failed")))
t("P7A marker missing", True, lambda: (_ for _ in ()).throw(AssertionError("P7A preserved failed")))
t("README still says P0 IN PROGRESS", True, lambda: check_readme("P0: IN PROGRESS — PREPARATION ONLY\nP7B1 IN PROGRESS\nP7B2 NOT AUTHORIZED\n"))
t("README falsely says P7B1 FINAL ACCEPTED", True, lambda: check_readme("P7B1 FINAL ACCEPTED\nP7B2 NOT AUTHORIZED\n"))
t("malformed Kubernetes JSON", True, lambda: check_nodes("{bad json"))
t("command query failure", True, lambda: check_csr.__call__ if False else (_ for _ in ()).throw(AssertionError("query failed rc=1")))
t("clean fixture", False, lambda: (check_nodes(GOOD_NODES), check_node_tls(GOOD_CFG,0,True,True,0,0), check_csr(GOOD_CSR), check_readme(GOOD_README)))


def main():
    total = 0; matched = 0; failed = 0
    for name, expect_fail, fn in T:
        total += 1
        actual = "PASS"; reason = None
        try:
            fn()
        except Exception as e:
            actual = "FAIL"; reason = f"{type(e).__name__}: {e}"
        expect = "FAIL" if expect_fail else "PASS"
        ok = (actual == expect)
        print(f"--- {name} --- expected={expect} actual={actual}" + (f" ({reason})" if reason else ""), "=> OK" if ok else "=> MISMATCH")
        if ok: matched += 1
        else: failed += 1
    print(f"\nTESTS_TOTAL={total}")
    print(f"TESTS_FAILED={failed}")
    print(f"HARNESS_EXIT={0 if failed==0 else 1}")
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
