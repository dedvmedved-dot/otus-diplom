#!/usr/bin/env python3
"""Unit tests for the Forgejo lock-update gate (granular functions).

Exercises each stage of the admission chain independently, with synthetic inputs
only (no build, no registry, no credentials). The full end-to-end chain (positive
scratch-lock case + the four "blocking discrepancy" classes) is covered by
test_forgejo_offline_integration.py; this file pins the per-function contracts.
"""
import hashlib
import json
import time
import unittest

import forgejo_lock_gate as gate

PINNED = "d22aa8f1170deaf09580518916ea02c7c4d8bfba"
TOOLS = "a" * 40
OWNER = "owner-otus@example"
REGISTRY = "registry.example"
IMAGE = REGISTRY + "/aiopslab/otus-diplom-portal"
RUN_ID = "1234567890"
NOW = 2000000000  # 2033-05-18T03:33:20Z

MANIFEST = b'{"schemaVersion":2,"mediaType":"application/vnd.oci.image.manifest.v1+json"}'
DIGEST = "sha256:" + hashlib.sha256(MANIFEST).hexdigest()


def iso(epoch):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(epoch))


def make_gate(owner=OWNER, source=PINNED, workflow=TOOLS, repository="aiopslab/otus-diplom",
              package=IMAGE, ref="refs/heads/main", mode="LIVE", issued=None,
              expiry=1, attempt=1):
    return {
        "owner": owner,
        "source_sha": source,
        "workflow_sha": workflow,
        "repository": repository,
        "package": package,
        "ref": ref,
        "mode": mode,
        "issued_at_utc": issued or iso(NOW - 60),
        "expiry_hours": expiry,
        "attempt": attempt,
    }


def make_statement(digest=DIGEST, image=IMAGE, source=PINNED, workflow=TOOLS,
                   run_id=RUN_ID, builder=None, predicate_type=None, build_type=None):
    pred = gate.build_predicate(source, workflow, run_id)
    if builder is not None:
        pred["builder"]["id"] = builder
    if build_type is not None:
        pred["buildType"] = build_type
    return {
        "_type": "https://in-toto.io/Statement/v1",
        "subject": [{"name": image, "digest": {"sha256": digest[len("sha256:"):]}}],
        "predicateType": predicate_type or gate.SLSA,
        "predicate": pred,
    }


class TestOwnerGate(unittest.TestCase):
    def _verify(self, gate_doc, **kw):
        params = dict(expected_owner=OWNER, expected_source_sha=PINNED,
                      expected_workflow_sha=TOOLS, expected_repository="aiopslab/otus-diplom",
                      expected_package=IMAGE, expected_ref="refs/heads/main",
                      run_attempt="1", now=NOW)
        params.update(kw)
        return gate.verify_owner_gate(gate_doc, **params)

    def test_valid(self):
        ok, reason = self._verify(make_gate())
        self.assertTrue(ok, reason)

    def test_missing_gate(self):
        ok, reason = self._verify(None)
        self.assertFalse(ok)
        self.assertIn("not an object", reason)

    def test_foreign_owner(self):
        ok, reason = self._verify(make_gate(owner="intruder@evil.example"))
        self.assertFalse(ok)
        self.assertIn("foreign owner", reason)

    def test_wrong_source_sha(self):
        ok, reason = self._verify(make_gate(source="b" * 40))
        self.assertFalse(ok)
        self.assertIn("source_sha", reason)

    def test_wrong_workflow_sha(self):
        ok, reason = self._verify(make_gate(workflow="b" * 40))
        self.assertFalse(ok)
        self.assertIn("workflow_sha", reason)

    def test_wrong_repository(self):
        ok, reason = self._verify(make_gate(repository="other/repo"))
        self.assertFalse(ok)
        self.assertIn("repository", reason)

    def test_wrong_package(self):
        ok, reason = self._verify(make_gate(package="registry.example/other"))
        self.assertFalse(ok)
        self.assertIn("package", reason)

    def test_expired(self):
        ok, reason = self._verify(make_gate(issued=iso(NOW - 7200), expiry=1))
        self.assertFalse(ok)
        self.assertIn("expired", reason)

    def test_future(self):
        ok, reason = self._verify(make_gate(issued=iso(NOW + 60)))
        self.assertFalse(ok)
        self.assertIn("future", reason)

    def test_wrong_mode(self):
        ok, reason = self._verify(make_gate(mode="TEST_ONLY"))
        self.assertFalse(ok)
        self.assertIn("LIVE", reason)

    def test_attempt_not_one(self):
        ok, reason = self._verify(make_gate(attempt=2))
        self.assertFalse(ok)
        self.assertIn("attempt", reason)

    def test_run_attempt_not_one(self):
        ok, reason = self._verify(make_gate(), run_attempt="2")
        self.assertFalse(ok)
        self.assertIn("attempt", reason)


