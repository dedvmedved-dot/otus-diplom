#!/usr/bin/env python3
"""Offline INTEGRATION harness for the P8C Forgejo admission chain.

Proves, with synthetic inputs only (no CI, no build/push/sign/attest, no real
secrets, no stand access, no change to the real locks), that the FULL chain

    owner gate -> trusted registry -> verified signed statement -> lock pair

behaves exactly as review #52 (and the review #55 tightenings) require:

  * POSITIVE: a fully-valid evidence bundle is ALLOWED and the CLI writes the
    (full image, digest) pair into a SCRATCH lock only; the real lock is untouched.
  * BLOCKING DISCREPANCY 1 (owner gate): missing / expired / foreign admission /
    unconfirmed actor / run replay => NOT allowed, scratch lock byte-identical.
  * BLOCKING DISCREPANCY 2 (source/tools): tools smuggled into the source tree,
    source substituted with a new HEAD => NOT allowed.
  * BLOCKING DISCREPANCY 3 (registry): foreign destination refused BEFORE any
    network request (mock transport never invoked); manifest bytes / image_ref
    mismatch => NOT allowed.
  * BLOCKING DISCREPANCY 4 (verified statement): no verified attestation,
    unbound subject, predicate substitution, another run/registry => NOT allowed.

Every negative case mutates exactly ONE field of the valid baseline, so each
case is guaranteed to reach its named check (no silent pass on an earlier gate).
"""
import hashlib
import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

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

# Independent policy bindings (what the workflow CLI passes via --owner /
# --trusted-registry / --pinned-source / --pinned-tools / --workflow-sha /
# --source-tree-sha256).
BINDINGS = {
    "owner": OWNER,
    "trusted_registry": REGISTRY,
    "source_sha": PINNED,
    "tools_sha": TOOLS,
    "workflow_sha": WORKFLOW,
    "source_tree_sha256": gate.PINNED_SOURCE_TREE_SHA256,
}

# A real-format lock: `image.registry` holds the FULL image name (review #55
# item 5), surrounded by sections that must survive the write untouched.
LOCK_TEMPLATE = (
    'baseline: "P8C-R1"\n'
    'verification_status: NOT_VERIFIED\n'
    '\n'
    'application:\n'
    '  go: "1.27.3"\n'
    '\n'
    'image:\n'
    '  registry: "%s"\n'
    '  digest: "NOT_VERIFIED"   # final digest only after reproducible build (G2)\n'
    '  base: "scratch"\n'
    '  base_digest: "NOT_APPLICABLE_EMPTY_BASE"\n'
    '\n'
    'notes:\n'
    '  - "tool release metadata recorded from source-verification.json."\n'
) % IMAGE


def iso(epoch):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(epoch))


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


def full_source_tree():
    """The COMPLETE pinned source tree (review #58 item 2) — used so the positive
    chain genuinely exercises the full-tree completeness check, not a curated
    subset."""
    import subprocess
    repo_root = Path(__file__).resolve().parents[2]
    return subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", PINNED],
        capture_output=True, text=True, check=True, cwd=str(repo_root)).stdout.splitlines()


