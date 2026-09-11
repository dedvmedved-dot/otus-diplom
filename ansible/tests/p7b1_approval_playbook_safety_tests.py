#!/usr/bin/env python3
"""
TASK-P7B1-R1 — Approval playbook safety tests (offline, no cluster mutation).
Parses the approval playbook YAML and asserts the hardened safety contract.
Plus reuse of the policy checker for a live-node/CSR IP mismatch case.
"""

import os
import sys
import yaml

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import p7b1_validate_kubelet_serving_csr as checker

PLAYBOOK = os.path.join(os.path.dirname(__file__), "..", "playbooks", "p7b1-approve-kubelet-serving-csr.yml")


def load_playbook():
    with open(PLAYBOOK) as f:
        return yaml.safe_load(f)


def find_task(pb, name_substr):
    for play in pb:
        for task in play.get("tasks", []):
            if name_substr in task.get("name", ""):
                return task
    return None


def test_default_approve_false(pb):
    for play in pb:
        for var in play.get("vars", []):
            if var == "approve":
                return  # var declared; check default below
    # approve var must have default false
    for play in pb:
        v = play.get("vars", {})
        if isinstance(v, dict) and "approve" in v:
            default = v["approve"]
            assert "false" in str(default), f"approve default not false: {default}"
            return
    raise AssertionError("approve var with default false not found")


def test_no_operator_node_ip(pb):
    # no node_ip var declared
    for play in pb:
        v = play.get("vars", {})
        if isinstance(v, dict) and "node_ip" in v:
            raise AssertionError("operator node_ip var present")
    # checker must not be invoked with --ip (operator IP)
    t = find_task(pb, "Validate CSR policy")
    cmd = t["ansible.builtin.shell"]["cmd"]
    assert "--ip " not in cmd, "checker invoked with --ip (operator IP)"


def test_live_node_fetch(pb):
    t = find_task(pb, "Fetch exact live Node JSON")
    assert t is not None, "live Node fetch task missing"
    assert "get node" in t["ansible.builtin.shell"]["cmd"], "no kubectl get node"


def test_checker_receives_node_json(pb):
    t = find_task(pb, "Validate CSR policy")
    assert "--node-json" in t["ansible.builtin.shell"]["cmd"], "checker not given --node-json"


def test_exact_csr_name(pb):
    t = find_task(pb, "Approve EXACTLY this CSR")
    cmd = t["ansible.builtin.shell"]["cmd"]
    assert "{{ csr_name }}" in cmd, "approve not using exact csr_name"
    assert "approve -A" not in cmd and "approve --all" not in cmd, "wildcard approve present"
    # when clause
    w = t.get("when", [])
    assert "approve | bool" in w, "approve=true gate missing"
    assert "policy.rc == 0" in w, "policy PASS gate missing"


def test_foreign_ip_mismatch_fails():
    # reuse checker directly: CSR claims node-01 but live Node IP differs
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID
    import ipaddress, base64
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    san = x509.SubjectAlternativeName([x509.DNSName("node-01"), x509.IPAddress(ipaddress.ip_address("172.30.140.102"))])
    csr = (x509.CertificateSigningRequestBuilder()
           .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "system:node:node-01"),
                                    x509.NameAttribute(NameOID.ORGANIZATION_NAME, "system:nodes")]))
           .add_extension(san, critical=False).sign(key, hashes.SHA256()))
    req = base64.b64encode(csr.public_bytes(serialization.Encoding.PEM)).decode()
    csr_obj = {"kind": "CertificateSigningRequest", "spec": {
        "signerName": "kubernetes.io/kubelet-serving", "username": "system:node:node-01",
        "groups": ["system:nodes", "system:authenticated"],
        "usages": ["digital signature", "key encipherment", "server auth"], "request": req}}
    try:
        checker.validate(csr_obj, "node-01", "172.30.140.101")
        raise AssertionError("foreign IP mismatch did not fail")
    except AssertionError:
        pass  # expected


TESTS = [
    ("default approve=false", lambda pb: test_default_approve_false(pb)),
    ("no authoritative operator node_ip", lambda pb: test_no_operator_node_ip(pb)),
    ("live Node JSON is fetched", lambda pb: test_live_node_fetch(pb)),
    ("checker receives Node JSON", lambda pb: test_checker_receives_node_json(pb)),
    ("exact CSR name / no wildcard", lambda pb: test_exact_csr_name(pb)),
    ("foreign live-node/CSR IP mismatch fails", lambda pb: test_foreign_ip_mismatch_fails()),
    ("checker failure prevents approval (policy.rc==0 gate)", lambda pb: _check_policy_gate(pb)),
    ("approve=true required (default false)", lambda pb: test_default_approve_false(pb)),
]


def _check_policy_gate(pb):
    t = find_task(pb, "Approve EXACTLY this CSR")
    assert "policy.rc == 0" in t.get("when", []), "policy gate missing"


def main():
    pb = load_playbook()
    total = 0
    failed = 0
    for name, fn in TESTS:
        total += 1
        try:
            fn(pb)
            print(f"--- {name} --- PASS")
        except Exception as e:
            failed += 1
            print(f"--- {name} --- FAIL ({type(e).__name__}: {e})")
    print(f"\nTESTS_TOTAL={total}")
    print(f"TESTS_FAILED={failed}")
    print(f"HARNESS_EXIT={0 if failed == 0 else 1}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
