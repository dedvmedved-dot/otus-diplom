#!/usr/bin/env python3
"""Offline CLI-acceptance test for the ACTUAL cosign v3.1.3 binary.

review #99 item 1: the workflow previously passed `-a ref=…` to
``cosign verify-attestation``, which cosign v3.1.3 REJECTS
("unknown shorthand flag: 'a'"). This test runs the REAL binary (downloaded and
SHA-256-verified if not already present) and proves:

  * verify-attestation REJECTS `-a` (the broken mechanism) — for BOTH
    slsaprovenance and spdxjson;
  * verify-attestation ACCEPTS the supported flag set (--type /
    --certificate-identity / --certificate-oidc-issuer / --policy);
  * verify and sign ACCEPT `-a ref=…` (the image-signature ref check is kept).

The class SKIPS (rather than fails) when the binary cannot be located or
downloaded — flag acceptance is a property of the tool, not of this repo's
offline environment. The checksum is re-asserted from the pinned value so a
substituted binary cannot silently change the verdict.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

COSIGN_VERSION = "3.1.3"
COSIGN_SHA256 = "4629c757b7618056f8ddd7e2625ae9fdd94c0372a65049520bc7d9df9efc7f71"
COSIGN_URL = ("https://github.com/sigstore/cosign/releases/download/"
              "v%s/cosign-linux-amd64" % COSIGN_VERSION)


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _locate_cosign():
    """Return a path to a verified cosign binary, or None."""
    candidates = [os.environ.get("COSIGN_BINARY"), "/usr/local/bin/cosign",
                  "/tmp/cosign-linux-amd64"]
    for c in candidates:
        if c and Path(c).is_file():
            if _sha256(c) == COSIGN_SHA256:
                return c
            # A locally present binary with the WRONG checksum must not be used.
            return None
    # Download + verify into a temp cache.
    try:
        cache = Path(tempfile.gettempdir()) / ("cosign-%s" % COSIGN_VERSION)
        if cache.is_file() and _sha256(cache) == COSIGN_SHA256:
            return str(cache)
        tmp = str(cache) + ".part"
        subprocess.run(["curl", "-sSfL", COSIGN_URL, "-o", tmp], check=True)
        if _sha256(tmp) != COSIGN_SHA256:
            return None
        os.chmod(tmp, 0o755)
        shutil.move(tmp, cache)
        return str(cache)
    except Exception:
        return None


COSIGN = _locate_cosign()


@unittest.skipUnless(COSIGN, "cosign v3.1.3 binary unavailable (offline env)")
class TestCosignCliFlags(unittest.TestCase):
    """Flag-acceptance of the ACTUAL cosign v3.1.3 CLI."""

    def _run(self, *args):
        assert COSIGN is not None  # guarded by skipUnless
        return subprocess.run([COSIGN, *args], capture_output=True, text=True)

    def test_verify_attestation_rejects_a_slsaprovenance(self):
        r = self._run("verify-attestation", "--type", "slsaprovenance",
                      "-a", "ref=test", "--help")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("unknown shorthand flag: 'a'", r.stderr)

    def test_verify_attestation_rejects_a_spdxjson(self):
        r = self._run("verify-attestation", "--type", "spdxjson",
                      "-a", "ref=test", "--help")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("unknown shorthand flag: 'a'", r.stderr)

    def test_verify_attestation_accepts_supported_flags(self):
        r = self._run("verify-attestation", "--type", "slsaprovenance",
                      "--certificate-identity", "X",
                      "--certificate-oidc-issuer", "Y",
                      "--policy", "/nonexistent.cue", "--help")
        self.assertEqual(r.returncode, 0)
        self.assertNotIn("unknown", r.stderr)

    def test_verify_accepts_a_annotation(self):
        r = self._run("verify", "-a", "ref=test", "--help")
        self.assertEqual(r.returncode, 0)

    def test_sign_accepts_a_annotation(self):
        r = self._run("sign", "-a", "ref=test", "--help")
        self.assertEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
