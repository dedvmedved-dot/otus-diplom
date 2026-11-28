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
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import cosign_fixtures as fixtures

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

    # --- review #168 item 2/3: private keyless trust chain flags (v3.1.3) ----

    def test_sign_accepts_private_fulcio_rekor_oidc_issuer(self):
        # review #168 item 3: sign is bound to the PRIVATE Fulcio/Rekor/OIDC
        # endpoints explicitly (no public-sigstore fallback). --fulcio-url/
        # --rekor-url are the pinned v3.1.3 mechanism (deprecated in later cosign,
        # but the pin is immutable).
        r = self._run("sign", "--fulcio-url", "https://fulcio.private.example",
                      "--rekor-url", "https://rekor.private.example",
                      "--oidc-issuer", "https://o.private.example",
                      "--oidc-client-id", "sigstore", "--help")
        self.assertEqual(r.returncode, 0)
        self.assertNotIn("unknown", r.stderr)

    def test_attest_accepts_oidc_client_id_and_private_endpoints(self):
        # review #168 item 2: both attestations request the LITERAL sigstore
        # audience (--oidc-client-id) and the private endpoints.
        r = self._run("attest", "--type", "spdxjson",
                      "--oidc-client-id", "sigstore",
                      "--fulcio-url", "https://fulcio.private.example",
                      "--rekor-url", "https://rekor.private.example",
                      "--oidc-issuer", "https://o.private.example", "--help")
        self.assertEqual(r.returncode, 0)
        self.assertNotIn("unknown", r.stderr)

    def test_verify_accepts_private_rekor_and_trusted_root(self):
        # review #168 item 3: verify is bound to the PRIVATE trusted root + Rekor.
        r = self._run("verify",
                      "--certificate-identity", "X",
                      "--certificate-oidc-issuer", "Y",
                      "--rekor-url", "https://rekor.private.example",
                      "--trusted-root", "/nonexistent-root.json", "--help")
        self.assertEqual(r.returncode, 0)
        self.assertNotIn("unknown", r.stderr)

    def test_verify_attestation_accepts_private_rekor_and_trusted_root(self):
        # review #168 item 3: verify-attestation is bound to the PRIVATE trusted
        # root + Rekor for both slsaprovenance and spdxjson.
        r = self._run("verify-attestation", "--type", "slsaprovenance",
                      "--certificate-identity", "X",
                      "--certificate-oidc-issuer", "Y",
                      "--rekor-url", "https://rekor.private.example",
                      "--trusted-root", "/nonexistent-root.json",
                      "--policy", "/nonexistent.cue", "--help")
        self.assertEqual(r.returncode, 0)
        self.assertNotIn("unknown", r.stderr)


