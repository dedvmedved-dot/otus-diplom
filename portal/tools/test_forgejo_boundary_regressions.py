#!/usr/bin/env python3
"""Boundary regressions for the review #55 rework (offline, synthetic inputs only).

Maps 1:1 to the review's "next acceptance" boundaries:

  1. template -> shell   : the workflow template's shell steps resolve against the
                           REAL workspace layout (no repeated `cd`, gate not
                           interpolated into shell source).
  2. runtime -> policy   : the runtime-observed values (evidence bundle) are only
                           ever COMPARED against the INDEPENDENT policy bindings;
                           stale self-reported pins in the evidence are ignored.
  3. HTTP -> next origin : the execution transport never leaks Basic/Bearer
                           credentials to a non-trusted origin (foreign realm
                           refused, implicit redirect refused).
  4. workspace -> real   : the lock write runs against a copy of the REAL
     lock           portal/versions.lock layout and preserves every other section.
"""
import hashlib
import json
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
from pathlib import Path

import forgejo_lock_gate as gate

REPO_ROOT = Path(__file__).resolve().parents[2]
PINNED = "4c09d6b4a85e2d021516244988f48b92eade7acf"
TOOLS = "a" * 40
WORKFLOW = "c" * 40
OWNER = "owner-otus@example"
RUN_ID = "1234567890"

# REAL image identity from the actual portal/versions.lock.
REAL_REGISTRY_HOST = "git.aiopslab.online"
REAL_IMAGE = "git.aiopslab.online/aiopslab/otus-diplom-portal"


def iso(epoch):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(epoch))


def _statement(image, digest, run_id=RUN_ID):
    return {
        "_type": "https://in-toto.io/Statement/v1",
        "subject": [{"name": image, "digest": {"sha256": digest[len("sha256:"):]}}],
        "predicateType": gate.SLSA,
        "predicate": gate.build_predicate(PINNED, WORKFLOW, TOOLS, run_id),
    }


def full_source_tree():
    import subprocess
    return subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", PINNED],
        capture_output=True, text=True, check=True, cwd=str(REPO_ROOT)).stdout.splitlines()


def _evidence(image, registry_host, digest, manifest, run_id=RUN_ID, actor=OWNER):
    return {
        "owner_gate": {
            "owner": OWNER, "source_sha": PINNED, "tools_sha": TOOLS, "workflow_sha": WORKFLOW,
            "repository": "aiopslab/otus-diplom", "package": image,
            "ref": "refs/heads/main", "mode": "LIVE",
            "issued_at_utc": iso(time.time() - 60), "expiry_hours": 1,
            "attempt": 1, "run_id": run_id,
        },
        "source_sha": PINNED,
        "tools_sha": TOOLS,
        "workflow_sha": WORKFLOW,
        "source_inventory": full_source_tree(),
        "tools_inventory": list(gate.REQUIRED_TOOLS_FILES),
        "registry_host": registry_host,
        "image_ref": image,
        "digest": digest,
        "manifest_bytes": manifest,
        "docker_content_digest": digest,
        "verified_attestation": json.dumps(_statement(image, digest, run_id)) + "\n",
        "certificate_identity": gate.WORKFLOW_IDENTITY,
        "certificate_issuer": gate.FORGEJO_OIDC_ISSUER,
        "actor": actor,
        "run_id": run_id,
        "run_attempt": "1",
        "observed_repository": "aiopslab/otus-diplom",
        "observed_ref": "refs/heads/main",
        "observed_workflow_sha": WORKFLOW,
    }


class TestTemplateToShell(unittest.TestCase):
    def _template(self):
        import yaml
        return yaml.safe_load((Path(__file__).parent / "p8c-portal-forgejo-release.yml.template").read_text())

    def test_no_repeated_cd_in_test_job(self):
        # review #55 item 2: repeated `cd src/portal` resolves from an already
        # changed cwd; the test step must cd into src/portal exactly once.
        doc = self._template()
        test_steps = doc["jobs"]["test"]["steps"]
        step = next(s for s in test_steps if isinstance(s, dict)
                    and (s.get("name") or "").startswith("Helper mock"))
        run = step["run"]
        self.assertEqual(run.count("cd src/portal"), 1, run)

    def test_preflight_checkout_before_gate_and_no_release_perms(self):
        doc = self._template()
        pf = doc["jobs"]["preflight"]
        steps = pf["steps"]
        gate_i = next(i for i, s in enumerate(steps) if (s.get("name") or "").startswith("Verify owner gate"))
        # checkouts must come before the gate step
        self.assertLess(0, gate_i)
        perms = pf.get("permissions", {})
        self.assertNotIn("packages", perms)
        self.assertNotIn("id-token", perms)

    def test_gate_json_not_interpolated_into_run(self):
        doc = self._template()
        pf_steps = doc["jobs"]["preflight"]["steps"]
        gate_step = next(s for s in pf_steps if (s.get("name") or "").startswith("Verify owner gate"))
        run = gate_step["run"]
        self.assertNotIn("secrets.OWNER_GATE", run)   # not interpolated into source
        self.assertEqual(gate_step["env"]["OWNER_GATE"], "${{ secrets.OWNER_GATE }}")
        # data read via the env var, not the expression
        self.assertIn('printf \'%s\' "$OWNER_GATE"', run)


