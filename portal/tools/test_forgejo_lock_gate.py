#!/usr/bin/env python3
"""Negative/binding tests for the Forgejo Actions lock-update gate.

Exercises the SAME validation implementation the (inactive) Forgejo workflow
uses (forgejo_lock_gate.decide_lock_update / --apply). Proves, with synthetic
inputs only (no build, no registry, no credentials):

  - a source SHA that does NOT match the pinned literal => lock update NOT allowed;
  - missing / non-binding SLSA provenance => lock update NOT allowed;
  - a tag (or any non-sha256) in place of the digest => lock update NOT allowed;
  - the valid case => allowed, and --apply writes the digest into a scratch lock
    file only in the valid case (negative cases leave the file byte-identical).

Crypto (cosign verify/verify-attestation) is CI-only and is NOT simulated here;
this harness validates the fail-closed decision over the parsed provenance, which
is the offline-verifiable half of the lock-update contract.
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import forgejo_lock_gate as gate

PINNED = "d22aa8f1170deaf09580518916ea02c7c4d8bfba"
IMAGE = "ghcr.io/dedvmedved-dot/otus-diplom-portal"
DIGEST = "sha256:" + "a" * 64
OTHER_SHA = "b" * 40


def make_provenance(source=PINNED, digest=DIGEST, builder=gate.WORKFLOW_IDENTITY):
    return {
        "builder": {"id": builder},
        "buildType": "https://github.com/Attestations/GitHubActionsWorkflow@v1",
        "invocation": {"configSource": {
            "uri": "git+https://git.aiopslab.online/aiopslab/otus-diplom@refs/heads/main",
            "digest": {"sha1": source}}},
        "subject": [{"name": IMAGE, "digest": {"sha256": digest[len("sha256:"):]}}],
    }


class TestDecideLockUpdate(unittest.TestCase):
    def test_valid_bindings_allowed(self):
        allowed, reason = gate.decide_lock_update(
            source_sha=PINNED, digest=DIGEST,
            provenance=make_provenance(), image_ref=IMAGE, pinned_source_sha=PINNED)
        self.assertTrue(allowed, reason)
        self.assertEqual(reason, "all bindings verified")

    def test_source_sha_mismatch_not_allowed(self):
        allowed, reason = gate.decide_lock_update(
            source_sha=OTHER_SHA, digest=DIGEST,
            provenance=make_provenance(source=PINNED), image_ref=IMAGE, pinned_source_sha=PINNED)
        self.assertFalse(allowed)
        self.assertIn("mismatch", reason)

    def test_missing_provenance_not_allowed(self):
        allowed, reason = gate.decide_lock_update(
            source_sha=PINNED, digest=DIGEST,
            provenance={}, image_ref=IMAGE, pinned_source_sha=PINNED)
        self.assertFalse(allowed)
        self.assertIn("builder", reason)

    def test_provenance_binds_wrong_source_not_allowed(self):
        # provenance binds a DIFFERENT sha1 than the pinned source
        allowed, reason = gate.decide_lock_update(
            source_sha=PINNED, digest=DIGEST,
            provenance=make_provenance(source=OTHER_SHA), image_ref=IMAGE, pinned_source_sha=PINNED)
        self.assertFalse(allowed)
        self.assertIn("source SHA", reason)

    def test_provenance_binds_wrong_digest_not_allowed(self):
        allowed, reason = gate.decide_lock_update(
            source_sha=PINNED, digest=DIGEST,
            provenance=make_provenance(digest="sha256:" + "f" * 64), image_ref=IMAGE,
            pinned_source_sha=PINNED)
        self.assertFalse(allowed)
        self.assertIn("digest", reason)

    def test_tag_instead_of_digest_not_allowed(self):
        allowed, reason = gate.decide_lock_update(
            source_sha=PINNED, digest="candidate",  # a mutable tag, not a digest
            provenance=make_provenance(), image_ref=IMAGE, pinned_source_sha=PINNED)
        self.assertFalse(allowed)
        self.assertIn("tag", reason)

    def test_provenance_wrong_builder_not_allowed(self):
        allowed, reason = gate.decide_lock_update(
            source_sha=PINNED, digest=DIGEST,
            provenance=make_provenance(builder="https://github.com/evil/workflow@main"),
            image_ref=IMAGE, pinned_source_sha=PINNED)
        self.assertFalse(allowed)
        self.assertIn("builder", reason)


class TestApplyLockUpdate(unittest.TestCase):
    LOCK = 'image:\n  registry: "ghcr.io/dedvmedved-dot/otus-diplom-portal"\n' \
           '  digest: "NOT_VERIFIED"   # final digest only after reproducible build (G2)\n' \
           '  base: "scratch"\n  base_digest: "NOT_APPLICABLE_EMPTY_BASE"\n'

    def _run(self, source, prov, digest=DIGEST):
        with tempfile.TemporaryDirectory() as td:
            lock = Path(td) / "versions.lock"
            lock.write_text(self.LOCK)
            prov_path = Path(td) / "provenance.json"
            prov_path.write_text(json.dumps(prov))
            r = subprocess.run(
                [sys.executable, str(Path(__file__).parent / "forgejo_lock_gate.py"),
                 PINNED, source, digest, IMAGE, str(prov_path), "--apply", str(lock)],
                capture_output=True, text=True)
            return r, lock.read_text()

    def test_apply_writes_only_when_allowed(self):
        r, text = self._run(PINNED, make_provenance())
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('digest: "%s"' % DIGEST, text)
        self.assertNotIn("NOT_VERIFIED", text)

    def test_apply_source_mismatch_leaves_lock_untouched(self):
        r, text = self._run(OTHER_SHA, make_provenance(source=PINNED))
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(text, self.LOCK)  # byte-identical: no write
        self.assertIn("NOT ALLOWED", r.stderr)

    def test_apply_missing_provenance_leaves_lock_untouched(self):
        r, text = self._run(PINNED, {})
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(text, self.LOCK)  # byte-identical: no write
        self.assertIn("NOT ALLOWED", r.stderr)

    def test_apply_tag_instead_of_digest_leaves_lock_untouched(self):
        r, text = self._run(PINNED, make_provenance(), digest="candidate")
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(text, self.LOCK)  # byte-identical: no write
        self.assertIn("NOT ALLOWED", r.stderr)


class TestCliCheckMode(unittest.TestCase):
    """CLI `check` mode (no --apply): valid bindings exit 0, mismatch exit nonzero.

    Regression guard for the no-apply argument path of forgejo_lock_gate.main().
    """

    def _run(self, source, prov, digest=DIGEST):
        with tempfile.TemporaryDirectory() as td:
            prov_path = Path(td) / "provenance.json"
            prov_path.write_text(json.dumps(prov))
            r = subprocess.run(
                [sys.executable, str(Path(__file__).parent / "forgejo_lock_gate.py"),
                 PINNED, source, digest, IMAGE, str(prov_path)],
                capture_output=True, text=True)
            return r

    def test_check_valid_bindings_exit_zero(self):
        r = self._run(PINNED, make_provenance())
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('"allowed": true', r.stdout)

    def test_check_source_mismatch_exit_nonzero(self):
        r = self._run(OTHER_SHA, make_provenance(source=PINNED))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("NOT ALLOWED", r.stderr)

    def test_check_missing_provenance_exit_nonzero(self):
        r = self._run(PINNED, {})
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("NOT ALLOWED", r.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
