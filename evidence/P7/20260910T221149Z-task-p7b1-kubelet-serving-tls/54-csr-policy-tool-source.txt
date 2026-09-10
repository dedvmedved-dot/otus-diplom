#!/usr/bin/env python3
"""
TASK-P7B1 — Validate a kubernetes.io/kubelet-serving CertificateSigningRequest
against strict policy. FAIL-CLOSED. Read-only (no cluster mutation).

Usage:
  python3 p7b1_validate_kubelet_serving_csr.py <csr.json> --node <node> --ip <InternalIP>

Exit 0 only when ALL checks pass.
"""

import argparse
import base64
import json
import subprocess
import sys
import tempfile
import os

SIGNER = "kubernetes.io/kubelet-serving"
ALLOWED_USAGES = {"digital signature", "key encipherment", "server auth"}
FORBIDDEN_USAGES = {"client auth", "cert sign", "crl sign", "code signing",
                    "email protection", "key agreement", "encipher only",
                    "decipher only", "any", "ipsec end system", "ipsec tunnel",
                    "ipsec user", "timestamping", "ocsp signing", "microsoft sgc",
                    "netscape sgc"}


def fail(msg):
    raise AssertionError(msg)


def parse_csr_request(request_b64):
    """Decode PKCS#10 request (base64 PEM) and return (subject_cn, subject_o, dns_sans, ip_sans)."""
    try:
        pem = base64.b64decode(request_b64).decode("utf-8", errors="replace")
    except Exception as e:
        fail(f"cannot base64-decode spec.request: {e}")
    if "-----BEGIN CERTIFICATE REQUEST-----" not in pem:
        fail("spec.request does not contain a PEM CSR")
    with tempfile.NamedTemporaryFile(suffix=".pem", delete=False, mode="w") as f:
        f.write(pem)
        pem_path = f.name

    r = subprocess.run(["openssl", "req", "-in", pem_path, "-noout", "-subject", "-text"],
                       capture_output=True, text=True)
    os.unlink(pem_path)
    if r.returncode != 0:
        fail(f"openssl req failed: {r.stderr}")

    out = r.stdout
    import re
    subject_cn = None
    subject_o = None
    for line in out.splitlines():
        if line.startswith("subject="):
            mcn = re.search(r'CN\s*=\s*([^,\n]+)', line)
            mo = re.search(r'O\s*=\s*([^,\n]+)', line)
            if mcn:
                subject_cn = mcn.group(1).strip()
            if mo:
                subject_o = mo.group(1).strip()
    dns_sans = re.findall(r'DNS:([^,\s\n]+)', out)
    ip_sans = re.findall(r'IP Address:([0-9.]+)', out)
    return subject_cn, subject_o, dns_sans, ip_sans


def validate(csr, expected_node, expected_ip):
    if not isinstance(csr, dict):
        fail("CSR must be a JSON object")
    if csr.get("kind") != "CertificateSigningRequest":
        fail(f"kind != CertificateSigningRequest: {csr.get('kind')}")

    spec = csr.get("spec")
    if not isinstance(spec, dict):
        fail("spec missing/not object")

    if spec.get("signerName") != SIGNER:
        fail(f"signerName != {SIGNER}: {spec.get('signerName')}")

    username = spec.get("username", "")
    if username != f"system:node:{expected_node}":
        fail(f"username != system:node:{expected_node}: {username}")

    groups = spec.get("groups", [])
    if not isinstance(groups, list) or "system:nodes" not in groups:
        fail(f"groups missing system:nodes: {groups}")

    usages = spec.get("usages", [])
    if not isinstance(usages, list):
        fail("usages missing/not list")
    usages_set = set(usages)
    if "server auth" not in usages_set:
        fail("usages missing 'server auth'")
    if usages_set - ALLOWED_USAGES:
        fail(f"unexpected usages: {usages_set - ALLOWED_USAGES}")

    request_b64 = spec.get("request", "")
    if not request_b64:
        fail("spec.request empty")

    cn, o, dns_sans, ip_sans = parse_csr_request(request_b64)

    if cn != f"system:node:{expected_node}":
        fail(f"CN != system:node:{expected_node}: {cn}")
    if o != "system:nodes":
        fail(f"O != system:nodes: {o}")

    if expected_node not in dns_sans:
        fail(f"DNS SAN missing {expected_node}: {dns_sans}")
    if expected_ip not in ip_sans:
        fail(f"IP SAN missing {expected_ip}: {ip_sans}")

    for d in dns_sans:
        if d != expected_node:
            fail(f"foreign DNS SAN: {d}")
    for ip in ip_sans:
        if ip != expected_ip:
            fail(f"foreign IP SAN: {ip}")

    # no wildcard / no foreign
    for d in dns_sans:
        if "*" in d:
            fail(f"wildcard DNS SAN: {d}")

    print(f"POLICY_RESULT=PASS")
    print(f"NODE={expected_node}")
    print(f"IP={expected_ip}")
    print(f"SIGNER={spec.get('signerName')}")
    print(f"USERNAME={username}")
    print(f"GROUPS={groups}")
    print(f"USAGES={usages}")
    print(f"CN={cn}")
    print(f"O={o}")
    print(f"DNS_SANS={dns_sans}")
    print(f"IP_SANS={ip_sans}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csr_json")
    ap.add_argument("--node", required=True)
    ap.add_argument("--ip", required=True)
    args = ap.parse_args()

    with open(args.csr_json) as f:
        csr = json.load(f)

    try:
        validate(csr, args.node, args.ip)
    except AssertionError as e:
        print(f"POLICY_RESULT=FAIL")
        print(f"REASON={e}")
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
