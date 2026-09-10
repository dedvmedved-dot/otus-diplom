#!/usr/bin/env python3
"""
TASK-P7B1 — Negative tests for the kubelet-serving CSR policy checker.
Pure offline fixtures (no cluster mutation). Monkey-patches CSR parsing to
isolate the policy logic, plus one real malformed-base64 case.
"""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import p7b1_validate_kubelet_serving_csr as checker


def make_csr(signer="kubernetes.io/kubelet-serving", username="system:node:node-01",
             groups=None, usages=None, request="dGVzdA=="):
    return {
        "kind": "CertificateSigningRequest",
        "spec": {
            "signerName": signer,
            "username": username,
            "groups": groups if groups is not None else ["system:nodes", "system:authenticated"],
            "usages": usages if usages is not None else ["digital signature", "key encipherment", "server auth"],
            "request": request,
        },
    }


# fixture parse results
GOOD = ("system:node:node-01", "system:nodes", ["node-01"], ["172.30.140.101"])

def run(name, expect_fail, csr=None, node="node-01", ip="172.30.140.101",
        parse=GOOD, parse_exc=None):
    results.append((name, expect_fail, csr, node, ip, parse, parse_exc))


results = []

# 1 valid
run("valid node-01 CSR", False, make_csr())
# 2 wrong signer
run("wrong signer", True, make_csr(signer="kubernetes.io/kube-apiserver-client-kubelet"))
# 3 wrong username
run("wrong username", True, make_csr(username="system:node:node-02"))
# 4 missing system:nodes group
run("missing system:nodes group", True, make_csr(groups=["system:authenticated"]))
# 5 wrong CN
run("wrong CN", True, make_csr(), parse=("system:node:node-02", "system:nodes", ["node-01"], ["172.30.140.101"]))
# 6 wrong organization
run("wrong organization", True, make_csr(), parse=("system:node:node-01", "evil", ["node-01"], ["172.30.140.101"]))
# 7 missing server auth
run("missing server auth", True, make_csr(usages=["digital signature", "key encipherment"]))
# 8 client auth present
run("client auth present", True, make_csr(usages=["server auth", "client auth"]))
# 9 missing InternalIP SAN
run("missing InternalIP SAN", True, make_csr(), parse=("system:node:node-01", "system:nodes", ["node-01"], []))
# 10 foreign node IP SAN
run("foreign node IP SAN", True, make_csr(), parse=("system:node:node-01", "system:nodes", ["node-01"], ["172.30.140.102"]))
# 11 foreign node DNS SAN
run("foreign node DNS SAN", True, make_csr(), parse=("system:node:node-01", "system:nodes", ["node-02"], ["172.30.140.101"]))
# 12 wildcard DNS SAN
run("wildcard DNS SAN", True, make_csr(), parse=("system:node:node-01", "system:nodes", ["*.example.com"], ["172.30.140.101"]))
# 13 URI SAN -> represented as foreign DNS SAN
run("URI SAN (foreign)", True, make_csr(), parse=("system:node:node-01", "system:nodes", ["node-01", "spiffe://x"], ["172.30.140.101"]))
# 14 Email SAN -> foreign DNS
run("Email SAN (foreign)", True, make_csr(), parse=("system:node:node-01", "system:nodes", ["node-01", "a@b.c"], ["172.30.140.101"]))
# 15 unknown extra SAN
run("unknown extra SAN", True, make_csr(), parse=("system:node:node-01", "system:nodes", ["node-01", "extra"], ["172.30.140.101"]))
# 16 malformed CSR request (real base64 decode fail, no monkey-patch)
run("malformed CSR request", True, make_csr(request="!!!not-base64!!!"), parse=None)
# 17 malformed Kubernetes JSON
run("malformed Kubernetes JSON", True, csr="not-a-dict")
# 18 clean node-02
run("clean node-02 fixture", False, make_csr(username="system:node:node-02"), node="node-02", ip="172.30.140.102",
    parse=("system:node:node-02", "system:nodes", ["node-02"], ["172.30.140.102"]))
# 19 clean node-03
run("clean node-03 fixture", False, make_csr(username="system:node:node-03"), node="node-03", ip="172.30.140.103",
    parse=("system:node:node-03", "system:nodes", ["node-03"], ["172.30.140.103"]))


def main():
    total = 0
    matched = 0
    failed = 0
    orig_parse = checker.parse_csr_request
    for name, expect_fail, csr, node, ip, parse, parse_exc in results:
        total += 1
        # monkey-patch parse_csr_request (unless parse=None signals real parse)
        if parse is None:
            checker.parse_csr_request = orig_parse
        elif parse_exc is not None:
            checker.parse_csr_request = lambda req, e=parse_exc: (_ for _ in ()).throw(e)
        else:
            checker.parse_csr_request = lambda req, p=parse: p

        actual = "PASS"
        reason = None
        try:
            if csr == "not-a-dict":
                checker.validate("not-a-dict", node, ip)
            else:
                checker.validate(csr, node, ip)
        except Exception as e:
            actual = "FAIL"
            reason = f"{type(e).__name__}: {e}"

        expect = "FAIL" if expect_fail else "PASS"
        ok = (actual == expect)
        print(f"--- TEST {name} ---")
        print(f"  expected: {expect}")
        print(f"  actual:   {actual}" + (f"  ({reason})" if reason else ""))
        print(f"  outcome:  {'OK' if ok else '*** MISMATCH ***'}")
        if ok:
            matched += 1
        else:
            failed += 1

    print("")
    print(f"TESTS_TOTAL={total}")
    print(f"TESTS_FAILED={failed}")
    print(f"HARNESS_EXIT={0 if failed == 0 else 1}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
