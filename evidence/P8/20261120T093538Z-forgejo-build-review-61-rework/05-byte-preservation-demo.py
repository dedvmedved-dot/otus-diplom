#!/usr/bin/env python3
"""Offline byte-level demonstration (review #61 item 2).

Proves, on SCRATCH copies only (never the real portal/versions.lock), that
apply_lock_pair preserves the raw bytes OUTSIDE the digest line for LF, CRLF,
mixed endings and an absent trailing newline. Run from portal/tools with the
repo's interpreter:

    /usr/bin/python3 -B evidence/P8/<runid>/05-byte-preservation-demo.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "portal" / "tools"))
import forgejo_lock_gate as gate  # noqa: E402

IMAGE = "registry.example/aiopslab/otus-diplom-portal"
DIGEST = "sha256:" + "d" * 64

LOCK_LF = (
    '# P8C Portal application + toolchain lock (new entries; does not override\n'
    '# infrastructure locks).\n'
    'baseline: "P8C-R1"\n'
    'verification_status: NOT_VERIFIED\n'
    '\n'
    'application:\n'
    '  go: "1.27.3"\n'
    '  go_archive_sha256: "65efbc80fdc1fa2cd2631cad5b481777a68e8725f34e89f50fc6ac714e379b40"\n'
    '\n'
    'image:\n'
    '  registry: "%s"\n'
    '  digest: "NOT_VERIFIED"   # final digest only after reproducible build (G2)\n'
    '  base: "scratch"\n'
    '  base_digest: "NOT_APPLICABLE_EMPTY_BASE"\n'
    '\n'
    'notes:\n'
    '  - "tool release metadata recorded from source-verification.json."\n'
    '\n'
    'actions:\n'
    '  checkout: "11bd71901bbe5b1630ceea73d27597364c9af683"\n'
) % IMAGE


def report(name, raw_before, raw_after):
    b = raw_before.splitlines(keepends=True)
    a = raw_after.splitlines(keepends=True)
    diffs = [i for i in range(len(b)) if i >= len(a) or b[i] != a[i]]
    if len(b) != len(a):
        diffs += list(range(len(b), len(a)))
    print("[%s]" % name)
    print("  before: lines=%d CRLF=%d LF=%d trailing_newline=%s"
          % (len(b), raw_before.count(b"\r\n"), raw_before.count(b"\n"),
             raw_before.endswith(b"\n")))
    print("  after : lines=%d CRLF=%d LF=%d trailing_newline=%s"
          % (len(a), raw_after.count(b"\r\n"), raw_after.count(b"\n"),
             raw_after.endswith(b"\n")))
    print("  changed_line_indices=%s (must be exactly one, the digest line)" % diffs)
    assert len(diffs) == 1, diffs
    assert b"digest:" in b[diffs[0]]
    assert DIGEST.encode() in a[diffs[0]]
    # every byte outside the changed line is identical (the review's requirement)
    assert raw_before.count(b"\r\n") == raw_after.count(b"\r\n")
    assert raw_before.endswith(b"\n") == raw_after.endswith(b"\n")
    print("  OK: exactly one line changed; CRLF count + trailing-newline preserved\n")


def scratch(raw):
    import tempfile
    td = Path(tempfile.mkdtemp(prefix="lockbyte-"))
    lock = td / "versions.lock"
    lock.write_bytes(raw)
    gate.apply_lock_pair(lock, IMAGE, DIGEST)
    after = lock.read_bytes()
    return after


def main():
    # 1. LF (real-lock style)
    raw_lf = LOCK_LF.encode()
    report("LF", raw_lf, scratch(raw_lf))

    # 2. CRLF (the review's exact failure: was CRLF 47 -> 0)
    raw_crlf = LOCK_LF.replace("\n", "\r\n").encode()
    report("CRLF", raw_crlf, scratch(raw_crlf))

    # 3. mixed endings (some CRLF, digest line stays LF)
    lines = LOCK_LF.rstrip("\n").split("\n")
    mixed = "".join(ln + ("\r\n" if i in (2, 5) else "\n")
                    for i, ln in enumerate(lines))
    report("MIXED", mixed.encode(), scratch(mixed.encode()))

    # 4. no trailing newline
    body = LOCK_LF.rstrip("\n").encode()
    report("NO_TRAILING_NEWLINE", body, scratch(body))

    print("BYTE_PRESERVATION = VERIFIED (LF / CRLF / mixed / no-trailing-newline)")


if __name__ == "__main__":
    main()
