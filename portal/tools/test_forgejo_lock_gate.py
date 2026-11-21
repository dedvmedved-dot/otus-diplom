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

PINNED = "4c09d6b4a85e2d021516244988f48b92eade7acf"
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
                      run_attempt="1", now=NOW,
                      observed_repository="aiopslab/otus-diplom",
                      observed_ref="refs/heads/main",
                      observed_workflow_sha=WORKFLOW)
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

    # --- review #58 item 1/4: TRIPLE check (policy allowed == owner document
    #     == observed runtime context) -----------------------------------------

    def test_observed_repository_mismatch(self):
        # Document and policy agree on the repository, but the OBSERVED runtime
        # context (github.repository) differs -> refused.
        ok, reason = self._verify(make_gate(), observed_repository="evil.example/repo")
        self.assertFalse(ok)
        self.assertIn("observed repository", reason)

    def test_observed_ref_mismatch(self):
        ok, reason = self._verify(make_gate(), observed_ref="refs/heads/dev")
        self.assertFalse(ok)
        self.assertIn("observed ref", reason)

    def test_observed_workflow_sha_mismatch(self):
        # The owner document binds workflow SHA == policy, but the observed
        # runtime GITHUB_WORKFLOW_SHA differs -> refused BEFORE release.
        ok, reason = self._verify(make_gate(), observed_workflow_sha="b" * 40)
        self.assertFalse(ok)
        self.assertIn("observed workflow SHA", reason)

    def test_document_repository_vs_observed_mismatch(self):
        # Document repo == policy, but observed context differs from BOTH the
        # policy and the document -> refused.
        ok, reason = self._verify(make_gate(repository="aiopslab/otus-diplom"),
                                  observed_repository="other.example/repo")
        self.assertFalse(ok)
        self.assertIn("observed repository", reason)

    def test_observed_workflow_sha_absent(self):
        # Absent runtime workflow SHA (cannot confirm the executed revision) ->
        # refused before release rights (fail-closed, never skipped).
        ok, reason = self._verify(make_gate(), observed_workflow_sha=None)
        self.assertFalse(ok)
        self.assertIn("observed workflow SHA", reason)

    def test_observed_repository_absent(self):
        ok, reason = self._verify(make_gate(), observed_repository=None)
        self.assertFalse(ok)
        self.assertIn("observed repository", reason)

    def test_observed_ref_absent(self):
        ok, reason = self._verify(make_gate(), observed_ref=None)
        self.assertFalse(ok)
        self.assertIn("observed ref", reason)

    def test_policy_workflow_sha_differs_from_agreeing_doc_and_runtime(self):
        # review #61 item 1: the owner document and the observed runtime AGREE on
        # the workflow SHA, but the INDEPENDENT policy pin differs -> refused. The
        # check is over THREE distinct quantities (policy pin / document /
        # runtime), so a document+observed agreement cannot paper over a wrong
        # policy pin (previously the policy pin was the document's own value).
        ok, reason = self._verify(make_gate(workflow=WORKFLOW),   # doc == runtime
                                  expected_workflow_sha="b" * 40)  # policy differs
        self.assertFalse(ok)
        self.assertIn("workflow_sha", reason)


