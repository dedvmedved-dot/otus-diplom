#!/usr/bin/env python3
"""Unit tests for the Forgejo lock-update gate (granular functions).

Exercises each stage of the admission chain independently, with synthetic inputs
only (no build, no registry, no credentials). The full end-to-end chain (positive
scratch-lock case + the four "blocking discrepancy" classes) is covered by
test_forgejo_offline_integration.py; this file pins the per-function contracts,
including the review #55 boundary contracts (trusted-origin-only HTTP transport,
owner confirmation via actor, single-run binding, separate source/tools/workflow
pins, section-aware lock write).
"""
import base64
import hashlib
import json
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

import forgejo_lock_gate as gate

PINNED = "d22aa8f1170deaf09580518916ea02c7c4d8bfba"
TOOLS = "a" * 40
WORKFLOW = "c" * 40
OWNER = "owner-otus@example"
REGISTRY = "registry.example"
IMAGE = REGISTRY + "/aiopslab/otus-diplom-portal"
RUN_ID = "1234567890"
NOW = 2000000000  # 2033-05-18T03:33:20Z

MANIFEST = b'{"schemaVersion":2,"mediaType":"application/vnd.oci.image.manifest.v1+json"}'
DIGEST = "sha256:" + hashlib.sha256(MANIFEST).hexdigest()


def iso(epoch):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(epoch))


def make_gate(owner=OWNER, source=PINNED, tools=TOOLS, workflow=WORKFLOW,
              repository="aiopslab/otus-diplom", package=IMAGE, ref="refs/heads/main",
              mode="LIVE", issued=None, expiry=1, attempt=1, run_id=RUN_ID):
    return {
        "owner": owner,
        "source_sha": source,
        "tools_sha": tools,
        "workflow_sha": workflow,
        "repository": repository,
        "package": package,
        "ref": ref,
        "mode": mode,
        "issued_at_utc": issued or iso(NOW - 60),
        "expiry_hours": expiry,
        "attempt": attempt,
        "run_id": run_id,
    }


def make_statement(digest=DIGEST, image=IMAGE, source=PINNED, workflow=WORKFLOW,
                   tools=TOOLS, run_id=RUN_ID, builder=None, predicate_type=None,
                   build_type=None):
    pred = gate.build_predicate(source, workflow, tools, run_id)
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
                      expected_tools_sha=TOOLS, expected_workflow_sha=WORKFLOW,
                      expected_repository="aiopslab/otus-diplom", expected_package=IMAGE,
                      expected_ref="refs/heads/main", actor=OWNER, run_id=RUN_ID,
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

    def test_actor_missing(self):
        ok, reason = self._verify(make_gate(), actor=None)
        self.assertFalse(ok)
        self.assertIn("actor", reason)

    def test_actor_does_not_confirm_owner(self):
        ok, reason = self._verify(make_gate(), actor="intruder@evil.example")
        self.assertFalse(ok)
        self.assertIn("actor", reason)

    def test_run_id_missing(self):
        ok, reason = self._verify(make_gate(), run_id=None)
        self.assertFalse(ok)
        self.assertIn("run id", reason)

    def test_run_id_not_bound_to_run(self):
        ok, reason = self._verify(make_gate(run_id="different-run"))
        self.assertFalse(ok)
        self.assertIn("run_id", reason)

    def test_wrong_source_sha(self):
        ok, reason = self._verify(make_gate(source="b" * 40))
        self.assertFalse(ok)
        self.assertIn("source_sha", reason)

    def test_wrong_tools_sha(self):
        ok, reason = self._verify(make_gate(tools="b" * 40))
        self.assertFalse(ok)
        self.assertIn("tools_sha", reason)

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

    def test_all_required_source_files_are_real_source_tree_files(self):
        # The expanded list (review #55 item 2) must name files that actually
        # exist in the pinned source tree, not invent new ones.
        import subprocess
        repo_root = Path(__file__).resolve().parents[2]
        tree = subprocess.run(
            ["git", "ls-tree", "-r", "--name-only", PINNED, "--", "portal/"],
            capture_output=True, text=True, check=True, cwd=str(repo_root)).stdout.splitlines()
        missing = [f for f in gate.REQUIRED_SOURCE_FILES if f not in tree]
        self.assertEqual(missing, [], "REQUIRED_SOURCE_FILES names files not in the source tree: %s" % missing)

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