class TestFileInventory(unittest.TestCase):
    def test_valid(self):
        ok, reason = gate.verify_file_inventory(
            list(gate.REQUIRED_SOURCE_FILES), list(gate.REQUIRED_TOOLS_FILES),
            source_pin=PINNED, tools_pin=TOOLS)
        self.assertTrue(ok, reason)

    def test_missing_source_file(self):
        src = list(gate.REQUIRED_SOURCE_FILES)[:-1]
        ok, reason = gate.verify_file_inventory(src, list(gate.REQUIRED_TOOLS_FILES),
                                                source_pin=PINNED, tools_pin=TOOLS)
        self.assertFalse(ok)
        self.assertIn("source files missing", reason)

    def test_missing_tools_file(self):
        tls = list(gate.REQUIRED_TOOLS_FILES)[:-1]
        ok, reason = gate.verify_file_inventory(list(gate.REQUIRED_SOURCE_FILES), tls,
                                                source_pin=PINNED, tools_pin=TOOLS)
        self.assertFalse(ok)
        self.assertIn("tools files missing", reason)

    def test_tools_smuggled_into_source(self):
        src = list(gate.REQUIRED_SOURCE_FILES) + [gate.REQUIRED_TOOLS_FILES[0]]
        ok, reason = gate.verify_file_inventory(src, list(gate.REQUIRED_TOOLS_FILES),
                                                source_pin=PINNED, tools_pin=TOOLS)
        self.assertFalse(ok)
        self.assertIn("smuggled", reason)

    def test_same_pins_rejected(self):
        ok, reason = gate.verify_file_inventory(
            list(gate.REQUIRED_SOURCE_FILES), list(gate.REQUIRED_TOOLS_FILES),
            source_pin=PINNED, tools_pin=PINNED)
        self.assertFalse(ok)
        self.assertIn("differ", reason)


class TestRegistry(unittest.TestCase):
    def test_fetch_refuses_foreign_host_before_transport(self):
        calls = []

        def transport(host, repo, dg):
            calls.append(host)
            return MANIFEST, DIGEST

        with self.assertRaises(ValueError) as cm:
            gate.fetch_registry_manifest(REGISTRY, "evil.example", "x", DIGEST, transport)
        self.assertIn("trusted registry", str(cm.exception))
        self.assertEqual(calls, [])  # transport never invoked => credentials never offered

    def test_fetch_allowed_host_calls_transport(self):
        calls = []

        def transport(host, repo, dg):
            calls.append((host, repo, dg))
            return MANIFEST, DIGEST

        body, dcd = gate.fetch_registry_manifest(REGISTRY, REGISTRY, "a/otus-diplom-portal", DIGEST, transport)
        self.assertEqual(calls, [(REGISTRY, "a/otus-diplom-portal", DIGEST)])
        self.assertEqual(body, MANIFEST)
        self.assertEqual(dcd, DIGEST)

    def test_verify_manifest_valid(self):
        ok, reason = gate.verify_registry_manifest(REGISTRY, REGISTRY, IMAGE, DIGEST, MANIFEST, DIGEST)
        self.assertTrue(ok, reason)

    def test_verify_manifest_wrong_registry(self):
        ok, reason = gate.verify_registry_manifest(REGISTRY, "evil.example", IMAGE, DIGEST, MANIFEST, DIGEST)
        self.assertFalse(ok)
        self.assertIn("trusted registry", reason)

    def test_verify_manifest_image_ref_foreign(self):
        ok, reason = gate.verify_registry_manifest(REGISTRY, REGISTRY, "evil.example/portal", DIGEST, MANIFEST, DIGEST)
        self.assertFalse(ok)
        self.assertIn("image_ref", reason)

    def test_verify_manifest_bytes_mismatch(self):
        ok, reason = gate.verify_registry_manifest(REGISTRY, REGISTRY, IMAGE, DIGEST, b"tampered", DIGEST)
        self.assertFalse(ok)
        self.assertIn("bytes", reason)

    def test_verify_manifest_dcd_mismatch(self):
        ok, reason = gate.verify_registry_manifest(REGISTRY, REGISTRY, IMAGE, DIGEST, MANIFEST, "sha256:" + "f" * 64)
        self.assertFalse(ok)
        self.assertIn("Docker-Content-Digest", reason)


