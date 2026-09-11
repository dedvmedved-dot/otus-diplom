#!/usr/bin/env python3
"""
TASK-P7B1-R1 — Real PKCS#10 CSR policy tests (fail-closed).
Generates real CSRs with cryptography; NO monkey-patching of parsed SAN arrays.
Node JSON is authoritative. Temporary private keys are in-memory only.
"""

import base64
import ipaddress
import json
import os
import sys
import tempfile

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import p7b1_validate_kubelet_serving_csr as checker


def gen_csr_pem(cn, o, dns_sans, ip_sans, uris=None, emails=None, others=None):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    san_entries = []
    for d in dns_sans:
        san_entries.append(x509.DNSName(d))
    for ip in ip_sans:
        san_entries.append(x509.IPAddress(ipaddress.ip_address(ip)))
    for u in (uris or []):
        san_entries.append(x509.UniformResourceIdentifier(u))
    for e in (emails or []):
        san_entries.append(x509.RFC822Name(e))
    for oth in (others or []):
        san_entries.append(oth)
    builder = x509.CertificateSigningRequestBuilder().subject_name(
        x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn),
                   x509.NameAttribute(NameOID.ORGANIZATION_NAME, o)]))
    if san_entries:
        builder = builder.add_extension(x509.SubjectAlternativeName(san_entries), critical=False)
    csr = builder.sign(key, hashes.SHA256())
    return csr.public_bytes(serialization.Encoding.PEM)


def make_csr(cn="system:node:node-01", o="system:nodes", dns=["node-01"], ip=["172.30.140.101"],
             signer="kubernetes.io/kubelet-serving", username="system:node:node-01",
             groups=None, usages=None, uris=None, emails=None, others=None,
             request=None):
    if request is None:
        pem = gen_csr_pem(cn, o, dns, ip, uris, emails, others)
        request = base64.b64encode(pem).decode()
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


def node_json(name="node-01", ready=True, ips=None):
    ips = ips if ips is not None else ["172.30.140.101"]
    return {
        "kind": "Node",
        "metadata": {"name": name},
        "status": {
            "conditions": [{"type": "Ready", "status": "True" if ready else "False"}],
            "addresses": [{"type": "InternalIP", "address": ip} for ip in ips],
        },
    }


def write_json(obj):
    f = tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w")
    json.dump(obj, f)
    f.close()
    return f.name


T = []
def t(name, expect_fail, csr=None, node=None, expected_node=None, csr_raw=None, node_raw=None):
    T.append((name, expect_fail, csr, node, expected_node, csr_raw, node_raw))