class TestRuntimeToPolicy(unittest.TestCase):
    BINDINGS = {"owner": OWNER, "trusted_registry": "registry.example",
                "source_sha": PINNED, "tools_sha": TOOLS, "workflow_sha": WORKFLOW}
    NOW = 2000000000

    def _base(self):
        image = "registry.example/aiopslab/otus-diplom-portal"
        manifest = b'{"schemaVersion":2}'
        digest = "sha256:" + hashlib.sha256(manifest).hexdigest()
        ev = _evidence(image, "registry.example", digest, manifest)
        ev["owner_gate"]["issued_at_utc"] = iso(self.NOW - 60)
        return ev

    def test_stale_self_reported_pins_ignored(self):
        # A stale self-reported pin in the evidence is NOT authority: the
        # independent policy binding decides. source_sha == policy => allowed even
        # if the evidence carries a bogus legacy pin key.
        ev = self._base()
        ev["pinned_source_sha"] = "b" * 40          # stale key, ignored
        ev["pinned_workflow_sha"] = "b" * 40        # stale key, ignored
        allowed, reason = gate.decide_lock_update(ev, self.BINDINGS, now=self.NOW)
        self.assertTrue(allowed, reason)

    def test_runtime_source_sha_checked_against_policy(self):
        ev = self._base()
        ev["source_sha"] = "b" * 40
        ev["pinned_source_sha"] = "b" * 40          # even if evidence self-consistently lies
        allowed, reason = gate.decide_lock_update(ev, self.BINDINGS, now=self.NOW)
        self.assertFalse(allowed)
        self.assertIn("mismatch", reason)

    def test_workflow_sha_flag_drives_decision_not_evidence(self):
        # The CLI --workflow-sha (policy) is the authority; a matching evidence
        # workflow_sha cannot override a wrong policy pin.
        ev = self._base()
        gate_py = Path(__file__).parent / "forgejo_lock_gate.py"
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            (td / "manifest.bin").write_bytes(ev["manifest_bytes"])
            ev.pop("manifest_bytes", None)
            ev["manifest_file"] = str(td / "manifest.bin")
            (td / "evidence.json").write_text(json.dumps(ev))
            r = subprocess.run(
                [sys.executable, str(gate_py), "verify", str(td / "evidence.json"),
                 "--owner", OWNER, "--trusted-registry", "registry.example",
                 "--pinned-source", PINNED, "--pinned-tools", TOOLS,
                 "--workflow-sha", "b" * 40],   # wrong policy pin
                capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("workflow_sha", r.stderr)


class TestHttpTransportNextOrigin(unittest.TestCase):
    def test_real_opener_refuses_implicit_redirect(self):
        # End-to-end proof that the execution transport's opener refuses a
        # redirect (which would otherwise leak the Basic/Bearer credential to the
        # next origin). A local server issues a 302; the opener must raise, not
        # follow.
        import http.server
        import socketserver
        import threading

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == "/redirect":
                    self.send_response(302)
                    self.send_header("Location", "http://127.0.0.1:%d/v2/" % self.server.server_address[1])
                    self.end_headers()
                else:
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(b"ok")

            def log_message(self, *args):
                pass

        srv = socketserver.TCPServer(("127.0.0.1", 0), Handler)
        port = srv.server_address[1]
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            with self.assertRaises(urllib.error.HTTPError) as cm:
                gate._strict_urlopen("http://127.0.0.1:%d/redirect" % port)
            self.assertEqual(cm.exception.code, 302)
        finally:
            srv.shutdown()
            srv.server_close()

    def test_bearer_realm_foreign_origin_refused(self):
        # The bearer challenge must not send Basic credentials to a foreign
        # origin (the "next origin" after the /v2/ ping).
        with self.assertRaises(ValueError) as cm:
            gate._bearer_token_url(
                'Bearer realm="https://auth.evil.example/token",service="x"', "registry.example")
        self.assertIn("trusted HTTPS origin", str(cm.exception))


class TestWorkspaceRealLock(unittest.TestCase):
    """Apply the verified digest to a COPY of the REAL portal/versions.lock, in the
    same workspace layout (src/portal/versions.lock), and prove the other sections
    survive and a foreign image / missing authorization is refused."""

    GATE_PY = Path(__file__).parent / "forgejo_lock_gate.py"
    REAL_LOCK = REPO_ROOT / "portal" / "versions.lock"

    def _run_apply(self, ev, lock_path, apply_lock=True):
        cmd = [sys.executable, str(self.GATE_PY), "verify", str(ev),
               "--owner", OWNER, "--trusted-registry", REAL_REGISTRY_HOST,
               "--pinned-source", PINNED, "--pinned-tools", TOOLS,
               "--workflow-sha", WORKFLOW,
               "--apply", str(lock_path)]
        if apply_lock:
            cmd += ["--apply-lock", "true"]
        return subprocess.run(cmd, capture_output=True, text=True)

    def test_real_lock_apply_preserves_sections(self):
        manifest = b'{"schemaVersion":2,"mediaType":"application/vnd.oci.image.manifest.v1+json"}'
        digest = "sha256:" + hashlib.sha256(manifest).hexdigest()
        ev = _evidence(REAL_IMAGE, REAL_REGISTRY_HOST, digest, manifest)
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            # same workspace layout: src/portal/versions.lock
            (td / "tools").mkdir(parents=True)
            lock = td / "tools" / "images.lock"
            original = (REPO_ROOT / "images.lock").read_text()
            lock.write_text(original)
            (td / "manifest.bin").write_bytes(manifest)
            ev.pop("manifest_bytes", None)
            ev["manifest_file"] = str(td / "manifest.bin")
            (td / "evidence.json").write_text(json.dumps(ev))
            r = self._run_apply(td / "evidence.json", lock)
            self.assertEqual(r.returncode, 0, r.stderr)
            text = lock.read_text()
            self.assertIn('digest: "%s"' % digest, text)
            self.assertNotIn('digest: "NOT_VERIFIED"', text)
            self.assertEqual(text, original.replace('digest: "NOT_VERIFIED"', 'digest: "%s"' % digest).replace('verified: false\n', 'verified: true\n'))

    def test_real_lock_foreign_image_not_rewritten(self):
        manifest = b'{"schemaVersion":2}'
        digest = "sha256:" + hashlib.sha256(manifest).hexdigest()
        # A fully-valid chain for a DIFFERENT image than the real lock's
        # registry value: the chain passes, but apply_lock_pair must refuse to
        # rewrite the foreign image automatically.
        foreign_image = "git.aiopslab.online/aiopslab/OTHER-image"
        ev = _evidence(foreign_image, REAL_REGISTRY_HOST, digest, manifest)
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            (td / "tools").mkdir(parents=True)
            lock = td / "tools" / "images.lock"
            original = (REPO_ROOT / "images.lock").read_text()
            lock.write_text(original)
            (td / "manifest.bin").write_bytes(manifest)
            ev.pop("manifest_bytes", None)
            ev["manifest_file"] = str(td / "manifest.bin")
            (td / "evidence.json").write_text(json.dumps(ev))
            r = self._run_apply(td / "evidence.json", lock)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("pair mismatch", r.stderr)
            self.assertEqual(lock.read_text(), original)  # untouched

    def test_real_lock_refused_without_authorization(self):
        manifest = b'{"schemaVersion":2}'
        digest = "sha256:" + hashlib.sha256(manifest).hexdigest()
        ev = _evidence(REAL_IMAGE, REAL_REGISTRY_HOST, digest, manifest)
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            (td / "tools").mkdir(parents=True)
            lock = td / "tools" / "images.lock"
            original = (REPO_ROOT / "images.lock").read_text()
            lock.write_text(original)
            (td / "manifest.bin").write_bytes(manifest)
            ev.pop("manifest_bytes", None)
            ev["manifest_file"] = str(td / "manifest.bin")
            (td / "evidence.json").write_text(json.dumps(ev))
            r = self._run_apply(td / "evidence.json", lock, apply_lock=False)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("apply-lock", r.stderr)
            self.assertEqual(lock.read_text(), original)

    # --- review #58 item 5: pre-push lock-image agreement (CLI) --------------

    def _run_lock_image_check(self, lock_path, image_ref):
        return subprocess.run(
            [sys.executable, str(self.GATE_PY), "lock-image-check",
             "--lock", str(lock_path), "--image", image_ref],
            capture_output=True, text=True)

    def test_lock_image_check_agrees_with_real_lock(self):
        with tempfile.TemporaryDirectory() as td:
            lock = Path(td) / "versions.lock"
            lock.write_text(self.REAL_LOCK.read_text())
            r = self._run_lock_image_check(lock, REAL_IMAGE)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn('"lock_image_agreed": true', r.stdout)

    def test_lock_image_check_refuses_template_path_mismatch_before_push(self):
        # The OLD template IMAGE path /aiopslab/... does NOT equal the real lock's
        # /dedvmedved-dot/... — the pre-push check must refuse (host substitution
        # alone does not make them equal).
        with tempfile.TemporaryDirectory() as td:
            lock = Path(td) / "versions.lock"
            lock.write_text(self.REAL_LOCK.read_text())
            wrong = REAL_REGISTRY_HOST + "/other/otus-diplom-portal"
            r = self._run_lock_image_check(lock, wrong)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("pair mismatch", r.stderr)


class TestOwnerGateCliPolicyPin(unittest.TestCase):
    """review #61 item 1: the owner-gate CLI REQUIRES --pinned-workflow (the
    INDEPENDENT protected out-of-band policy pin). Omitting it must fail-closed,
    and a policy pin that contradicts an agreeing document+runtime must be
    refused — proving the real CLI/template boundary, not just the pure
    function."""

    GATE_PY = Path(__file__).parent / "forgejo_lock_gate.py"
    PKG = "registry.example/aiopslab/otus-diplom-portal"

    def _gate_json(self, workflow=WORKFLOW):
        return json.dumps({
            "owner": OWNER, "source_sha": PINNED, "tools_sha": TOOLS,
            "workflow_sha": workflow,
            "repository": "aiopslab/otus-diplom",
            "package": self.PKG, "ref": "refs/heads/main", "mode": "LIVE",
            "issued_at_utc": iso(time.time() - 60), "expiry_hours": 1,
            "attempt": 1, "run_id": RUN_ID,
        })

    def _run(self, gate_text, pinned_workflow):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            gate_file = td / "gate.json"
            gate_file.write_text(gate_text)
            cmd = [sys.executable, str(self.GATE_PY), "owner-gate", str(gate_file),
                   "--owner", OWNER, "--pinned-source", PINNED, "--pinned-tools", TOOLS,
                   "--package", self.PKG, "--repository", "aiopslab/otus-diplom",
                   "--ref", "refs/heads/main", "--actor", OWNER, "--run-id", RUN_ID,
                   "--run-attempt", "1",
                   "--observed-repository", "aiopslab/otus-diplom",
                   "--observed-ref", "refs/heads/main",
                   "--observed-workflow-sha", WORKFLOW]
            if pinned_workflow is not None:
                cmd += ["--pinned-workflow", pinned_workflow]
            return subprocess.run(cmd, capture_output=True, text=True)

    def test_missing_pinned_workflow_fails_closed(self):
        r = self._run(self._gate_json(), pinned_workflow=None)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("--pinned-workflow", r.stderr)

    def test_invalid_pinned_workflow_fails_closed(self):
        r = self._run(self._gate_json(), pinned_workflow="not-a-sha")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("--pinned-workflow", r.stderr)

    def test_policy_differs_from_agreeing_doc_and_runtime_fails(self):
        # Document and observed runtime AGREE (both == WORKFLOW), but the
        # independent policy pin differs -> refused. This is the case the review
        # flagged: two quantities (document + runtime) must not pass without the
        # third (policy pin).
        r = self._run(self._gate_json(workflow=WORKFLOW), pinned_workflow="b" * 40)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("workflow_sha", r.stderr)

    def test_matching_policy_allows(self):
        r = self._run(self._gate_json(workflow=WORKFLOW), pinned_workflow=WORKFLOW)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('"owner_gate": true', r.stdout)


class TestTemplatePolicyWorkflowPin(unittest.TestCase):
    """review #61 item 1/4: the template wires the INDEPENDENT policy pin through
    preflight AND the final verify/apply steps — never using the runtime
    GITHUB_WORKFLOW_SHA as its own policy pin."""

    def _doc(self):
        import yaml
        return yaml.safe_load((Path(__file__).parent / "p8c-portal-forgejo-release.yml.template").read_text())

    def test_release_verify_steps_use_policy_pin_not_runtime(self):
        doc = self._doc()
        for name_prefix in ("Gate lock update", "Apply verified digest"):
            step = next(s for s in doc["jobs"]["release"]["steps"]
                        if isinstance(s, dict) and (s.get("name") or "").startswith(name_prefix))
            run = step["run"]
            self.assertIn("--workflow-sha \"${{ secrets.POLICY_WORKFLOW_SHA }}\"", run)
            self.assertNotIn("--workflow-sha \"$GITHUB_WORKFLOW_SHA\"", run)

    def test_predicate_still_binds_runtime_workflow_sha(self):
        # The predicate (SLSA configSource) must bind the ACTUAL executed workflow
        # SHA (runtime), which preflight already cross-checked against the policy
        # pin — not a placeholder.
        doc = self._doc()
        step = next(s for s in doc["jobs"]["release"]["steps"]
                    if isinstance(s, dict) and (s.get("name") or "").startswith("SBOM + provenance"))
        self.assertIn("$GITHUB_WORKFLOW_SHA", step["run"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
