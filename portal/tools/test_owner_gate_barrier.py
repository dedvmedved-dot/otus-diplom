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

MANIFEST = b'{"schemaVersion":2,"mediaType":"application/vnd.oci.image.manifest.v1+json"}'
DIGEST = "sha256:" + hashlib.sha256(MANIFEST).hexdigest()

# Independent policy bindings (what the workflow CLI passes via flags), plus the
# review #95 OIDC-trust confirmation (true only for the POSITIVE flow).
BINDINGS = {
    "owner": OWNER,
    "trusted_registry": REGISTRY,
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
    if kw.get("builder") is not None:
        pred["builder"]["id"] = kw["builder"]
    if kw.get("build_type") is not None:
        pred["buildType"] = kw["build_type"]
    return {
        "_type": "https://in-toto.io/Statement/v1",
        "subject": [{"name": IMAGE, "digest": {"sha256": DIGEST[len("sha256:"):]}}],
        "predicateType": gate.SLSA,
        "predicate": pred,
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
        "certificate_identity": gate.WORKFLOW_IDENTITY,
        "certificate_issuer": gate.FORGEJO_OIDC_ISSUER,
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

    def test_identity_is_unconfirmed_placeholder(self):
        # review #95: do NOT guess the sub/SAN — it stays an explicit placeholder.
        self.assertEqual(gate.WORKFLOW_IDENTITY, "<FORGEJO_OIDC_IDENTITY_UNCONFIRMED>")

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


if __name__ == "__main__":
    unittest.main(verbosity=2)
