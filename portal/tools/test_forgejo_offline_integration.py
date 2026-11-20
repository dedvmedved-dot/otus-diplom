#!/usr/bin/env python3
"""Offline INTEGRATION harness for the P8C Forgejo admission chain.

Proves, with synthetic inputs only (no CI, no build/push/sign/attest, no real
secrets, no stand access, no change to the real locks), that the FULL chain

    owner gate -> trusted registry -> verified signed statement -> lock pair

behaves exactly as review #52 requires:

  * POSITIVE: a fully-valid evidence bundle is ALLOWED and the CLI writes the
    (registry, digest) pair into a SCRATCH lock only; the real lock is untouched.
  * BLOCKING DISCREPANCY 1 (owner gate): missing / expired / foreign admission
    => NOT allowed, scratch lock byte-identical.
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
OWNER = "owner-otus@example"
REGISTRY = "registry.example"
IMAGE = REGISTRY + "/aiopslab/otus-diplom-portal"
RUN_ID = "1234567890"
NOW = 2000000000  # 2033-05-18T03:33:20Z

MANIFEST = b'{"schemaVersion":2,"mediaType":"application/vnd.oci.image.manifest.v1+json"}'
DIGEST = "sha256:" + hashlib.sha256(MANIFEST).hexdigest()

BINDINGS = {"owner": OWNER, "trusted_registry": REGISTRY, "workflow_sha": TOOLS}

LOCK_TEMPLATE = (
    'image:\n'
    '  registry: "%s"\n'
    '  digest: "NOT_VERIFIED"   # final digest only after reproducible build (G2)\n'
    '  base: "scratch"\n'
    '  base_digest: "NOT_APPLICABLE_EMPTY_BASE"\n'
) % REGISTRY


def iso(epoch):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(epoch))


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


def baseline():
    """A fully-valid evidence bundle (correct digests/identity/inventory)."""
    return {
        "owner_gate": {
            "owner": OWNER, "source_sha": PINNED, "workflow_sha": TOOLS,
            "repository": "aiopslab/otus-diplom", "package": IMAGE,
            "ref": "refs/heads/main", "mode": "LIVE",
            "issued_at_utc": iso(NOW - 60), "expiry_hours": 1, "attempt": 1,
        },
        "source_sha": PINNED,
        "pinned_source_sha": PINNED,
        "workflow_sha": TOOLS,
        "pinned_workflow_sha": TOOLS,
        "source_inventory": list(gate.REQUIRED_SOURCE_FILES),
        "tools_inventory": list(gate.REQUIRED_TOOLS_FILES),
        "registry_host": REGISTRY,
        "image_ref": IMAGE,
        "digest": DIGEST,
        "manifest_bytes": MANIFEST,
        "docker_content_digest": DIGEST,
        "verified_attestation": json.dumps(make_statement()) + "\n",
        "certificate_identity": gate.WORKFLOW_IDENTITY,
        "certificate_issuer": gate.FORGEJO_OIDC_ISSUER,
        "run_id": RUN_ID,
        "run_attempt": "1",
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
    """End-to-end CLI: positive writes the (registry, digest) pair into a SCRATCH
    lock; every discrepancy leaves it byte-identical. The REAL portal/versions.lock
    is never touched."""

    GATE_PY = Path(__file__).parent / "forgejo_lock_gate.py"

    def _run(self, evidence, apply=True):
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
                   "--workflow-sha", TOOLS]
            if apply:
                cmd += ["--apply", str(lock)]
            r = subprocess.run(cmd, capture_output=True, text=True)
            return r, lock.read_text()

    def test_positive_writes_scratch_lock_pair(self):
        r, text = self._run(baseline())
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('registry: "%s"' % REGISTRY, text)
        self.assertIn('digest: "%s"' % DIGEST, text)
        self.assertNotIn("NOT_VERIFIED", text)

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
    """The owner gate must be the FIRST release-job check, before the login/build/
    push/sign steps — verified structurally on the (inactive) template."""

    def test_owner_gate_precedes_login_build(self):
        import yaml
        template = Path(__file__).parent / "p8c-portal-forgejo-release.yml.template"
        doc = yaml.safe_load(template.read_text())
        jobs = doc["jobs"]
        self.assertIn("release", jobs)
        names = [s["name"] for s in jobs["release"]["steps"] if isinstance(s, dict) and "name" in s]
        gate_idx = next(i for i, n in enumerate(names) if n.startswith("Verify owner gate"))
        login_idx = next(i for i, n in enumerate(names) if n.startswith("Login to registry"))
        build_idx = next(i for i, n in enumerate(names) if n.startswith("Build OCI image"))
        self.assertLess(gate_idx, login_idx)
        self.assertLess(gate_idx, build_idx)

    def test_owner_gate_input_required(self):
        import yaml
        template = Path(__file__).parent / "p8c-portal-forgejo-release.yml.template"
        doc = yaml.safe_load(template.read_text())
        # PyYAML 1.1 coerces bare `on` to True; read the trigger through either key.
        on = doc.get("on", doc.get(True, {}))
        inputs = on.get("workflow_dispatch", {}).get("inputs", {})
        self.assertTrue(inputs.get("release_gate", {}).get("required"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