class _FakeResp:
    def __init__(self, body=b"", dcd=None):
        self._body = body
        self.headers = {"Docker-Content-Digest": dcd} if dcd else {}

    def read(self):
        return self._body


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

    # --- trusted-origin / redirect / realm policy (review #55 item 3) --------

    def test_trusted_origin_same_host_https(self):
        self.assertTrue(gate._trusted_origin_ok("https://registry.example/v2/", "registry.example"))
        self.assertTrue(gate._trusted_origin_ok("https://registry.example:443/x", "registry.example"))

    def test_trusted_origin_rejects_http(self):
        self.assertFalse(gate._trusted_origin_ok("http://registry.example/v2/", "registry.example"))

    def test_trusted_origin_rejects_foreign_host(self):
        self.assertFalse(gate._trusted_origin_ok("https://evil.example/v2/", "registry.example"))

    def test_bearer_token_url_trusted(self):
        url = gate._bearer_token_url(
            'Bearer realm="https://registry.example/token",service="registry.example",scope="pull"',
            "registry.example")
        self.assertTrue(url.startswith("https://registry.example/token?"))

    def test_bearer_token_url_rejects_foreign_realm(self):
        with self.assertRaises(ValueError) as cm:
            gate._bearer_token_url('Bearer realm="https://evil.example/token",service="x"', "registry.example")
        self.assertIn("trusted HTTPS origin", str(cm.exception))

    def test_bearer_token_url_rejects_http_realm(self):
        with self.assertRaises(ValueError):
            gate._bearer_token_url('Bearer realm="http://registry.example/token",service="x"', "registry.example")

    def test_bearer_token_url_rejects_missing_realm(self):
        with self.assertRaises(ValueError):
            gate._bearer_token_url('Basic realm="x"', "registry.example")

    def test_redirect_handler_refuses(self):
        handler = gate._RefuseRedirect()
        req = urllib.request.Request("https://registry.example/v2/")
        with self.assertRaises(urllib.error.HTTPError) as cm:
            handler.redirect_request(req, None, 302, "Found", {}, "https://evil.example/v2/")
        self.assertEqual(cm.exception.code, 302)

    def test_generic_transport_foreign_realm_refused_before_basic(self):
        # The REAL execution transport must refuse a foreign bearer realm BEFORE
        # sending Basic credentials anywhere except the trusted host.
        calls = []

        def fake_urlopen(url, headers=None, timeout=30):
            calls.append((url, headers))
            if url == "https://registry.example/v2/":
                raise urllib.error.HTTPError(
                    url, 401, "Unauthorized",
                    {"WWW-Authenticate": 'Bearer realm="https://evil.example/token",service="x"'},
                    None)
            raise AssertionError("must not reach foreign origin: " + url)

        with mock.patch.dict("os.environ", {"REGISTRY_USERNAME": "u", "REGISTRY_TOKEN": "t"}):
            with self.assertRaises(ValueError) as cm:
                gate._generic_oci_transport(REGISTRY, "a/otus-diplom-portal", DIGEST, urlopen=fake_urlopen)
        self.assertIn("trusted HTTPS origin", str(cm.exception))
        self.assertEqual(len(calls), 1)  # only the /v2/ ping; never the foreign realm
        self.assertEqual(calls[0][0], "https://registry.example/v2/")

    def test_generic_transport_trusted_realm_flow(self):
        calls = []

        def fake_urlopen(url, headers=None, timeout=30):
            calls.append((url, headers))
            if url == "https://registry.example/v2/":
                raise urllib.error.HTTPError(
                    url, 401, "Unauthorized",
                    {"WWW-Authenticate": 'Bearer realm="https://registry.example/token",service="registry.example"'},
                    None)
            if url.startswith("https://registry.example/token"):
                return _FakeResp(b'{"token":"tok"}')
            if "/manifests/" in url:
                self.assertIn("Bearer tok", headers.get("Authorization", ""))
                return _FakeResp(MANIFEST, DIGEST)
            raise AssertionError("unexpected url: " + url)

        with mock.patch.dict("os.environ", {"REGISTRY_USERNAME": "u", "REGISTRY_TOKEN": "t"}):
            body, dcd = gate._generic_oci_transport(REGISTRY, "a/otus-diplom-portal", DIGEST, urlopen=fake_urlopen)
        self.assertEqual(body, MANIFEST)
        self.assertEqual(dcd, DIGEST)
        # Basic only ever sent to the trusted host; Bearer only to the trusted host.
        for url, headers in calls:
            self.assertTrue(gate._trusted_origin_ok(url, REGISTRY), url)