def baseline():
    """A fully-valid evidence bundle (correct digests/identity/inventory)."""
    return {
        "owner_gate": {
            "owner": OWNER, "source_sha": PINNED, "tools_sha": TOOLS, "workflow_sha": WORKFLOW,
            "repository": "aiopslab/otus-diplom", "package": IMAGE,
            "ref": "refs/heads/main", "mode": "LIVE",
            "issued_at_utc": iso(NOW - 60), "expiry_hours": 1, "attempt": 1, "run_id": RUN_ID,
        },
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


class TestFullChain(unittest.TestCase):
    def test_positive_allowed(self):
        allowed, reason = gate.decide_lock_update(baseline(), BINDINGS, now=NOW)
        self.assertTrue(allowed, reason)
        self.assertEqual(reason, "all bindings verified")

    # --- Blocking discrepancy 1: owner gate --------------------------------

    def test_owner_gate_missing_not_allowed(self):
        ev = baseline()
        ev["owner_gate"] = None
        allowed, reason = gate.decide_lock_update(ev, BINDINGS, now=NOW)
        self.assertFalse(allowed)
        self.assertIn("owner gate", reason)

    def test_owner_gate_expired_not_allowed(self):
        ev = baseline()
        ev["owner_gate"]["issued_at_utc"] = iso(NOW - 7200)
        ev["owner_gate"]["expiry_hours"] = 1
        allowed, reason = gate.decide_lock_update(ev, BINDINGS, now=NOW)
        self.assertFalse(allowed)
        self.assertIn("expired", reason)

    def test_owner_gate_foreign_not_allowed(self):
        ev = baseline()
        ev["owner_gate"]["owner"] = "intruder@evil.example"
        allowed, reason = gate.decide_lock_update(ev, BINDINGS, now=NOW)
        self.assertFalse(allowed)
        self.assertIn("foreign owner", reason)

    def test_owner_gate_unconfirmed_actor_not_allowed(self):
        ev = baseline()
        ev["actor"] = "intruder@evil.example"  # trusted runtime actor != owner
        allowed, reason = gate.decide_lock_update(ev, BINDINGS, now=NOW)
        self.assertFalse(allowed)
        self.assertIn("actor", reason)

    def test_owner_gate_run_replay_not_allowed(self):
        ev = baseline()
        ev["owner_gate"]["run_id"] = "a-different-run"  # gate bound to another run
        allowed, reason = gate.decide_lock_update(ev, BINDINGS, now=NOW)
        self.assertFalse(allowed)
        self.assertIn("run_id", reason)

    # --- Blocking discrepancy 2: source/tools separation -------------------

    def test_tools_smuggled_into_source_not_allowed(self):
        ev = baseline()
        ev["source_inventory"] = list(gate.REQUIRED_SOURCE_FILES) + [gate.REQUIRED_TOOLS_FILES[0]]
        allowed, reason = gate.decide_lock_update(ev, BINDINGS, now=NOW)
        self.assertFalse(allowed)
        self.assertIn("smuggled", reason)

    def test_source_substituted_new_head_not_allowed(self):
        ev = baseline()
        ev["source_sha"] = "b" * 40  # a NEW head, not the pinned source
        allowed, reason = gate.decide_lock_update(ev, BINDINGS, now=NOW)
        self.assertFalse(allowed)
        self.assertIn("mismatch", reason)

    def test_tools_sha_not_bound_not_allowed(self):
        ev = baseline()
        ev["tools_sha"] = "b" * 40
        allowed, reason = gate.decide_lock_update(ev, BINDINGS, now=NOW)
        self.assertFalse(allowed)
        self.assertIn("tools_sha", reason)

    def test_workflow_sha_not_bound_not_allowed(self):
        ev = baseline()
        ev["workflow_sha"] = "b" * 40
        allowed, reason = gate.decide_lock_update(ev, BINDINGS, now=NOW)
        self.assertFalse(allowed)
        self.assertIn("workflow_sha", reason)

    # --- review #58 item 1/4: observed runtime context (triple check) --------

    def test_observed_repository_mismatch_not_allowed(self):
        ev = baseline()
        ev["observed_repository"] = "evil.example/repo"
        allowed, reason = gate.decide_lock_update(ev, BINDINGS, now=NOW)
        self.assertFalse(allowed)
        self.assertIn("observed repository", reason)

    def test_observed_ref_mismatch_not_allowed(self):
        ev = baseline()
        ev["observed_ref"] = "refs/heads/dev"
        allowed, reason = gate.decide_lock_update(ev, BINDINGS, now=NOW)
        self.assertFalse(allowed)
        self.assertIn("observed ref", reason)

    def test_observed_workflow_sha_mismatch_not_allowed(self):
        ev = baseline()
        ev["observed_workflow_sha"] = "b" * 40
        allowed, reason = gate.decide_lock_update(ev, BINDINGS, now=NOW)
        self.assertFalse(allowed)
        self.assertIn("observed workflow SHA", reason)

    def test_observed_workflow_sha_absent_not_allowed(self):
        ev = baseline()
        del ev["observed_workflow_sha"]
        allowed, reason = gate.decide_lock_update(ev, BINDINGS, now=NOW)
        self.assertFalse(allowed)
        self.assertIn("observed workflow SHA", reason)

    # --- review #58 item 2: full-tree completeness ---------------------------

    def test_full_tree_omission_not_allowed(self):
        # Omit a file NOT in the curated list — only the full-tree hash catches it.
        ev = baseline()
        ev["source_inventory"] = [p for p in ev["source_inventory"] if p != "README.md"]
        allowed, reason = gate.decide_lock_update(ev, BINDINGS, now=NOW)
        self.assertFalse(allowed)
        self.assertIn("complete pinned tree", reason)

    def test_full_tree_extra_file_not_allowed(self):
        ev = baseline()
        # An EXTRA file that is neither a required source nor a tools file — only
        # the full-tree hash catches it (the named-list + smuggling checks pass).
        ev["source_inventory"] = ev["source_inventory"] + ["extra/evil-injected.txt"]
        allowed, reason = gate.decide_lock_update(ev, BINDINGS, now=NOW)
        self.assertFalse(allowed)
        self.assertIn("complete pinned tree", reason)

    # --- Blocking discrepancy 3: trusted registry --------------------------

    def test_foreign_registry_not_allowed_before_network(self):
        # The mock transport proves the foreign destination is refused BEFORE
        # any network request (fetch_registry_manifest host gate).
        calls = []

        def transport(host, repo, dg):
            calls.append(host)
            return MANIFEST, DIGEST

        with self.assertRaises(ValueError):
            gate.fetch_registry_manifest(REGISTRY, "evil.example", "x", DIGEST, transport)
        self.assertEqual(calls, [])

    def test_registry_host_mismatch_not_allowed(self):
        ev = baseline()
        ev["registry_host"] = "evil.example"
        allowed, reason = gate.decide_lock_update(ev, BINDINGS, now=NOW)
        self.assertFalse(allowed)
        self.assertIn("trusted registry", reason)

    def test_manifest_bytes_tampered_not_allowed(self):
        ev = baseline()
        ev["manifest_bytes"] = b"tampered-manifest"
        allowed, reason = gate.decide_lock_update(ev, BINDINGS, now=NOW)
        self.assertFalse(allowed)
        self.assertIn("bytes", reason)

    # --- Blocking discrepancy 4: verified signed statement -----------------

    def test_no_verified_attestation_not_allowed(self):
        ev = baseline()
        ev["verified_attestation"] = ""
        allowed, reason = gate.decide_lock_update(ev, BINDINGS, now=NOW)
        self.assertFalse(allowed)
        self.assertIn("no verified attestation", reason)

    def test_unbound_subject_not_allowed(self):
        ev = baseline()
        st = make_statement(digest="sha256:" + "f" * 64)
        ev["verified_attestation"] = json.dumps(st) + "\n"
        allowed, reason = gate.decide_lock_update(ev, BINDINGS, now=NOW)
        self.assertFalse(allowed)
        self.assertIn("subject", reason)

    def test_predicate_substitution_not_allowed(self):
        # A verified statement whose predicate binds a DIFFERENT source/material
        # (predicate swapped out) must not authorize the write.
        ev = baseline()
        st = make_statement(source="b" * 40)
        ev["verified_attestation"] = json.dumps(st) + "\n"
        allowed, reason = gate.decide_lock_update(ev, BINDINGS, now=NOW)
        self.assertFalse(allowed)
        self.assertIn("materials", reason)

    def test_tools_material_swap_not_allowed(self):
        ev = baseline()
        st = make_statement(tools="b" * 40)
        ev["verified_attestation"] = json.dumps(st) + "\n"
        allowed, reason = gate.decide_lock_update(ev, BINDINGS, now=NOW)
        self.assertFalse(allowed)
        self.assertIn("tools SHA", reason)

    def test_another_run_not_allowed(self):
        ev = baseline()
        st = make_statement(run_id="different-run-id")
        ev["verified_attestation"] = json.dumps(st) + "\n"
        allowed, reason = gate.decide_lock_update(ev, BINDINGS, now=NOW)
        self.assertFalse(allowed)
        self.assertIn("run id", reason)

    def test_another_registry_not_allowed(self):
        ev = baseline()
        st = make_statement(image="evil.example/aiopslab/otus-diplom-portal")
        ev["verified_attestation"] = json.dumps(st) + "\n"
        allowed, reason = gate.decide_lock_update(ev, BINDINGS, now=NOW)
        self.assertFalse(allowed)
        self.assertIn("subject", reason)

    def test_certificate_identity_mismatch_not_allowed(self):
        ev = baseline()
        ev["certificate_identity"] = "https://github.com/evil/wf@main"
        allowed, reason = gate.decide_lock_update(ev, BINDINGS, now=NOW)
        self.assertFalse(allowed)
        self.assertIn("certificate identity", reason)

    def test_certificate_issuer_mismatch_not_allowed(self):
        ev = baseline()
        ev["certificate_issuer"] = "https://evil.example"
        allowed, reason = gate.decide_lock_update(ev, BINDINGS, now=NOW)
        self.assertFalse(allowed)
        self.assertIn("certificate issuer", reason)


class TestCliApplyScratchLock(unittest.TestCase):
    """End-to-end CLI: positive writes the (full image, digest) pair into a SCRATCH
    lock; every discrepancy leaves it byte-identical. The REAL portal/versions.lock
    is never touched. Writing additionally requires --apply-lock true."""

    GATE_PY = Path(__file__).parent / "forgejo_lock_gate.py"

    def _run(self, evidence, apply=True, apply_lock=True):
        # The subprocess gates on the REAL clock, so rebase the gate's issued_at
        # to now (offline harness keeps the gate live without a --now bypass).
        ev = dict(evidence)
        ev["owner_gate"] = dict(ev["owner_gate"])
        ev["owner_gate"]["issued_at_utc"] = iso(time.time() - 60)
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            (td / "manifest.bin").write_bytes(ev["manifest_bytes"])
            lock = td / "versions.lock"
            lock.write_text(LOCK_TEMPLATE)
            ev.pop("manifest_bytes", None)
            ev["manifest_file"] = str(td / "manifest.bin")
            # verified_attestation stays inline (it is text)
            ev_path = td / "evidence.json"
            ev_path.write_text(json.dumps(ev))
            cmd = [sys.executable, str(self.GATE_PY), "verify", str(ev_path),
                   "--owner", OWNER, "--trusted-registry", REGISTRY,
                   "--pinned-source", PINNED, "--pinned-tools", TOOLS,
                   "--workflow-sha", WORKFLOW]
            if apply:
                cmd += ["--apply", str(lock)]
                if apply_lock:
                    cmd += ["--apply-lock", "true"]
            r = subprocess.run(cmd, capture_output=True, text=True)
            return r, lock.read_text()

    def test_positive_writes_scratch_lock_pair(self):
        r, text = self._run(baseline())
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('registry: "%s"' % IMAGE, text)
        self.assertIn('digest: "%s"' % DIGEST, text)
        self.assertNotIn('digest: "NOT_VERIFIED"', text)
        # other sections preserved
        self.assertIn('go: "1.27.3"', text)
        self.assertIn('base: "scratch"', text)

    def test_apply_without_apply_lock_authorization_refused(self):
        r, text = self._run(baseline(), apply=True, apply_lock=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(text, LOCK_TEMPLATE)  # byte-identical (no authorization)
        self.assertIn("apply-lock", r.stderr)

    def test_owner_gate_foreign_leaves_lock_untouched(self):
        ev = baseline()
        ev["owner_gate"]["owner"] = "intruder@evil.example"
        r, text = self._run(ev)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(text, LOCK_TEMPLATE)  # byte-identical
        self.assertIn("NOT ALLOWED", r.stderr)

    def test_manifest_tamper_leaves_lock_untouched(self):
        ev = baseline()
        ev["manifest_bytes"] = b"tampered-manifest"
        r, text = self._run(ev)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(text, LOCK_TEMPLATE)
        self.assertIn("NOT ALLOWED", r.stderr)

    def test_no_attestation_leaves_lock_untouched(self):
        ev = baseline()
        ev["verified_attestation"] = ""
        r, text = self._run(ev)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(text, LOCK_TEMPLATE)
        self.assertIn("NOT ALLOWED", r.stderr)

    def test_check_mode_positive_exit_zero_no_write(self):
        r, _ = self._run(baseline(), apply=False)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('"allowed": true', r.stdout)


class TestWorkflowStructuralOrder(unittest.TestCase):
    """The owner gate must run in an UNPRIVILEGED preflight job that has NO release
    credentials, and the release job must depend on it — verified structurally on
    the (inactive) template."""

    def _doc(self):
        import yaml
        template = Path(__file__).parent / "p8c-portal-forgejo-release.yml.template"
        return yaml.safe_load(template.read_text())

    def test_owner_gate_lives_in_unprivileged_preflight(self):
        doc = self._doc()
        jobs = doc["jobs"]
        self.assertIn("preflight", jobs)
        pf = jobs["preflight"]
        perms = pf.get("permissions", {})
        # preflight MUST NOT carry release credentials
        self.assertEqual(perms.get("packages"), None)
        self.assertEqual(perms.get("id-token"), None)
        names = [(s.get("name") or "") for s in pf["steps"] if isinstance(s, dict)]
        self.assertTrue(any(n.startswith("Verify owner gate") for n in names),
                        "owner gate step must live in the preflight job")

    def test_release_job_needs_preflight(self):
        doc = self._doc()
        jobs = doc["jobs"]
        self.assertIn("release", jobs)
        self.assertEqual(jobs["release"]["needs"], "preflight")

    def test_owner_gate_step_uses_env_secret_not_shell_interpolation(self):
        doc = self._doc()
        jobs = doc["jobs"]
        pf_steps = jobs["preflight"]["steps"]
        gate_step = next(s for s in pf_steps if isinstance(s, dict)
                         and (s.get("name") or "").startswith("Verify owner gate"))
        # Gate JSON must arrive via env (secret), never interpolated into `run:`.
        self.assertEqual(gate_step["env"]["OWNER_GATE"], "${{ secrets.OWNER_GATE }}")
        run = gate_step["run"]
        self.assertNotIn("inputs.release_gate", run)
        # review #58 item 1/4: the POLICY-ALLOWED repository/ref (env.POLICY_*) is
        # passed as the expected value; the OBSERVED runtime context
        # (github.repository / github.ref / GITHUB_WORKFLOW_SHA) is passed as the
        # observed value; the owner is confirmed against the trusted runtime actor
        # + run id.
        self.assertIn("--repository \"${{ env.POLICY_REPOSITORY }}\"", run)
        self.assertIn("--ref \"${{ env.POLICY_REF }}\"", run)
        self.assertIn("--observed-repository \"${{ github.repository }}\"", run)
        self.assertIn("--observed-ref \"${{ github.ref }}\"", run)
        self.assertIn("--observed-workflow-sha \"$GITHUB_WORKFLOW_SHA\"", run)
        self.assertIn("--actor \"${{ github.actor }}\"", run)
        self.assertIn("--run-id \"${{ github.run_id }}\"", run)
        self.assertIn("--run-attempt \"${{ github.run_attempt }}\"", run)

    def test_apply_lock_targets_source_tree_real_lock(self):
        doc = self._doc()
        jobs = doc["jobs"]
        apply_step = next(s for s in jobs["release"]["steps"] if isinstance(s, dict)
                          and (s.get("name") or "").startswith("Apply verified digest"))
        self.assertIn("--apply src/portal/versions.lock", apply_step["run"])
        self.assertIn("--apply-lock true", apply_step["run"])
        self.assertEqual(apply_step["if"], "inputs.apply_lock == true")


if __name__ == "__main__":
    unittest.main(verbosity=2)