# 1-3 valid
t("valid node-01 + Node", False, make_csr(), node_json())
t("valid node-02 + Node", False, make_csr(cn="system:node:node-02", dns=["node-02"], ip=["172.30.140.102"], username="system:node:node-02"), node_json("node-02", ips=["172.30.140.102"]))
t("valid node-03 + Node", False, make_csr(cn="system:node:node-03", dns=["node-03"], ip=["172.30.140.103"], username="system:node:node-03"), node_json("node-03", ips=["172.30.140.103"]))
# 4 wrong signer
t("wrong signer", True, make_csr(signer="kubernetes.io/kube-apiserver-client-kubelet"), node_json())
# 5 wrong username
t("wrong username", True, make_csr(username="system:node:node-02"), node_json())
# 6 missing system:nodes group
t("missing system:nodes group", True, make_csr(groups=["system:authenticated"]), node_json())
# 7 wrong CN
t("wrong CN", True, make_csr(cn="system:node:node-02"), node_json())
# 8 wrong O
t("wrong O", True, make_csr(o="evil"), node_json())
# 9 missing server auth
t("missing server auth", True, make_csr(usages=["digital signature", "key encipherment"]), node_json())
# 10 client auth present
t("client auth present", True, make_csr(usages=["server auth", "client auth"]), node_json())
# 11 missing DNS SAN
t("missing DNS SAN", True, make_csr(dns=[]), node_json())
# 12 missing IP SAN
t("missing IP SAN", True, make_csr(ip=[]), node_json())
# 13 foreign DNS SAN
t("foreign DNS SAN", True, make_csr(dns=["node-02"]), node_json())
# 14 foreign IP SAN
t("foreign IP SAN", True, make_csr(ip=["172.30.140.102"]), node_json())
# 15 wildcard DNS SAN
t("wildcard DNS SAN", True, make_csr(dns=["*.example.com"]), node_json())
# 16 extra DNS SAN
t("extra DNS SAN", True, make_csr(dns=["node-01", "extra"]), node_json())
# 17 extra IP SAN
t("extra IP SAN", True, make_csr(ip=["172.30.140.101", "172.30.140.102"]), node_json())
# 18 real URI SAN
t("real URI SAN", True, make_csr(uris=["spiffe://cluster.local/node-01"]), node_json())
# 19 real Email SAN
t("real Email SAN", True, make_csr(emails=["a@b.c"]), node_json())
# 20 valid + URI
t("valid DNS/IP + URI", True, make_csr(uris=["spiffe://x"]), node_json())
# 21 valid + Email
t("valid DNS/IP + Email", True, make_csr(emails=["a@b.c"]), node_json())
# 22 malformed PKCS#10
t("malformed PKCS#10", True, make_csr(request=base64.b64encode(b"not a csr").decode()), node_json())
# 23 malformed CSR JSON
t("malformed CSR JSON", True, csr_raw='"not json"', node=node_json())
# 24 malformed Node JSON
t("malformed Node JSON", True, make_csr(), node_raw='"not json"')
# 25 Node missing -> node_json with kind != Node
t("Node missing kind", True, make_csr(), node_raw=json.dumps({"metadata":{"name":"node-01"}}))
# 26 Node NotReady
t("Node NotReady", True, make_csr(), node=node_json(ready=False))
# 27 Node without InternalIP
t("Node without InternalIP", True, make_csr(), node=node_json(ips=[]))
# 28 multiple InternalIP
t("multiple InternalIP", True, make_csr(), node=node_json(ips=["172.30.140.101", "172.30.140.199"]))
# 29 expected node mismatch
t("expected node mismatch", True, make_csr(), node_json(), expected_node="node-02")
# 30 CSR IP differs from live Node
t("CSR IP differs from live Node", True, make_csr(ip=["172.30.140.102"]), node_json())
# 31 CSR claims another node
t("CSR claims another node", True, make_csr(cn="system:node:node-02", username="system:node:node-02", dns=["node-02"]), node_json())
# 32 unknown SAN type (OtherName)
t("unknown SAN type (OtherName)", True, make_csr(others=[x509.OtherName(x509.ObjectIdentifier("1.2.3.4"), b"\x05\x00")]), node_json())
# 33 canonical clean
t("canonical clean", False, make_csr(), node_json())


def main():
    total = 0
    matched = 0
    failed = 0
    for name, expect_fail, csr, node, expected_node, csr_raw, node_raw in T:
        total += 1
        csr_path = write_json(csr) if csr is not None else write_json(csr_raw)
        node_path = write_json(node) if node is not None else write_json(node_raw)
        actual = "PASS"
        reason = None
        try:
            args = ["x", csr_path, "--node-json", node_path]
            if expected_node:
                args += ["--expected-node", expected_node]
            import argparse
            # call internal validate directly to avoid sys.exit
            if node is not None:
                live_node, live_ip = checker.load_node(node_path)
            else:
                live_node, live_ip = checker.load_node(node_path)
            with open(csr_path) as f:
                csr_obj = json.load(f)
            checker.validate(csr_obj, live_node, live_ip, expected_node)
        except Exception as e:
            actual = "FAIL"
            reason = f"{type(e).__name__}: {e}"
        finally:
            os.unlink(csr_path)
            os.unlink(node_path)

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
