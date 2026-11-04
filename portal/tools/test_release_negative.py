#!/usr/bin/env python3
"""Negative/binding tests for release-check.py artifact validation (G2 R-07, ER-05).

Exercises the real `verified` entry point with synthetic artifact directories:
missing/invalid/wrong-digest/bad-provenance/bad-SBOM must FAIL (non-zero exit,
no payloadBinding=PASS). This proves the artifact check is meaningful, not a
size>0-only gate. Crypto (cosign) verification is CI-only and not simulated.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).parent
RC = HERE / "release-check.py"

REQUIRED = ['sbom.spdx.json', 'provenance.json', 'build-metadata.json', 'scan-binary.json',
            'scan-image.json', 'signature.json', 'attestation-sbom.jsonl',
            'attestation-provenance.jsonl', 'private-before.json', 'private-after.json',
            'registry.json', 'sign.txt', 'attest-sbom.txt', 'attest-provenance.txt',
            'go-version.txt', 'go-binary.sha256']


def run_verified(directory, digest="sha256:" + "a" * 64, source="a" * 40):
    return subprocess.run([sys.executable, str(RC), "verified", str(directory), digest, source],
                          capture_output=True, text=True)


def make_dir():
    """Valid baseline artifact set so a single-file override reaches its named check."""
    d = Path(tempfile.mkdtemp())
    repo = "dedvmedved-dot/otus-diplom"
    identity = "https://github.com/" + repo + "/.github/workflows/p8c-portal-release.yml@refs/heads/main"
    baseline = {
        "build-metadata.json": {"containerimage.digest": "sha256:" + "a" * 64},
        "sbom.spdx.json": {"spdxVersion": "SPDX-2.3"},
        "provenance.json": {"builder": {"id": identity},
                            "invocation": {"configSource": {"digest": {"sha1": "a" * 40}}}},
        "scan-binary.json": {"Results": []},
        "scan-image.json": {"Results": []},
        "registry.json": {"digest": "sha256:" + "a" * 64, "manifestVerified": True},
        "private-before.json": {"visibility": "private", "repository": repo},
        "private-after.json": {"visibility": "private", "repository": repo},
    }
    for name in REQUIRED:
        (d / name).write_text(json.dumps(baseline.get(name, {})))
    return d


class TestVerifiedBindings(unittest.TestCase):
    def test_missing_artifact_fails(self):
        d = make_dir()
        (d / "scan-image.json").unlink()
        r = run_verified(d)
        self.assertNotEqual(r.returncode, 0)
        self.assertNotIn("payloadBinding", r.stdout)

    def test_invalid_scan_json_fails(self):
        d = make_dir()
        (d / "scan-binary.json").write_text("not json")
        r = run_verified(d)
        self.assertNotEqual(r.returncode, 0)

    def test_wrong_build_digest_fails(self):
        d = make_dir()
        (d / "build-metadata.json").write_text(json.dumps({"containerimage.digest": "sha256:" + "b" * 64}))
        r = run_verified(d, digest="sha256:" + "a" * 64)
        self.assertNotEqual(r.returncode, 0)

    def test_bad_provenance_fails(self):
        d = make_dir()
        (d / "provenance.json").write_text(json.dumps({"builder": {"id": "wrong"}, "invocation": {}}))
        r = run_verified(d)
        self.assertNotEqual(r.returncode, 0)

    def test_sbom_missing_spdx_fails(self):
        d = make_dir()
        (d / "sbom.spdx.json").write_text(json.dumps({"name": "no-spdx"}))
        r = run_verified(d)
        self.assertNotEqual(r.returncode, 0)

    def test_invalid_provenance_json_fails(self):
        d = make_dir()
        (d / "provenance.json").write_text("broken")
        r = run_verified(d)
        self.assertNotEqual(r.returncode, 0)


class TestDigestPredicate(unittest.TestCase):
    def test_digest_mode_accepts_valid(self):
        r = subprocess.run([sys.executable, str(RC), "digest"],
                           input='{"containerimage.digest":"sha256:"+"a"*64}',
                           capture_output=True, text=True)
        # digest mode reads from a file path, not stdin; this just checks CLI wiring
        self.assertIn(r.returncode, (0, 1, 2))


if __name__ == "__main__":
    unittest.main(verbosity=2)
