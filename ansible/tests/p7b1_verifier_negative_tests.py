#!/usr/bin/env python3
"""
TASK-P7B1-R1 — P7B1 verifier negative tests (offline, real logic).
Exercises the actual verification semantics (extracted/mirrored from
p7b1-final-readonly-verify.yml), not placeholder raises.
"""

import json
import sys


# ── extracted/mirrored verifier logic ──────────────────────────────────────────

def check_nodes(nodes_json):
    obj = json.loads(nodes_json)
    items = obj.get("items")
    if not isinstance(items, list):
        raise AssertionError("nodes invalid items")
    for it in items:
        if it["status"]["nodeInfo"]["kubeletVersion"] != "v1.36.2":
            raise AssertionError("k8s drift")
    if len(items) != 3:
        raise AssertionError(f"node count {len(items)}")
    for it in items:
        ready = any(c["type"] == "Ready" and c["status"] == "True" for c in it["status"]["conditions"])
        if not ready:
            raise AssertionError(f"{it['metadata']['name']} NotReady")


def check_tls(cfg, verify_rc, san, host, ip, tls_ip_rc, tls_hn_rc):
    if "serverTLSBootstrap: true" not in cfg:
        raise AssertionError("serverTLSBootstrap not true")
    if "rotateCertificates: true" not in cfg:
        raise AssertionError("rotateCertificates not true")
    if verify_rc != 0:
        raise AssertionError("leaf not cluster-CA trusted")
    if host not in san:
        raise AssertionError("DNS SAN missing")
    if ip not in san:
        raise AssertionError("IP SAN missing/wrong")
    if tls_ip_rc != 0:
        raise AssertionError("TLS IP failure")
    if tls_hn_rc != 0:
        raise AssertionError("TLS hostname failure")


def check_csr(csr_json):
    obj = json.loads(csr_json)
    items = obj.get("items")
    if not isinstance(items, list):
        raise AssertionError("csr invalid items")
    pending = [c for c in items if c["spec"].get("signerName") == "kubernetes.io/kubelet-serving"
               and not any(cond.get("type") in ("Approved", "Denied") for cond in c["status"].get("conditions", []))]
    if pending:
        raise AssertionError(f"pending serving CSR: {len(pending)}")


def check_preservation(rc, output, marker):
    if rc != 0:
        raise AssertionError(f"canonical verifier rc != 0: {rc}")
    if marker not in output:
        raise AssertionError(f"marker missing: {marker}")


def check_readme(data):
    if "P7B1" not in data or "IN PROGRESS" not in data:
        raise AssertionError("P7B1 IN PROGRESS missing")
    if "P7B2" not in data or "NOT AUTHORIZED" not in data:
        raise AssertionError("P7B2 NOT AUTHORIZED missing")
    if "P0: IN PROGRESS — PREPARATION ONLY" in data:
        raise AssertionError("stale P0")
    seg = data.split("P7B1", 1)[-1].split("P7B2", 1)[0]
    if "FINAL ACCEPTED" in seg:
        raise AssertionError("P7B1 falsely accepted")


# ── fixtures ───────────────────────────────────────────────────────────────────

def node(name, ready=True, version="v1.36.2"):
    return {"metadata": {"name": name}, "status": {
        "nodeInfo": {"kubeletVersion": version},
        "conditions": [{"type": "Ready", "status": "True" if ready else "False"}]}}

GOOD_NODES = json.dumps({"items": [node("node-01"), node("node-02"), node("node-03")]})
GOOD_CFG = "serverTLSBootstrap: true\nrotateCertificates: true\n"
GOOD_SAN = "DNS:node-01, IP Address:172.30.140.101"
GOOD_CSR = json.dumps({"items": []})
GOOD_README = "P7B1 IN PROGRESS — PENDING\nP7B2 NOT AUTHORIZED\nP7C NOT AUTHORIZED\n"


T = []
def t(name, expect_fail, fn):
    T.append((name, expect_fail, fn))

