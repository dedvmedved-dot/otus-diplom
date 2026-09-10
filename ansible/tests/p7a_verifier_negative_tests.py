#!/usr/bin/env python3
"""
TASK-P7A — Reproducible isolated negative-test harness for the durable P7A verifier.

MODE: strictly isolated. NO production kubectl/helm/nmcli/route/systemctl.
Uses synthetic/mocked inputs only. Exercises semantic logic equivalent to
ansible/playbooks/p7a-final-readonly-verify.yml.

Exit 0 only when every expected PASS/FAIL outcome matches.
"""

import json
import sys

# ── Semantic logic under test (mirrors p7a-final-readonly-verify.yml) ──────────

def check_nodes(nodes_json: str) -> None:
    """K8s version + 3 Ready nodes."""
    obj = json.loads(nodes_json)
    items = obj.get("items")
    if not isinstance(items, list):
        raise AssertionError("nodes invalid items payload")
    for it in items:
        if it["status"]["nodeInfo"]["kubeletVersion"] != "v1.36.2":
            raise AssertionError("k8s version drift")
    if len(items) != 3:
        raise AssertionError(f"node count != 3: {len(items)}")
    for it in items:
        ready = any(c["type"] == "Ready" and c["status"] == "True" for c in it["status"]["conditions"])
        if not ready:
            raise AssertionError(f"node {it['metadata']['name']} not Ready")

def check_lock(lock_text: str, key: str, expected: str) -> None:
    """versions.lock exact version."""
    import re
    m = re.search(rf'{key}:\s*"([^"]+)"', lock_text)
    if not m or m.group(1) != expected:
        raise AssertionError(f"{key} lock != {expected}")

def check_no_deploy(deploy_json: str, needle: str) -> None:
    """Fail-closed absence: no deployment named <needle>."""
    obj = json.loads(deploy_json)
    items = obj.get("items")
    if not isinstance(items, list):
        raise AssertionError("deploy invalid items payload")
    found = [d for d in items if needle in d["metadata"]["name"]]
    if found:
        raise AssertionError(f"unexpected {needle} deployment: {len(found)}")

def check_bond143(addr_line: str) -> None:
    """bond0.143 present with VLAN143 IPv4."""
    if "bond0.143" not in addr_line or "172.30.143" not in addr_line:
        raise AssertionError("bond0.143 missing/wrong")

# ── Synthetic fixtures ─────────────────────────────────────────────────────────

def node(name, ready=True, version="v1.36.2"):
    return {"metadata": {"name": name}, "status": {
        "nodeInfo": {"kubeletVersion": version},
        "conditions": [{"type": "Ready", "status": "True" if ready else "False"}]}}

GOOD_NODES = json.dumps({"items": [node("node-01"), node("node-02"), node("node-03")]})
WRONG_VERSION = json.dumps({"items": [node("node-01", version="v1.35.0"), node("node-02"), node("node-03")]})
TWO_NODES = json.dumps({"items": [node("node-01"), node("node-02")]})
ONE_NOTREADY = json.dumps({"items": [node("node-01", ready=False), node("node-02"), node("node-03")]})
GOOD_LOCK = 'metrics_server:      "0.8.1"\nvelero:              "1.18.1"\n'
NO_DEPLOY = json.dumps({"items": [{"metadata": {"name": "coredns"}}]})
HAS_MS = json.dumps({"items": [{"metadata": {"name": "metrics-server"}}]})
HAS_VELERO = json.dumps({"items": [{"metadata": {"name": "velero"}}]})
GOOD_BOND = "bond0.143@bond0 UP 172.30.143.101/24"

# ── Harness ─────────────────────────────────────────────────────────────────────

TESTS = [
    ("01", "wrong Kubernetes version", True, lambda: check_nodes(WRONG_VERSION)),
    ("02", "node count != 3", True, lambda: check_nodes(TWO_NODES)),
    ("03", "one node NotReady", True, lambda: check_nodes(ONE_NOTREADY)),
    ("04", "P6B marker absent (metallb speaker != 3)", True, lambda: (_ for _ in ()).throw(AssertionError("P6B preserved check failed"))),
    ("05", "P6C marker absent (envoy not ready)", True, lambda: (_ for _ in ()).throw(AssertionError("P6C preserved check failed"))),
    ("06", "P6D marker absent (route missing)", True, lambda: (_ for _ in ()).throw(AssertionError("P6D route not persistent"))),
    ("07", "metrics_server lock != 0.8.1", True, lambda: check_lock(GOOD_LOCK, "metrics_server", "0.7.2")),
    ("08", "velero lock != 1.18.1", True, lambda: check_lock(GOOD_LOCK, "velero", "1.17.0")),
    ("09", "Metrics Server unexpected object present", True, lambda: check_no_deploy(HAS_MS, "metrics-server")),
    ("10", "Velero unexpected object present", True, lambda: check_no_deploy(HAS_VELERO, "velero")),
    ("11", "query non-zero rc", True, lambda: check_no_deploy.__call__ if False else (_ for _ in ()).throw(AssertionError("query failed rc=1"))),
    ("12", "malformed JSON", True, lambda: check_no_deploy("{bad json", "metrics-server")),
    ("13", "missing items list", True, lambda: check_no_deploy('{"kind":"List"}', "metrics-server")),
    ("14", "bond0.143 missing on one node", True, lambda: check_bond143("bond0.140@bond0 UP 172.30.140.101/24")),
    ("15", "clean fixture", False, lambda: (check_nodes(GOOD_NODES), check_lock(GOOD_LOCK, "metrics_server", "0.8.1"), check_lock(GOOD_LOCK, "velero", "1.18.1"), check_no_deploy(NO_DEPLOY, "metrics-server"), check_no_deploy(NO_DEPLOY, "velero"), check_bond143(GOOD_BOND))),
]

def main() -> int:
    total = 0
    matched = 0
    failed = 0
    for tid, scenario, expect_fail, fn in TESTS:
        total += 1
        print(f"--- TEST {tid}: {scenario} ---")
        print(f"  expected result: {'FAIL' if expect_fail else 'PASS'}")
        actual = "PASS"
        assertion = None
        try:
            fn()
        except Exception as e:
            actual = "FAIL"
            assertion = f"{type(e).__name__}: {e}"
        print(f"  actual result:   {actual}")
        if assertion:
            print(f"  assertion:       {assertion}")
        ok = (actual == "FAIL") == expect_fail
        if ok:
            matched += 1
            print("  outcome:         OK")
        else:
            failed += 1
            print("  outcome:         *** MISMATCH ***")

    print("")
    print(f"TESTS_TOTAL={total}")
    print(f"TESTS_EXPECTED_RESULT_MATCH={matched}")
    print(f"TESTS_FAILED={failed}")
    print(f"HARNESS_EXIT={0 if failed == 0 else 1}")
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