@unittest.skipUnless(COSIGN, "cosign v3.1.3 binary unavailable (offline env)")
class TestCosignLoaderRuntime(unittest.TestCase):
    """review #170 + review #172: RUNTIME acceptance of the ACTUAL cosign v3.1.3
    signing loader (``signcommon.LoadTrustedMaterialAndSigningConfig``) driven
    with real parameters — NOT ``--help``.

    This is the LOADER-COMPATIBILITY half of the split. The ORIGIN-POLICY half
    (a foreign URL INSIDE the signing-config JSON, no CLI override) is enforced
    by the gate and unit-tested in ``test_owner_gate_barrier.py``. Here the
    actual binary proves, OFFLINE:
      * a coherent ``--signing-config`` + ``--trusted-root`` (no service URLs)
        is ACCEPTED by the loader — the command proceeds PAST the loader to the
        image-access stage ("accessing image"), a POSITIVE observable loader
        pass, never a loader error (a later-stage network failure is expected
        offline and is NOT a loader failure);
      * a STRUCTURALLY-CORRECT trusted root whose certificate / tlog public key
        ``rawBytes`` is unreadable (garbage base64) is REJECTED by the loader
        ("loading trusted root: failed to parse …");
      * an explicit ``--fulcio-url`` alongside ``--signing-config`` is REJECTED
        by the loader ("cannot specify service URLs and use signing config") —
        the loader's OWN flag-incompatibility, distinct from the gate's ban on a
        foreign URL inside the JSON.
    """

    IMG = ("registry.example/image@sha256:0123456789abcdef0123456789abcdef"
           "0123456789abcdef0123456789abcdef")
    LOADER_ERRORS = (
        "cannot specify service URLs and use signing config",
        "loading trusted root",
        "error reading signing config",
        "must provide --new-bundle-format",
        "failed to parse certificate",
        "failed to parse public key",
    )

    def _write(self, obj):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        p = Path(d.name) / "fixture.json"
        p.write_text(json.dumps(obj))
        return str(p)

    def _run(self, *args):
        assert COSIGN is not None  # guarded by skipUnless
        return subprocess.run([COSIGN, *args], capture_output=True, text=True,
                              timeout=30)

    def test_loader_accepts_coherent_signing_config_and_root(self):
        # POSITIVE with an OBSERVABLE loader pass: the command must reach the
        # image-access stage ("accessing image"), NOT merely avoid the loader
        # error strings. A later-stage network/reference failure is expected
        # offline and proves the loader already parsed both files.
        sc = self._write(fixtures.make_signing_config())
        tr = self._write(fixtures.make_trusted_root())
        r = self._run("sign", "--signing-config", sc, "--trusted-root", tr,
                      "--new-bundle-format", "--oidc-client-id", "sigstore",
                      "--yes", self.IMG)
        out = (r.stderr or "") + (r.stdout or "")
        self.assertNotEqual(r.returncode, 0)  # offline: fails AFTER the loader
        self.assertIn("accessing image", out)  # reached the image-access stage
        for err in self.LOADER_ERRORS:
            self.assertNotIn(err, out)

    def test_loader_rejects_explicit_service_url_alongside_signing_config(self):
        # The loader itself refuses an explicit --fulcio-url alongside
        # --signing-config (flag incompatibility). Distinct from the gate's
        # origin-policy ban on a foreign URL INSIDE the JSON (unit-tested in
        # test_owner_gate_barrier.py).
        sc = self._write(fixtures.make_signing_config())
        tr = self._write(fixtures.make_trusted_root())
        r = self._run("sign", "--signing-config", sc, "--trusted-root", tr,
                      "--new-bundle-format", "--fulcio-url", "https://evil.example",
                      "--yes", self.IMG)
        out = (r.stderr or "") + (r.stdout or "")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("cannot specify service URLs and use signing config", out)

    def test_loader_rejects_unreadable_certificate(self):
        # A STRUCTURALLY-CORRECT trusted root whose CA certificate rawBytes is
        # not a readable X.509 certificate (garbage base64) is refused by the
        # loader ("failed to parse certificate"). The gate refuses the SAME
        # fixture BEFORE push (test_unreadable_certificate_rejected_even_with_correct_digest).
        sc = self._write(fixtures.make_signing_config())
        bad = fixtures.make_trusted_root()
        bad["certificateAuthorities"][0]["certChain"]["certificates"][0]["rawBytes"] = (
            "bm90LWEtcGVtLWdhcmJhZ2U=")
        tr = self._write(bad)
        r = self._run("sign", "--signing-config", sc, "--trusted-root", tr,
                      "--new-bundle-format", "--yes", self.IMG)
        out = (r.stderr or "") + (r.stdout or "")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("loading trusted root", out)

    def test_loader_rejects_unreadable_tlog_key(self):
        # A structurally-correct root whose tlog public key rawBytes is not a
        # readable public key (garbage base64) is refused by the loader
        # ("failed to parse public key").
        sc = self._write(fixtures.make_signing_config())
        bad = fixtures.make_trusted_root()
        bad["tlogs"][0]["publicKey"]["rawBytes"] = "bm90LWEtcGVtLWdhcmJhZ2U="
        tr = self._write(bad)
        r = self._run("sign", "--signing-config", sc, "--trusted-root", tr,
                      "--new-bundle-format", "--yes", self.IMG)
        out = (r.stderr or "") + (r.stdout or "")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("loading trusted root", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