class TestVerifiedStatement(unittest.TestCase):
    def test_parse_raw_statement(self):
        text = json.dumps(make_statement()) + "\n"
        stmts = gate.parse_verified_attestation(text)
        self.assertEqual(len(stmts), 1)
        self.assertEqual(stmts[0]["predicateType"], gate.SLSA)

    def test_parse_dsse_envelope(self):
        import base64
        stmt = make_statement()
        envelope = {"payloadType": "application/vnd.in-toto+json",
                    "payload": base64.b64encode(json.dumps(stmt).encode()).decode(),
                    "signatures": [{"sig": "aa", "keyid": ""}]}
        stmts = gate.parse_verified_attestation(json.dumps(envelope) + "\n")
        self.assertEqual(len(stmts), 1)
        self.assertEqual(stmts[0]["_type"], stmt["_type"])

    def _check(self, stmt, **kw):
        params = dict(expected_image_ref=IMAGE, expected_digest=DIGEST,
                      expected_source_sha=PINNED, expected_workflow_sha=TOOLS,
                      expected_run_id=RUN_ID, expected_identity=gate.WORKFLOW_IDENTITY,
                      expected_repository="aiopslab/otus-diplom", expected_ref="refs/heads/main",
                      expected_workflow_file=gate.WORKFLOW_FILE, expected_build_type=gate.BUILD_TYPE)
        params.update(kw)
        return gate.check_verified_statement(stmt, **params)

    def test_valid(self):
        ok, reason = self._check(make_statement())
        self.assertTrue(ok, reason)

    def test_wrong_subject_digest(self):
        ok, reason = self._check(make_statement(digest="sha256:" + "f" * 64))
        self.assertFalse(ok)
        self.assertIn("subject", reason)

    def test_wrong_subject_image(self):
        ok, reason = self._check(make_statement(image="evil.example/portal"))
        self.assertFalse(ok)
        self.assertIn("subject", reason)

    def test_wrong_builder(self):
        ok, reason = self._check(make_statement(builder="https://github.com/evil/wf@main"))
        self.assertFalse(ok)
        self.assertIn("builder", reason)

    def test_wrong_source_material(self):
        ok, reason = self._check(make_statement(source="b" * 40))
        self.assertFalse(ok)
        self.assertIn("materials", reason)

    def test_wrong_workflow_sha(self):
        ok, reason = self._check(make_statement(workflow="b" * 40))
        self.assertFalse(ok)
        self.assertIn("workflow SHA", reason)

    def test_wrong_run_id(self):
        ok, reason = self._check(make_statement(run_id="999"))
        self.assertFalse(ok)
        self.assertIn("run id", reason)

    def test_wrong_predicate_type(self):
        ok, reason = self._check(make_statement(predicate_type="https://spdx.dev/Document"))
        self.assertFalse(ok)
        self.assertIn("predicateType", reason)

    def test_wrong_build_type(self):
        ok, reason = self._check(make_statement(build_type="https://github.com/Attestations/GitHubActionsWorkflow@v1"))
        self.assertFalse(ok)
        self.assertIn("buildType", reason)


class TestApplyLockPair(unittest.TestCase):
    LOCK = 'image:\n  registry: "%s"\n  digest: "NOT_VERIFIED"   # final digest only after reproducible build (G2)\n  base: "scratch"\n  base_digest: "NOT_APPLICABLE_EMPTY_BASE"\n' % REGISTRY

    def test_writes_pair(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as td:
            lock = Path(td) / "versions.lock"
            lock.write_text(self.LOCK)
            gate.apply_lock_pair(lock, REGISTRY, DIGEST)
            text = lock.read_text()
            self.assertIn('registry: "%s"' % REGISTRY, text)
            self.assertIn('digest: "%s"' % DIGEST, text)
            self.assertNotIn("NOT_VERIFIED", text)

    def test_rejects_registry_pair_mismatch(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as td:
            lock = Path(td) / "versions.lock"
            lock.write_text(self.LOCK.replace(REGISTRY, "ghcr.io/dedvmedved-dot/otus-diplom-portal"))
            with self.assertRaises(RuntimeError) as cm:
                gate.apply_lock_pair(lock, REGISTRY, DIGEST)
            self.assertIn("pair mismatch", str(cm.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)