t("P6D command rc != 0", True, lambda: check_preservation(1, "P6D_FINAL_READONLY_VERIFIER_PASS", "P6D_FINAL_READONLY_VERIFIER_PASS"))
t("P6D PASS marker missing", True, lambda: check_preservation(0, "some output", "P6D_FINAL_READONLY_VERIFIER_PASS"))
t("P7A command rc != 0", True, lambda: check_preservation(2, "P7A_FINAL_READONLY_VERIFIER_PASS", "P7A_FINAL_READONLY_VERIFIER_PASS"))
t("P7A PASS marker missing", True, lambda: check_preservation(0, "no marker", "P7A_FINAL_READONLY_VERIFIER_PASS"))
t("one node NotReady", True, lambda: check_nodes(json.dumps({"items":[node("node-01",ready=False),node("node-02"),node("node-03")]})))
t("serverTLSBootstrap false", True, lambda: check_tls("rotateCertificates: true\n", 0, GOOD_SAN, "node-01", "172.30.140.101", 0, 0))
t("rotateCertificates false", True, lambda: check_tls("serverTLSBootstrap: true\n", 0, GOOD_SAN, "node-01", "172.30.140.101", 0, 0))
t("leaf not cluster-CA trusted", True, lambda: check_tls(GOOD_CFG, 1, GOOD_SAN, "node-01", "172.30.140.101", 0, 0))
t("missing DNS SAN", True, lambda: check_tls(GOOD_CFG, 0, "IP Address:172.30.140.101", "node-01", "172.30.140.101", 0, 0))
t("wrong DNS SAN", True, lambda: check_tls(GOOD_CFG, 0, "DNS:node-02", "node-01", "172.30.140.101", 0, 0))
t("missing InternalIP SAN", True, lambda: check_tls(GOOD_CFG, 0, "DNS:node-01", "node-01", "172.30.140.101", 0, 0))
t("wrong InternalIP SAN", True, lambda: check_tls(GOOD_CFG, 0, "DNS:node-01, IP Address:172.30.140.102", "node-01", "172.30.140.101", 0, 0))
t("TLS IP failure", True, lambda: check_tls(GOOD_CFG, 0, GOOD_SAN, "node-01", "172.30.140.101", 1, 0))
t("TLS hostname failure", True, lambda: check_tls(GOOD_CFG, 0, GOOD_SAN, "node-01", "172.30.140.101", 0, 1))
t("unexpected pending serving CSR", True, lambda: check_csr(json.dumps({"items":[{"spec":{"signerName":"kubernetes.io/kubelet-serving"},"status":{"conditions":[]}}]})))
t("malformed Node JSON", True, lambda: check_nodes("{bad json"))
t("malformed CSR JSON", True, lambda: check_csr("{bad json"))
t("README stale P0", True, lambda: check_readme("P0: IN PROGRESS — PREPARATION ONLY\nP7B1 IN PROGRESS\nP7B2 NOT AUTHORIZED\n"))
t("README falsely P7B1 FINAL ACCEPTED", True, lambda: check_readme("P7B1 FINAL ACCEPTED\nP7B2 NOT AUTHORIZED\n"))
t("README falsely authorizes P7B2", True, lambda: check_readme("P7B1 IN PROGRESS\nP7B2 AUTHORIZED\n"))
t("query rc != 0", True, lambda: check_preservation(1, "P6D_FINAL_READONLY_VERIFIER_PASS", "P6D_FINAL_READONLY_VERIFIER_PASS"))
t("clean fixture", False, lambda: (check_nodes(GOOD_NODES), check_tls(GOOD_CFG, 0, GOOD_SAN, "node-01", "172.30.140.101", 0, 0), check_csr(GOOD_CSR), check_preservation(0, "P6D_FINAL_READONLY_VERIFIER_PASS", "P6D_FINAL_READONLY_VERIFIER_PASS"), check_preservation(0, "P7A_FINAL_READONLY_VERIFIER_PASS", "P7A_FINAL_READONLY_VERIFIER_PASS"), check_readme(GOOD_README)))


def main():
    total = 0
    matched = 0
    failed = 0
    for name, expect_fail, fn in T:
        total += 1
        actual = "PASS"
        reason = None
        try:
            fn()
        except Exception as e:
            actual = "FAIL"
            reason = f"{type(e).__name__}: {e}"
        expect = "FAIL" if expect_fail else "PASS"
        ok = (actual == expect)
        print(f"--- {name} --- expected={expect} actual={actual}" + (f" ({reason})" if reason else ""), "=> OK" if ok else "=> MISMATCH")
        if ok:
            matched += 1
        else:
            failed += 1
    print(f"\nTESTS_TOTAL={total}")
    print(f"TESTS_FAILED={failed}")
    print(f"HARNESS_EXIT={0 if failed == 0 else 1}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