class TestVerifiedStatement(unittest.TestCase):
    def test_parse_raw_statement(self):
        text = json.dumps(make_statement()) + "\n"
        stmts = gate.parse_verified_attestation(text)
        self.assertEqual(len(stmts), 1)
        self.assertEqual(stmts[0]["predicateType"], gate.SLSA)

    def test_parse_dsse_envelope(self):
        stmt = make_statement()
        envelope = {"payloadType": "application/vnd.in-toto+json",
                    "payload": base64.b64encode(json.dumps(stmt).encode()).decode(),
                    "signatures": [{"sig": "aa", "keyid": ""}]}
        stmts = gate.parse_verified_attestation(json.dumps(envelope) + "\n")
        self.assertEqual(len(stmts), 1)
        self.assertEqual(stmts[0]["_type"], stmt["_type"])

    def _check(self, stmt, **kw):
        params = dict(expected_image_ref=IMAGE, expected_digest=DIGEST,
                      expected_source_sha=PINNED, expected_tools_sha=TOOLS,
                      expected_workflow_sha=WORKFLOW, expected_run_id=RUN_ID,
                      expected_identity=gate.WORKFLOW_IDENTITY,
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

    def test_wrong_tools_material(self):
        ok, reason = self._check(make_statement(tools="b" * 40))
        self.assertFalse(ok)
        self.assertIn("tools SHA", reason)

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


# A representative real-format lock: the `image:` section holds the FULL image
# name in `registry:` (review #55 item 5), surrounded by other sections that
# must be preserved byte-for-byte.
REAL_LOCK = (
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


class TestApplyLockPair(unittest.TestCase):
    def test_writes_pair_preserving_other_sections(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as td:
            lock = Path(td) / "versions.lock"
            lock.write_text(REAL_LOCK)
            gate.apply_lock_pair(lock, IMAGE, DIGEST)
            text = lock.read_text()
            self.assertIn('registry: "%s"' % IMAGE, text)
            self.assertIn('digest: "%s"' % DIGEST, text)
            self.assertNotIn('digest: "NOT_VERIFIED"', text)
            # other sections preserved
            self.assertIn('baseline: "P8C-R1"', text)
            self.assertIn('go: "1.27.3"', text)
            self.assertIn('base: "scratch"', text)
            self.assertIn('checkout: "11bd71901bbe5b1630ceea73d27597364c9af683"', text)

    def test_rejects_foreign_image_not_rewritten(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as td:
            lock = Path(td) / "versions.lock"
            lock.write_text(REAL_LOCK.replace(IMAGE, "ghcr.io/other/image"))
            before = lock.read_text()
            with self.assertRaises(RuntimeError) as cm:
                gate.apply_lock_pair(lock, IMAGE, DIGEST)
            self.assertIn("pair mismatch", str(cm.exception))
            self.assertEqual(lock.read_text(), before)  # foreign image NOT rewritten

    def test_rejects_host_only_mismatch(self):
        # Passing the bare host (not the full image) must not match the full
        # image name stored in the lock.
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as td:
            lock = Path(td) / "versions.lock"
            lock.write_text(REAL_LOCK)
            with self.assertRaises(RuntimeError) as cm:
                gate.apply_lock_pair(lock, REGISTRY, DIGEST)  # bare host
            self.assertIn("pair mismatch", str(cm.exception))

    def test_rejects_already_set_digest(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as td:
            lock = Path(td) / "versions.lock"
            lock.write_text(REAL_LOCK.replace("NOT_VERIFIED", 'sha256:' + 'd' * 64))
            with self.assertRaises(RuntimeError) as cm:
                gate.apply_lock_pair(lock, IMAGE, DIGEST)
            self.assertIn("already set", str(cm.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)
