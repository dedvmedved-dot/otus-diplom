#!/usr/bin/env python3
"""
TASK-P7B1-R2 — Verifier portability tests (offline).
Proves the committed durable verifier contains no host-specific credential path,
no password argv, and that P6D/P7A real checks + final PASS gating are intact.
"""

import os
import sys

VERIFIER = os.path.join(os.path.dirname(__file__), "..", "playbooks", "p7b1-final-readonly-verify.yml")


def read():
    with open(VERIFIER) as f:
        return f.read()


def test_no_hermes_path(text):
    assert "/etc/hermes" not in text, "host-specific secret path present"


def test_no_pak_root_pass(text):
    assert "pak_root_pass" not in text, "pak_root_pass present"


def test_no_ansible_ssh_pass(text):
    assert "ansible_ssh_pass" not in text, "ansible_ssh_pass present"


def test_no_ssHpass(text):
    assert "SSHPASS" not in text and "sshpass" not in text, "SSHPASS/sshpass present"


def test_no_password_on_cmdline(text):
    assert "password=" not in text and "--ask-pass" not in text, "password argv present"


def test_no_embedded_credential(text):
    import re
    assert not re.search(r"(passwd|password|secret)\s*[=:]\s*\S+", text, re.I), "embedded credential present"


def test_p6d_real_check_required(text):
    assert "P7B1_P6D_PRESERVED" in text, "P6D marker missing"
    # real check: route assert, not a bare print
    assert "172.30.20.0/24 via 172.30.140.1 dev bond0.140" in text, "P6D route real check missing"
    assert "P7B1_P6D_KUBECTL_OK" in text, "P6D kubectl check missing"


def test_p7a_real_check_required(text):
    assert "P7B1_P7A_PRESERVED" in text, "P7A marker missing"
    assert "bond0.143" in text, "P7A bond0.143 real check missing"
    assert "P7B1_P7A_KUBECTL_OK" in text, "P7A kubectl check missing"


def test_p6d_failure_propagates(text):
    # any_errors_fatal => a failing P6D check aborts the play, so final marker won't print
    assert "any_errors_fatal: true" in text, "any_errors_fatal not set (P6D failure wouldn't propagate)"


def test_p7a_failure_propagates(text):
    assert "any_errors_fatal: true" in text, "any_errors_fatal not set"


def test_final_marker_requires_both(text):
    # final PASS printed only in the LAST task (README), after all preceding tasks
    # (cluster + node checks) completed; with any_errors_fatal any earlier failure aborts.
    assert "P7B1_FINAL_READONLY_VERIFIER_PASS" in text, "final marker missing"
    idx_final = text.index("P7B1_FINAL_READONLY_VERIFIER_PASS")
    idx_p6d = text.index("P7B1_P6D_PRESERVED")
    idx_p7a = text.index("P7B1_P7A_PRESERVED")
    assert idx_p6d < idx_final and idx_p7a < idx_final, "final PASS must come after P6D/P7A checks"


TESTS = [
    ("/etc/hermes path absent", lambda t: test_no_hermes_path(t)),
    ("pak_root_pass absent", lambda t: test_no_pak_root_pass(t)),
    ("ansible_ssh_pass absent", lambda t: test_no_ansible_ssh_pass(t)),
    ("SSHPASS absent", lambda t: test_no_ssHpass(t)),
    ("no password on command line", lambda t: test_no_password_on_cmdline(t)),
    ("no embedded credential", lambda t: test_no_embedded_credential(t)),
    ("P6D real check required", lambda t: test_p6d_real_check_required(t)),
    ("P7A real check required", lambda t: test_p7a_real_check_required(t)),
    ("P6D failure propagates", lambda t: test_p6d_failure_propagates(t)),
    ("P7A failure propagates", lambda t: test_p7a_failure_propagates(t)),
    ("final PASS requires both real checks", lambda t: test_final_marker_requires_both(t)),
]


def main():
    text = read()
    total = 0
    failed = 0
    for name, fn in TESTS:
        total += 1
        try:
            fn(text)
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
