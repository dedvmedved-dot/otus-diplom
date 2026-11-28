#!/usr/bin/env python3
"""Autonomous tests for the review #95 rework (owner-gate race + workflow blob + OIDC).

Offline, synthetic inputs only (no CI, no registry, no real secrets). Proves the
fail-closed branches the review names explicitly:

  * WRONG BLOB         — the executed workflow is OBSERVED as the git blob at the
                         fixed repo/path in the exact dispatch-commit tree and must
                         be a ``blob``; an absent path, a non-blob object, an invalid
                         commit, or a blob != the policy/workflow pin is rejected.
  * DELAYED PUT        — a gate whose PUT arrived after its validity window closed
                         (expired) is rejected; the single-run binding must still be
                         live at read time.
  * FOREIGN RUN        — a gate bound to a different run id is refused (replay).
  * WRONG ISSUER / IDENTITY — the keyless (OIDC) statement is accepted only with the
                         source-confirmed issuer (https://git.aiopslab.online/api/actions)
                         and the owner-confirmed identity, and only when OIDC trust
                         is explicitly confirmed; without confirmation it is BLOCKED.
  * BARRIER / OIDC structure — the workflow template carries an exclusive admission
                         barrier job and release-only enable-openid-connect.

It imports the SAME ``forgejo_lock_gate`` module the workflow drives, so there is
exactly one validation implementation (no parallel re-implementation).
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

import forgejo_lock_gate as gate

PINNED = "4c09d6b4a85e2d021516244988f48b92eade7acf"
TOOLS = "a" * 40
WORKFLOW = "c" * 40
OWNER = "owner-otus@example"
REGISTRY = "registry.example"
IMAGE = REGISTRY + "/aiopslab/otus-diplom-portal"
RUN_ID = "1234567890"
NOW = 2000000000  # 2033-05-18T03:33:20Z
# review #99 item 2: a CONFIRMED (owner-substituted) certificate identity. The
# POSITIVE flow uses this — the placeholder (gate.WORKFLOW_IDENTITY) is a
# REJECTION even at oidc_trust_confirmed=true.
CONFIRMED_IDENTITY = "repo:aiopslab/otus-diplom:ref:refs/heads/main"

MANIFEST = b'{"schemaVersion":2,"mediaType":"application/vnd.oci.image.manifest.v1+json"}'
DIGEST = "sha256:" + hashlib.sha256(MANIFEST).hexdigest()

# Independent policy bindings (what the workflow CLI passes via flags), plus the
# review #95 OIDC-trust confirmation and the review #99 CONFIRMED identity (both
# true only for the POSITIVE flow).
BINDINGS = {
    "owner": OWNER,
    "trusted_registry": REGISTRY,
    "identity": CONFIRMED_IDENTITY,
    "source_sha": PINNED,
    "tools_sha": TOOLS,
    "workflow_sha": WORKFLOW,
    "source_tree_sha256": gate.PINNED_SOURCE_TREE_SHA256,
    "oidc_trust_confirmed": True,
}


def iso(epoch):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(epoch))


def make_gate(**kw):
    g = {
        "owner": OWNER,
        "source_sha": PINNED,
        "tools_sha": TOOLS,
        "workflow_sha": WORKFLOW,
        "repository": "aiopslab/otus-diplom",
        "package": IMAGE,
        "ref": "refs/heads/main",
        "mode": "LIVE",
        "issued_at_utc": iso(NOW - 60),
        "expiry_hours": 1,
        "attempt": 1,
        "run_id": RUN_ID,
    }
    g.update(kw)
    return g


def make_statement(**kw):
    pred = gate.build_predicate(PINNED, WORKFLOW, TOOLS, RUN_ID)
    pred["builder"]["id"] = kw.get("builder", CONFIRMED_IDENTITY)
    if kw.get("build_type") is not None:
        pred["buildType"] = kw["build_type"]
    return {
        "_type": "https://in-toto.io/Statement/v1",
        "subject": [{"name": IMAGE, "digest": {"sha256": DIGEST[len("sha256:"):]}}],
        "predicateType": kw.get("predicate_type", gate.SLSA),
        "predicate": pred,
    }


def make_spdx_statement(**kw):
    """A valid SPDX (spdxjson) attestation statement (review #103 item 2): a
    realistic Syft/cosign SPDX-2.3 document — document identity (SPDX-2.x +
    SPDXRef-DOCUMENT), non-empty name / documentNamespace and a NON-EMPTY
    packages list. The predicateType string alone proves nothing, so the gate
    (check_verified_spdx_statement) and the CUE policy require this shape."""
    return {
        "_type": "https://in-toto.io/Statement/v1",
        "subject": [{"name": kw.get("image", IMAGE),
                     "digest": {"sha256": kw.get("digest", DIGEST)[len("sha256:"):]}}],
        "predicateType": kw.get("predicate_type", gate.SPDX),
        "predicate": {
            "spdxVersion": "SPDX-2.3",
            "dataLicense": "CC0-1.0",
            "SPDXID": "SPDXRef-DOCUMENT",
            "name": "otus-diplom-portal",
            "documentNamespace": "https://anchore.com/syft/otus-diplom-portal-0.1.0",
            "creationInfo": {
                "licenseListVersion": "3.24",
                "creators": ["Organization: Anchore, Inc", "Tool: syft-1.55.0"],
                "created": "2026-01-01T00:00:00Z",
            },
            "packages": [
                {"SPDXID": "SPDXRef-Package-portal", "name": "portal",
                 "versionInfo": "0.1.0", "downloadLocation": "NOASSERTION",
                 "licenseConcluded": "NOASSERTION", "licenseDeclared": "NOASSERTION",
                 "copyrightText": "NOASSERTION"},
            ],
            "documentDescribes": ["SPDXRef-Package-portal"],
        },
    }


def full_source_tree():
    """The COMPLETE pinned source tree (review #58 item 2)."""
    repo_root = Path(__file__).resolve().parents[2]
    return subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", PINNED],
        capture_output=True, text=True, check=True, cwd=str(repo_root)).stdout.splitlines()


def baseline():
    """A fully-valid evidence bundle (correct digests/identity/inventory)."""
    return {
        "owner_gate": make_gate(),
        "source_sha": PINNED,
        "tools_sha": TOOLS,
        "workflow_sha": WORKFLOW,
        "source_inventory": full_source_tree(),
        "tools_inventory": list(gate.REQUIRED_TOOLS_FILES),
        "registry_host": REGISTRY,
        "image_ref": IMAGE,
        "digest": DIGEST,
        "manifest_bytes": MANIFEST,
        "docker_content_digest": DIGEST,
        "verified_attestation": json.dumps(make_statement()) + "\n",
        "spdx_attestation": json.dumps(make_spdx_statement()) + "\n",
        "certificate_identity": CONFIRMED_IDENTITY,
        "certificate_issuer": gate.FORGEJO_OIDC_ISSUER,
        "certificate_audience": "sigstore",
        "actor": OWNER,
        "run_id": RUN_ID,
        "run_attempt": "1",
        "observed_repository": "aiopslab/otus-diplom",
        "observed_ref": "refs/heads/main",
        "observed_workflow_sha": WORKFLOW,
    }


class TestWorkflowBlob(unittest.TestCase):
    """A1: the executed workflow is observed as a git blob at a fixed path in the
    exact dispatch-commit tree; anything else is rejected before side effects."""

    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        d = self._dir.name
        subprocess.run(["git", "init", "-q", d], check=True)
        subprocess.run(["git", "-C", d, "config", "user.email", "t@example"], check=True)
        subprocess.run(["git", "-C", d, "config", "user.name", "t"], check=True)
        wf = Path(d) / ".forgejo" / "workflows" / "p8c-portal-forgejo-release.yml"
        wf.parent.mkdir(parents=True, exist_ok=True)
        wf.write_text("name: p8c-portal-forgejo-release\non: workflow_dispatch\n")
        subprocess.run(["git", "-C", d, "add", "."], check=True)
        subprocess.run(["git", "-C", d, "commit", "-q", "-m", "init"], check=True)
        self.commit = subprocess.run(
            ["git", "-C", d, "rev-parse", "HEAD"],
            capture_output=True, text=True).stdout.strip()

    def tearDown(self):
        self._dir.cleanup()

    def test_valid_blob(self):
        blob, reason = gate.observe_workflow_blob(
            self._dir.name, self.commit, ".forgejo/workflows/p8c-portal-forgejo-release.yml")
        self.assertTrue(gate.valid_sha(blob), reason)
        expected = subprocess.run(
            ["git", "-C", self._dir.name, "rev-parse",
             self.commit + ":.forgejo/workflows/p8c-portal-forgejo-release.yml"],
            capture_output=True, text=True).stdout.strip()
        self.assertEqual(blob, expected)

    def test_absent_path_rejected(self):
        blob, reason = gate.observe_workflow_blob(
            self._dir.name, self.commit, ".forgejo/workflows/does-not-exist.yml")
        self.assertIsNone(blob)
        self.assertIn("absent", reason)

    def test_non_blob_object_rejected(self):
        # ".forgejo" is a TREE object, not a blob — must be rejected.
        blob, reason = gate.observe_workflow_blob(self._dir.name, self.commit, ".forgejo")
        self.assertIsNone(blob)
        self.assertIn("not a blob", reason)

    def test_invalid_commit_rejected(self):
        blob, reason = gate.observe_workflow_blob(
            self._dir.name, "not-a-40-hex-sha", ".forgejo/workflows/p8c-portal-forgejo-release.yml")
        self.assertIsNone(blob)
        self.assertIn("invalid", reason)


class TestOwnerGateRace(unittest.TestCase):
    """The OWNER_GATE race: a wrong blob, a delayed PUT, or a foreign run is refused."""

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

    def test_wrong_blob_rejected(self):
        # The observed workflow blob (computed from the dispatch tree) differs
        # from both the policy pin and the owner-documented workflow_sha.
        ok, reason = self._verify(make_gate(), observed_workflow_sha="b" * 40)
        self.assertFalse(ok)
        self.assertIn("workflow SHA", reason)

    def test_foreign_run_rejected(self):
        # A gate bound to a DIFFERENT run id (a foreign / competing run) is refused.
        ok, reason = self._verify(make_gate(run_id="some-other-run"))
        self.assertFalse(ok)
        self.assertIn("run_id", reason)

    def test_delayed_put_expired_rejected(self):
        # The owner's PUT arrived after the gate's validity window closed (the
        # race where the PUT is delayed past the expiry), so the gate is expired.
        ok, reason = self._verify(make_gate(issued_at_utc=iso(NOW - 7200), expiry_hours=1))
        self.assertFalse(ok)
        self.assertIn("expired", reason)

    def test_delayed_put_future_rejected(self):
        # A gate whose issued_at is still in the future cannot have been a valid
        # delayed PUT — it must be already elapsed at read time.
        ok, reason = self._verify(make_gate(issued_at_utc=iso(NOW + 600)))
        self.assertFalse(ok)
        self.assertIn("future", reason)


class TestOIDCTrust(unittest.TestCase):
    """B: release-only keyless OIDC with source-confirmed issuer and explicit trust."""

    def test_issuer_is_source_confirmed(self):
        self.assertEqual(gate.FORGEJO_OIDC_ISSUER, "https://git.aiopslab.online/api/actions")

    def test_identity_is_pinned_literal_san(self):
        # Owner decision (#162 comment 12512): the SAN is pinned LITERALLY to
        # repo:aiopslab/otus-diplom:ref:refs/heads/main (no placeholder, no regex,
        # no diagnostic sub).
        self.assertEqual(gate.WORKFLOW_IDENTITY, "repo:aiopslab/otus-diplom:ref:refs/heads/main")

    def test_audience_is_sigstore(self):
        # Owner decision (#162 comment 12512): the OIDC token audience is the
        # LITERAL sigstore.
        self.assertEqual(gate.OIDC_AUDIENCE, "sigstore")

    def test_trust_not_confirmed_blocks(self):
        ev = baseline()
        allowed, reason = gate.decide_lock_update(
            ev, dict(BINDINGS, oidc_trust_confirmed=False), now=NOW)
        self.assertFalse(allowed)
        self.assertIn("OIDC trust not confirmed", reason)

    def test_wrong_issuer_rejected(self):
        ev = baseline()
        ev["certificate_issuer"] = "https://evil.example"
        allowed, reason = gate.decide_lock_update(ev, BINDINGS, now=NOW)
        self.assertFalse(allowed)
        self.assertIn("issuer", reason)

    def test_wrong_identity_rejected(self):
        ev = baseline()
        ev["certificate_identity"] = "repo:evil/other:ref:refs/heads/main"
        allowed, reason = gate.decide_lock_update(ev, BINDINGS, now=NOW)
        self.assertFalse(allowed)
        self.assertIn("identity", reason)

    def test_positive_allowed_with_confirmed_trust(self):
        ev = baseline()
        allowed, reason = gate.decide_lock_update(ev, BINDINGS, now=NOW)
        self.assertTrue(allowed, reason)

    def test_foreign_binding_identity_rejected_even_with_confirmed_trust(self):
        # Owner decision (#162): oidc_trust_confirmed=true with a FOREIGN
        # (non-literal) SAN must NOT reach push/sign. The expected binding is
        # changed to a foreign identity — rejected by EXACT equality (no regex).
        ev = baseline()
        foreign = "repo:aiopslab/otus-diplom:ref:refs/heads/engineer/139-oidc-enable-openid"
        allowed, reason = gate.decide_lock_update(
            ev, dict(BINDINGS, identity=foreign), now=NOW)
        self.assertFalse(allowed)
        self.assertIn("identity not confirmed", reason)

    def test_evidence_foreign_identity_rejected(self):
        # The binding is the literal SAN but the evidence carries a FOREIGN
        # (near-miss, diagnostic-sub) identity — the diagnostic sub must NOT be
        # accepted into the release policy (owner decision #162).
        ev = baseline()
        ev["certificate_identity"] = "repo:aiopslab/otus-diplom:ref:refs/heads/engineer/139-oidc-enable-openid"
        allowed, reason = gate.decide_lock_update(ev, BINDINGS, now=NOW)
        self.assertFalse(allowed)
        self.assertIn("identity not confirmed", reason)

    def test_wrong_audience_rejected(self):
        # Owner decision (#162): a non-sigstore token audience is refused
        # fail-closed — no public-sigstore fallback.
        ev = baseline()
        ev["certificate_audience"] = "https://git.aiopslab.online/api/actions"
        allowed, reason = gate.decide_lock_update(ev, BINDINGS, now=NOW)
        self.assertFalse(allowed)
        self.assertIn("audience", reason)


class TestSpdxAttestation(unittest.TestCase):
    """review #103 item 2: the SPDX (spdxjson) attestation must carry a SIGNED
    NON-EMPTY SPDX document of the expected shape — not just a predicateType and
    a subject list. Independent negative fixtures for missing / empty / foreign
    documents, alongside the positive Syft/cosign shape."""

    def _verify(self, spdx_stmt):
        ev = baseline()
        ev["spdx_attestation"] = json.dumps(spdx_stmt) + "\n"
        return gate.decide_lock_update(ev, BINDINGS, now=NOW)

    def test_valid_spdx_allowed(self):
        allowed, reason = self._verify(make_spdx_statement())
        self.assertTrue(allowed, reason)

    def test_spdx_wrong_predicate_type_rejected(self):
        allowed, reason = self._verify(make_spdx_statement(predicate_type=gate.SLSA))
        self.assertFalse(allowed)
        self.assertIn("SPDX", reason)

    def test_spdx_wrong_subject_digest_rejected(self):
        allowed, reason = self._verify(
            make_spdx_statement(digest="sha256:" + "b" * 64))
        self.assertFalse(allowed)
        self.assertIn("subject", reason)

    def test_spdx_missing_subject_rejected(self):
        stmt = make_spdx_statement()
        stmt["subject"] = []
        allowed, reason = self._verify(stmt)
        self.assertFalse(allowed)
        self.assertIn("subject", reason)

    def test_spdx_missing_attestation_rejected(self):
        ev = baseline()
        ev.pop("spdx_attestation")
        allowed, reason = gate.decide_lock_update(ev, BINDINGS, now=NOW)
        self.assertFalse(allowed)
        self.assertIn("SPDX", reason)

    # --- review #103 item 2: predicate CONTENT, not just the shell ------------

    def test_spdx_missing_predicate_rejected(self):
        stmt = make_spdx_statement()
        stmt.pop("predicate")
        allowed, reason = self._verify(stmt)
        self.assertFalse(allowed)
        self.assertIn("predicate", reason)

    def test_spdx_empty_predicate_rejected(self):
        stmt = make_spdx_statement()
        stmt["predicate"] = {}
        allowed, reason = self._verify(stmt)
        self.assertFalse(allowed)
        self.assertIn("predicate", reason)

    def test_spdx_foreign_document_wrong_version_rejected(self):
        stmt = make_spdx_statement()
        stmt["predicate"]["spdxVersion"] = "SPDX-1.0"  # not SPDX-2.x
        allowed, reason = self._verify(stmt)
        self.assertFalse(allowed)
        self.assertIn("spdxVersion", reason)

    def test_spdx_foreign_document_wrong_spdxid_rejected(self):
        stmt = make_spdx_statement()
        stmt["predicate"]["SPDXID"] = "SPDXRef-SomethingElse"
        allowed, reason = self._verify(stmt)
        self.assertFalse(allowed)
        self.assertIn("SPDXID", reason)

    def test_spdx_empty_packages_rejected(self):
        stmt = make_spdx_statement()
        stmt["predicate"]["packages"] = []
        allowed, reason = self._verify(stmt)
        self.assertFalse(allowed)
        self.assertIn("packages", reason)

    def test_spdx_missing_document_namespace_rejected(self):
        stmt = make_spdx_statement()
        stmt["predicate"].pop("documentNamespace")
        allowed, reason = self._verify(stmt)
        self.assertFalse(allowed)
        self.assertIn("documentNamespace", reason)


class TestGateChangedBetweenJobs(unittest.TestCase):
    """review #99 item 2: the release re-checks the gate against the POLICY pin +
    THIS job's observed blob; a gate that changed between preflight and release is
    refused BEFORE build/push."""

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

    def test_valid_gate_accepted(self):
        ok, reason = self._verify(make_gate())
        self.assertTrue(ok, reason)

    def test_gate_workflow_sha_changed_between_jobs_rejected(self):
        # The OWNER_GATE secret was swapped between preflight and release: the gate
        # now documents a DIFFERENT workflow_sha. Re-verification must refuse it
        # even though the observed blob (WORKFLOW) is unchanged.
        ok, reason = self._verify(make_gate(workflow_sha="d" * 40))
        self.assertFalse(ok)
        self.assertIn("workflow_sha", reason)

    def test_gate_source_sha_changed_between_jobs_rejected(self):
        ok, reason = self._verify(make_gate(source_sha="e" * 40))
        self.assertFalse(ok)
        self.assertIn("source_sha", reason)


class TestToolsPin(unittest.TestCase):
    """review #99 item 3 + review #103 item 3: the EXACT pinned tools checkout
    must implement every gate mode the workflow drives AND carry/load both CUE
    policies — a stale tools pin (predating workflow-blob) or one missing a
    policy is refused fail-closed."""

    def _tools_dir(self, gate_text, *, policies=None):
        import tempfile
        d = tempfile.mkdtemp()
        p = Path(d) / "portal" / "tools"
        p.mkdir(parents=True)
        (p / "forgejo_lock_gate.py").write_text(gate_text)
        # Copy the REAL CUE policies into the checkout so a complete tools dir
        # loads them from the SAME checkout (review #103 item 3).
        real_tools = Path(gate.__file__).parent
        names = policies if policies is not None else ("cosign-slsa-policy.cue",
                                                       "cosign-spdx-policy.cue")
        for name in names:
            (p / name).write_text((real_tools / name).read_text())
        return d

    def test_complete_gate_accepted(self):
        d = self._tools_dir(Path(gate.__file__).read_text())
        ok, reason = gate.verify_tools_pin(d)
        self.assertTrue(ok, reason)

    def test_stale_gate_missing_workflow_blob_rejected(self):
        # A gate predating workflow-blob (like the stale PINNED_TOOLS_SHA 32a38ea)
        # is missing the workflow-blob mode and must be refused.
        stale = Path(gate.__file__).read_text().replace(
            'if mode == "workflow-blob":', 'if mode == "workflow-blob-REMOVED":')
        d = self._tools_dir(stale)
        ok, reason = gate.verify_tools_pin(d)
        self.assertFalse(ok)
        self.assertIn("workflow-blob", reason)

    def test_missing_gate_file_rejected(self):
        import tempfile
        d = tempfile.mkdtemp()
        ok, reason = gate.verify_tools_pin(d)
        self.assertFalse(ok)
        self.assertIn("missing", reason)

    # --- review #103 item 3: the CUE policies must be carried by the checkout ---

    def test_gate_with_commands_but_missing_spdx_policy_rejected(self):
        # The gate implements every required mode but the SPDX CUE policy is
        # absent — the workflow opens it only after push/sign, so it must be
        # caught HERE (before any external write), not at verify time.
        d = self._tools_dir(Path(gate.__file__).read_text(),
                            policies=("cosign-slsa-policy.cue",))
        ok, reason = gate.verify_tools_pin(d)
        self.assertFalse(ok)
        self.assertIn("CUE policy missing", reason)

    def test_gate_with_commands_but_missing_slsa_policy_rejected(self):
        d = self._tools_dir(Path(gate.__file__).read_text(),
                            policies=("cosign-spdx-policy.cue",))
        ok, reason = gate.verify_tools_pin(d)
        self.assertFalse(ok)
        self.assertIn("CUE policy missing", reason)

    def test_gate_with_empty_cue_policy_rejected(self):
        d = self._tools_dir(Path(gate.__file__).read_text())
        p = Path(d) / "portal" / "tools" / "cosign-spdx-policy.cue"
        p.write_text("")
        ok, reason = gate.verify_tools_pin(d)
        self.assertFalse(ok)
        self.assertIn("empty", reason)

    def test_gate_with_swapped_cue_policies_rejected(self):
        # review #106 item 3: presence + a bare `predicateType:` substring cannot
        # tell the two policies apart — an EXACT copy of the SLSA policy placed at
        # the SPDX path used to pass (tools_pin=true). Each policy must match its
        # own role; the SPDX path carrying the SLSA policy must be refused.
        d = self._tools_dir(Path(gate.__file__).read_text())
        real_tools = Path(gate.__file__).parent
        p = Path(d) / "portal" / "tools" / "cosign-spdx-policy.cue"
        p.write_text((real_tools / "cosign-slsa-policy.cue").read_text())
        ok, reason = gate.verify_tools_pin(d)
        self.assertFalse(ok)
        self.assertIn("swapped or corrupted", reason)

    def test_gate_with_corrupted_cue_policy_rejected(self):
        # review #106 item 3: a corrupted (truncated) CUE policy is still readable
        # and non-empty, but its bytes no longer match the pre-reviewed reference —
        # it must be refused fail-closed before any external write.
        d = self._tools_dir(Path(gate.__file__).read_text())
        p = Path(d) / "portal" / "tools" / "cosign-spdx-policy.cue"
        raw = p.read_bytes()
        p.write_bytes(raw[: len(raw) // 2])
        ok, reason = gate.verify_tools_pin(d)
        self.assertFalse(ok)
        self.assertIn("swapped or corrupted", reason)


class TestWorkflowStructure(unittest.TestCase):
    """The workflow template encodes the barrier + release-only OIDC + fixed URL."""

    def _doc(self):
        import yaml
        template = Path(__file__).parent / "p8c-portal-forgejo-release.yml.template"
        return yaml.safe_load(template.read_text())

    def test_admission_barrier_job_runs_first(self):
        doc = self._doc()
        jobs = doc["jobs"]
        self.assertIn("admission", jobs)
        self.assertEqual(jobs["admission"]["runs-on"], "otus-diplom-admission")
        self.assertEqual(jobs["test"]["needs"], "admission")

    def test_release_only_oidc(self):
        doc = self._doc()
        jobs = doc["jobs"]
        self.assertTrue(jobs["release"].get("enable-openid-connect"))
        # preflight must NOT enable OIDC / carry id-token (unprivileged gate).
        self.assertNotIn("enable-openid-connect", jobs["preflight"])
        self.assertIsNone(jobs["preflight"].get("permissions", {}).get("id-token"))

    def test_fail_closed_inputs_present(self):
        doc = self._doc()
        # PyYAML 1.1 coerces the bare `on` trigger key to boolean True (see
        # check_forgejo_workflow_syntax.py); accept either spelling.
        trigger = doc.get("on") or doc.get(True)
        inputs = trigger["workflow_dispatch"]["inputs"]
        self.assertIn("admission_confirmed", inputs)
        self.assertIn("oidc_trust_confirmed", inputs)
        self.assertEqual(inputs["admission_confirmed"]["default"], False)
        self.assertEqual(inputs["oidc_trust_confirmed"]["default"], False)

    def test_cosign_version_has_no_double_v(self):
        doc = self._doc()
        self.assertEqual(doc["env"]["COSIGN_VERSION"], "3.1.3")

    def test_tool_versions_have_no_double_v(self):
        # review #99 item 3: rootlesskit/syft/trivy VERSION vars hold the bare tag
        # (buildkit keeps the "v" because its asset name includes it).
        doc = self._doc()
        self.assertEqual(doc["env"]["ROOTLESSKIT_VERSION"], "2.3.1")
        self.assertEqual(doc["env"]["SYFT_VERSION"], "1.55.0")
        self.assertEqual(doc["env"]["TRIVY_VERSION"], "0.76.0")

    def test_verify_attestation_uses_policy_not_annotations(self):
        # review #99 item 1: cosign verify-attestation has NO -a flag; the source
        # binding is enforced via --policy (CUE). The image-signature verify/sign
        # keep the bare -a ref=… (supported there).
        text = (Path(__file__).parent / "p8c-portal-forgejo-release.yml.template").read_text()
        self.assertIn("--policy tools/portal/tools/cosign-slsa-policy.cue", text)
        self.assertIn("--policy tools/portal/tools/cosign-spdx-policy.cue", text)
        self.assertNotIn('-a ref="${{', text)

    def test_release_rechecks_owner_gate(self):
        # review #99 item 2: the release job re-verifies the gate (policy pin +
        # observed blob) BEFORE build/push.
        doc = self._doc()
        steps = [s.get("name", "") for s in doc["jobs"]["release"]["steps"]]
        self.assertIn("Re-verify owner gate in release (before build/push/sign)", steps)

    def test_release_identity_literal_san_pinned(self):
        # Owner decision (#162 comment 12512): the release job pins the LITERAL
        # SAN and refuses any other identity/audience before push/sign.
        text = (Path(__file__).parent / "p8c-portal-forgejo-release.yml.template").read_text()
        self.assertIn('WORKFLOW_IDENTITY: "repo:aiopslab/otus-diplom:ref:refs/heads/main"', text)
        self.assertIn('OIDC_AUDIENCE: "sigstore"', text)
        self.assertIn('"${{ env.WORKFLOW_IDENTITY }}" == "repo:aiopslab/otus-diplom:ref:refs/heads/main"', text)
        self.assertIn('"${{ env.OIDC_AUDIENCE }}" == "sigstore"', text)

    def test_tools_pin_check_step_present(self):
        # review #99 item 3: the exact tools-pin check runs in every job.
        doc = self._doc()
        for job in ("test", "preflight", "release"):
            steps = [s.get("name", "") for s in doc["jobs"][job]["steps"]]
            self.assertIn("Verify pinned tools implement every gate mode (exact tools pin)", steps)


if __name__ == "__main__":
    unittest.main(verbosity=2)