class TestFileInventory(unittest.TestCase):
    def test_valid(self):
        ok, reason = gate.verify_file_inventory(
            list(gate.REQUIRED_SOURCE_FILES), list(gate.REQUIRED_TOOLS_FILES),
            source_pin=PINNED, tools_pin=TOOLS)
        self.assertTrue(ok, reason)

    def test_all_required_source_files_are_real_source_tree_files(self):
        # The expanded list (review #55 item 2 / #58 item 2) must name files that
        # actually exist in the FULL pinned source tree (inputs outside portal/
        # included), not invent new ones.
        import subprocess
        repo_root = Path(__file__).resolve().parents[2]
        tree = subprocess.run(
            ["git", "ls-tree", "-r", "--name-only", PINNED],
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

    # --- review #58 item 2: FULL-tree completeness ---------------------------

    def _full_tree(self):
        import subprocess
        repo_root = Path(__file__).resolve().parents[2]
        return subprocess.run(
            ["git", "ls-tree", "-r", "--name-only", PINNED],
            capture_output=True, text=True, check=True, cwd=str(repo_root)).stdout.splitlines()

    def test_source_tree_complete(self):
        tree = self._full_tree()
        ok, reason = gate.verify_source_tree_complete(tree, gate.PINNED_SOURCE_TREE_SHA256)
        self.assertTrue(ok, reason)

    def test_source_tree_omission_rejected(self):
        # Omit ONE file (e.g. the out-of-portal openapi.json) -> the full-tree
        # hash no longer matches -> refused (a curated list would miss this).
        tree = [p for p in self._full_tree() if p != "docs/architecture/p8c/openapi.json"]
        ok, reason = gate.verify_source_tree_complete(tree, gate.PINNED_SOURCE_TREE_SHA256)
        self.assertFalse(ok)
        self.assertIn("complete pinned tree", reason)

    def test_source_tree_extra_file_rejected(self):
        tree = self._full_tree() + ["portal/tools/forgejo_lock_gate.py"]
        ok, reason = gate.verify_source_tree_complete(tree, gate.PINNED_SOURCE_TREE_SHA256)
        self.assertFalse(ok)
        self.assertIn("complete pinned tree", reason)

    def test_full_tree_enforced_in_inventory(self):
        tree = self._full_tree()
        ok, reason = gate.verify_file_inventory(
            tree, list(gate.REQUIRED_TOOLS_FILES),
            source_pin=PINNED, tools_pin=TOOLS,
            source_tree_sha256=gate.PINNED_SOURCE_TREE_SHA256)
        self.assertTrue(ok, reason)

    def test_full_tree_omission_rejected_in_inventory(self):
        # Omit a file that is NOT in the curated required list (README.md) — the
        # named-list check passes, so the FULL-tree hash check is what catches it.
        tree = [p for p in self._full_tree() if p != "README.md"]
        ok, reason = gate.verify_file_inventory(
            tree, list(gate.REQUIRED_TOOLS_FILES),
            source_pin=PINNED, tools_pin=TOOLS,
            source_tree_sha256=gate.PINNED_SOURCE_TREE_SHA256)
        self.assertFalse(ok)
        self.assertIn("complete pinned tree", reason)

    def test_out_of_portal_inputs_in_required_list(self):
        # The curated list now names the out-of-portal inputs the go tests read
        # (review #58 item 2) — they must all exist in the real source tree.
        tree = self._full_tree()
        for f in ("docs/architecture/p8c/openapi.json",
                  "portal/migrations/migrations.go",
                  "portal/migrations/0001_portal_observations.sql",
                  "portal/manifests/networkpolicy.yaml",
                  "portal/manifests/deployment.yaml",
                  "portal/networkpolicy/testdata/accepted-policy-contract.json"):
            self.assertIn(f, tree, f)


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

    # --- review #58 item 3: Basic vs issued-Bearer are SEPARATE schemes -------

    def test_generic_transport_basic_accepted_uses_basic_for_manifest(self):
        # When /v2/ returns 200 (Basic accepted directly), the manifest fetch MUST
        # keep using Basic — never the raw Basic credential mislabeled as Bearer.
        calls = []

        def fake_urlopen(url, headers=None, timeout=30):
            calls.append((url, headers))
            if url == "https://registry.example/v2/":
                return _FakeResp(b"{}")
            if "/manifests/" in url:
                auth = headers.get("Authorization", "")
                self.assertTrue(auth.startswith("Basic "), auth)
                self.assertNotIn("Bearer", auth)
                return _FakeResp(MANIFEST, DIGEST)
            raise AssertionError("unexpected url: " + url)

        with mock.patch.dict("os.environ", {"REGISTRY_USERNAME": "u", "REGISTRY_TOKEN": "t"}):
            body, dcd = gate._generic_oci_transport(REGISTRY, "a/otus-diplom-portal", DIGEST, urlopen=fake_urlopen)
        self.assertEqual(body, MANIFEST)
        self.assertEqual(dcd, DIGEST)

    def test_generic_transport_bearer_never_sends_basic_as_bearer(self):
        # The manifest fetch after a bearer exchange must use the ISSUED token as
        # Bearer, never the Basic base64 credential.
        basic_cred = base64.b64encode(b"u:t").decode()
        calls = []

        def fake_urlopen(url, headers=None, timeout=30):
            calls.append((url, headers))
            if url == "https://registry.example/v2/":
                raise urllib.error.HTTPError(
                    url, 401, "Unauthorized",
                    {"WWW-Authenticate": 'Bearer realm="https://registry.example/token",service="x"'},
                    None)
            if url.startswith("https://registry.example/token"):
                return _FakeResp(b'{"token":"issued-token"}')
            if "/manifests/" in url:
                auth = headers.get("Authorization", "")
                self.assertEqual(auth, "Bearer issued-token")
                self.assertNotIn(basic_cred, auth)
                return _FakeResp(MANIFEST, DIGEST)
            raise AssertionError("unexpected url: " + url)

        with mock.patch.dict("os.environ", {"REGISTRY_USERNAME": "u", "REGISTRY_TOKEN": "t"}):
            body, dcd = gate._generic_oci_transport(REGISTRY, "a/otus-diplom-portal", DIGEST, urlopen=fake_urlopen)
        self.assertEqual(body, MANIFEST)
        self.assertEqual(dcd, DIGEST)

    def test_generic_transport_missing_bearer_token_rejected(self):
        # Token endpoint returns no token -> the manifest fetch must NOT fall back
        # to the Basic credential as a Bearer token.
        def fake_urlopen(url, headers=None, timeout=30):
            if url == "https://registry.example/v2/":
                raise urllib.error.HTTPError(
                    url, 401, "Unauthorized",
                    {"WWW-Authenticate": 'Bearer realm="https://registry.example/token",service="x"'},
                    None)
            if url.startswith("https://registry.example/token"):
                return _FakeResp(b'{}')
            raise AssertionError("unexpected url: " + url)

        with mock.patch.dict("os.environ", {"REGISTRY_USERNAME": "u", "REGISTRY_TOKEN": "t"}):
            with self.assertRaises(ValueError) as cm:
                gate._generic_oci_transport(REGISTRY, "a/otus-diplom-portal", DIGEST, urlopen=fake_urlopen)
        self.assertIn("no bearer token", str(cm.exception))


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


DEST_LOCK = ('images:\n  - component: otus-diplom-portal\n    image: %s\n'
    '    digest: "NOT_VERIFIED"\n    verified: false\n') % IMAGE


class TestApplyLockPair(unittest.TestCase):
    def test_refuses_images_lock_outside_tools_checkout(self):
        from pathlib import Path
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            lock = Path(td) / "images.lock"
            original = DEST_LOCK.encode()
            lock.write_bytes(original)
            with self.assertRaises(RuntimeError):
                gate.apply_lock_pair(lock, IMAGE, DIGEST)
            self.assertEqual(lock.read_bytes(), original)

    def test_writes_pair_preserving_other_sections(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as td:
            lock = Path(td) / "images.lock"
            lock.write_text(DEST_LOCK)
            gate.apply_lock_pair(lock, IMAGE, DIGEST, tools_root=td)
            text = lock.read_text()
            self.assertIn('image: %s' % IMAGE, text)
            self.assertIn('digest: "%s"' % DIGEST, text)
            self.assertNotIn('digest: "NOT_VERIFIED"', text)
            self.assertEqual(text, DEST_LOCK.replace('"NOT_VERIFIED"', '"%s"' % DIGEST).replace('verified: false', 'verified: true'))

    def test_rejects_foreign_image_not_rewritten(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as td:
            lock = Path(td) / "images.lock"
            lock.write_text(DEST_LOCK.replace(IMAGE, "ghcr.io/other/image"))
            before = lock.read_text()
            with self.assertRaises(RuntimeError) as cm:
                gate.apply_lock_pair(lock, IMAGE, DIGEST, tools_root=td)
            self.assertIn("pair mismatch", str(cm.exception))
            self.assertEqual(lock.read_text(), before)  # foreign image NOT rewritten

    def test_rejects_host_only_mismatch(self):
        # Passing the bare host (not the full image) must not match the full
        # image name stored in the lock.
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as td:
            lock = Path(td) / "images.lock"
            lock.write_text(DEST_LOCK)
            with self.assertRaises(RuntimeError) as cm:
                gate.apply_lock_pair(lock, REGISTRY, DIGEST, tools_root=td)  # bare host
            self.assertIn("pair mismatch", str(cm.exception))

    def test_rejects_already_set_digest(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as td:
            lock = Path(td) / "images.lock"
            lock.write_text(DEST_LOCK.replace("NOT_VERIFIED", 'sha256:' + 'd' * 64))
            with self.assertRaises(RuntimeError) as cm:
                gate.apply_lock_pair(lock, IMAGE, DIGEST, tools_root=td)
            self.assertIn("already set", str(cm.exception))

    # --- review #58 item 5: byte-level immutability + lock-image pre-agreement --

    def test_apply_changes_only_the_digest_line(self):
        # ALL bytes outside the changed digest line must be preserved — not just
        # the section markers. Verify the exact per-line diff is ONLY the digest.
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as td:
            lock = Path(td) / "images.lock"
            lock.write_text(DEST_LOCK)
            gate.apply_lock_pair(lock, IMAGE, DIGEST, tools_root=td)
            before = DEST_LOCK.split("\n")
            after = lock.read_text().split("\n")
            self.assertEqual(len(before), len(after))
            diffs = [i for i in range(len(before)) if before[i] != after[i]]
            self.assertEqual(len(diffs), 2, "expected exactly one changed line, got %r" % diffs)
            self.assertIn("digest:", before[diffs[0]])
            self.assertIn(DIGEST, after[diffs[0]])

    # --- review #61 item 2: byte-level line-ending preservation --------------

    def test_apply_preserves_crlf_line_endings(self):
        # The review's exact failure: read_text() normalized CRLF -> LF so a CRLF
        # lock came out with all 47 line endings rewritten. Now the raw bytes are
        # preserved — every CRLF survives, and ONLY the digest line changes.
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as td:
            lock = Path(td) / "images.lock"
            crlf = DEST_LOCK.replace("\n", "\r\n")
            lock.write_bytes(crlf.encode())
            gate.apply_lock_pair(lock, IMAGE, DIGEST, tools_root=td)
            before = crlf.encode().splitlines(keepends=True)
            after = lock.read_bytes().splitlines(keepends=True)
            self.assertEqual(len(before), len(after))
            diffs = [i for i in range(len(before)) if before[i] != after[i]]
            self.assertEqual(len(diffs), 2, "expected 1 changed line, got %r" % diffs)
            self.assertIn(b"digest:", before[diffs[0]])
            self.assertIn(DIGEST.encode(), after[diffs[0]])
            # CRLF terminators survive byte-for-byte (the review saw 47 -> 0).
            self.assertEqual(sum(x.endswith(b"\r\n") for x in after), sum(x.endswith(b"\r\n") for x in before))
            self.assertGreater(sum(x.endswith(b"\r\n") for x in after), 0)
            self.assertEqual(sum(x.endswith(b"\n") for x in before), sum(x.endswith(b"\n") for x in after))

    def test_apply_preserves_mixed_line_endings(self):
        # Some lines CRLF, some LF (digest line stays LF): only the digest line's
        # CONTENT changes; every line keeps its own original terminator.
        import tempfile
        from pathlib import Path
        lines = DEST_LOCK.rstrip("\n").split("\n")
        mixed = []
        for i, ln in enumerate(lines):
            ending = "\r\n" if i in (0, 2) else "\n"  # digest line (11) stays LF
            mixed.append(ln + ending)
        raw = "".join(mixed)
        with tempfile.TemporaryDirectory() as td:
            lock = Path(td) / "images.lock"
            lock.write_bytes(raw.encode())
            gate.apply_lock_pair(lock, IMAGE, DIGEST, tools_root=td)
            before = raw.encode().splitlines(keepends=True)
            after = lock.read_bytes().splitlines(keepends=True)
            self.assertEqual(len(before), len(after))
            diffs = [i for i in range(len(before)) if before[i] != after[i]]
            self.assertEqual(len(diffs), 2, diffs)
            self.assertIn(b"digest:", before[diffs[0]])
            # the digest line's OWN terminator is unchanged (still LF, not CRLF)
            self.assertTrue(after[diffs[0]].endswith(b"\n"))
            self.assertFalse(after[diffs[0]].endswith(b"\r\n"))
            # CRLF lines keep CRLF
            self.assertEqual(sum(x.endswith(b"\r\n") for x in after), sum(x.endswith(b"\r\n") for x in before))

    def test_apply_preserves_absent_trailing_newline(self):
        # A lock with NO trailing newline must keep the final line unterminated;
        # only the digest line changes.
        import tempfile
        from pathlib import Path
        body = DEST_LOCK.rstrip("\n")
        with tempfile.TemporaryDirectory() as td:
            lock = Path(td) / "images.lock"
            lock.write_bytes(body.encode())
            gate.apply_lock_pair(lock, IMAGE, DIGEST, tools_root=td)
            after = lock.read_bytes()
            self.assertFalse(after.endswith(b"\n"), "trailing newline must stay absent")
            self.assertFalse(after.endswith(b"\r\n"))
            before = body.encode().splitlines(keepends=True)
            after_lines = after.splitlines(keepends=True)
            self.assertEqual(len(before), len(after_lines))
            diffs = [i for i in range(len(before)) if before[i] != after_lines[i]]
            self.assertEqual(len(diffs), 2, diffs)
            self.assertIn(b"digest:", before[diffs[0]])
            self.assertIn(DIGEST.encode(), after_lines[diffs[0]])

    def test_ambiguous_or_wrong_destination_is_unchanged(self):
        from pathlib import Path
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            for name, body in (("versions.lock", DEST_LOCK),
                               ("images.lock", DEST_LOCK + DEST_LOCK),
                               ("images.lock", DEST_LOCK + DEST_LOCK.split("\n", 1)[1]),
                               ("images.lock", DEST_LOCK + "    digest: NOT_VERIFIED\n"),
                               ("images.lock", DEST_LOCK.replace("verified: false", "verified: true"))):
                with self.subTest(name=name, body=body):
                    lock = Path(td) / name
                    lock.write_text(body)
                    with self.assertRaises(RuntimeError):
                        gate.apply_lock_pair(lock, IMAGE, DIGEST, tools_root=td)
                    self.assertEqual(lock.read_text(), body)


    # --- review #76: root binding (outside / nested / symlink substitution) ---

    def test_refuses_nested_images_lock(self):
        # A nested same-named file (tools/sub/images.lock) is NOT the checkout
        # root lock and must be refused without writing.
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            nested = root / "sub" / "images.lock"
            nested.parent.mkdir(parents=True)
            nested.write_text(DEST_LOCK)
            with self.assertRaises(RuntimeError) as cm:
                gate.apply_lock_pair(nested, IMAGE, DIGEST, tools_root=root)
            self.assertIn("not the trusted tools checkout root", str(cm.exception))
            self.assertEqual(nested.read_text(), DEST_LOCK)  # untouched

    def test_refuses_symlink_lock_file(self):
        # A symlink at the root name that points elsewhere is a substitution and
        # must be refused without writing (even if it resolves inside the root).
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            real = root / "real-images.lock"
            real.write_text(DEST_LOCK)
            link = root / "images.lock"
            link.symlink_to(real.name)
            with self.assertRaises(RuntimeError) as cm:
                gate.apply_lock_pair(link, IMAGE, DIGEST, tools_root=root)
            self.assertIn("symlink", str(cm.exception))
            self.assertEqual(real.read_text(), DEST_LOCK)  # target untouched

    def test_refuses_symlink_parent_directory(self):
        # A symlinked PARENT directory is a path substitution: writing through
        # it lands outside the trusted checkout. Refuse without writing.
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            outside = td / "outside"
            outside.mkdir()
            real_lock = outside / "images.lock"
            real_lock.write_text(DEST_LOCK)
            root = td / "root"
            root.mkdir()
            (root / "tools").symlink_to(outside)
            link_path = root / "tools" / "images.lock"
            with self.assertRaises(RuntimeError) as cm:
                gate.apply_lock_pair(link_path, IMAGE, DIGEST, tools_root=root)
            self.assertIn("symlink", str(cm.exception))
            self.assertEqual(real_lock.read_text(), DEST_LOCK)  # untouched

    # --- review #79: the REFERENCE path (root/images.lock) must also be checked ---

    def test_refuses_symlinked_reference_lock_file(self):
        # The REFERENCE <root>/images.lock is itself a symlink; the INPUT path is
        # the symlink's real target (symlink-free). The OLD `.resolve()` equality
        # would resolve both to the target and let the write land on it even though
        # the reference is not an ordinary root file. Refuse, bytes unchanged.
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            real = root / "real-images.lock"
            real.write_text(DEST_LOCK)
            (root / "images.lock").symlink_to(real.name)
            with self.assertRaises(RuntimeError) as cm:
                gate.apply_lock_pair(real, IMAGE, DIGEST, tools_root=root)
            self.assertIn("symlink", str(cm.exception))
            self.assertEqual(real.read_text(), DEST_LOCK)  # target untouched

    def test_refuses_symlinked_tools_root(self):
        # The TRUSTED root (tools_root) is itself a symlink, so the reference
        # <root>/images.lock resolves through it. Refuse BEFORE any dereference;
        # the real file behind the link stays byte-identical.
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            outside = td / "outside"
            outside.mkdir()
            real_lock = outside / "images.lock"
            real_lock.write_text(DEST_LOCK)
            link = td / "tools-link"
            link.symlink_to(outside)
            with self.assertRaises(RuntimeError) as cm:
                gate.apply_lock_pair(real_lock, IMAGE, DIGEST, tools_root=link)
            self.assertIn("symlink", str(cm.exception))
            self.assertEqual(real_lock.read_text(), DEST_LOCK)  # untouched

    def test_refuses_dotdot_through_symlink_component(self):
        # `abspath` collapses `..` lexically, hiding a symlink in the skipped
        # component (root/escape/../images.lock). The component walk must check
        # `escape` BEFORE `..` is applied. Refuse, bytes unchanged.
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            root = td / "root"
            root.mkdir()
            (root / "images.lock").write_text(DEST_LOCK)
            outside = td / "outside"
            outside.mkdir()
            (outside / "images.lock").write_text(DEST_LOCK)
            (root / "escape").symlink_to(outside)
            tricky = root / "escape" / ".." / "images.lock"
            with self.assertRaises(RuntimeError) as cm:
                gate.apply_lock_pair(tricky, IMAGE, DIGEST, tools_root=root)
            self.assertIn("symlink", str(cm.exception))
            self.assertEqual((root / "images.lock").read_text(), DEST_LOCK)

    def test_lock_image_agreement_matches(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as td:
            lock = Path(td) / "versions.lock"
            lock.write_text(REAL_LOCK)
            ok, reason = gate.verify_lock_image_agreement(lock, IMAGE)
            self.assertTrue(ok, reason)

    def test_lock_image_agreement_path_mismatch(self):
        # Same registry host but a DIFFERENT path (/aiopslab/… vs /dedvmedved-dot/…)
        # must be refused (host substitution alone does not make them equal).
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as td:
            lock = Path(td) / "versions.lock"
            lock.write_text(REAL_LOCK)
            other = REGISTRY + "/dedvmedved-dot/otus-diplom-portal"
            ok, reason = gate.verify_lock_image_agreement(lock, other)
            self.assertFalse(ok)
            self.assertIn("pair mismatch", reason)

    def test_lock_image_agreement_foreign_registry(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as td:
            lock = Path(td) / "versions.lock"
            lock.write_text(REAL_LOCK)
            ok, reason = gate.verify_lock_image_agreement(lock, "evil.example/dedvmedved-dot/otus-diplom-portal")
            self.assertFalse(ok)
            self.assertIn("pair mismatch", reason)


if __name__ == "__main__":
    unittest.main(verbosity=2)
