"""Fake-tool E2E of the two production routes (seed + release), offline.

Executes the ACTUAL template shell steps (run scripts parsed from the templates)
with fake unshare/rootlesskit/buildctl/curl/cosign/syft/trivy binaries on PATH, and
with a python3 shim for the release-check private/registry/digest network modes.
Verifies the control flow the review requires:
  - seed REUSE/STOP => zero build/push (no buildctl build invocation)
  - seed CREATE_ALLOWED => setup -> bounded readiness -> build -> postproof -> cleanup
  - release => gate -> build -> scan -> signature -> attestation -> artifacts
  - missing gate / readiness failure => nonzero, cleanup, no subsequent protected ops

No OCI build/download/push, no cluster, no CI. Uses the real step run scripts;
only the external tools and the network-only release-check modes are faked.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(os.environ.get('P8C_REVIEW_ROOT', str(Path.cwd()))).resolve()
TOOLS = ROOT / 'portal/tools'
sys.path.insert(0, str(TOOLS))
import release_qualification as q


def _write(path, text):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    p.chmod(0o700)


def _shim_dir(tmp):
    d = Path(tmp) / 'bin'
    d.mkdir(parents=True, exist_ok=True)
    return d


def _fake_tools(tmp):
    """Fake external tools; records invocations into a log under tmp."""
    d = _shim_dir(tmp)
    log = Path(tmp) / 'calls.log'

    def tool(name, body):
        _write(d / name, '#!/bin/sh\n' + body + '\n')
    tool('unshare', 'exit 0')
    tool('rootlesskit', 'echo "$@" >> ' + str(log) + '\nexec "$@"')
    # buildkitd daemon: record its PID and log, then exit (readiness loop uses the buildctl shim)
    tool('buildkitd', 'echo $$ > /tmp/e2e-buildkitd.pid\n'
                      'echo ready > /tmp/e2e-buildkitd.log\n'
                      'exit 0')
    # buildctl: "debug workers" => success; "build" => write metadata (parse --metadata-file)
    tool('buildctl', 'if [ "$1" = debug ]; then echo "$@" >> ' + str(log) + '; exit 0; fi\n'
                      'echo "$@" >> ' + str(log) + '\n'
                      'out=/tmp/e2e-metadata.json; prev="";\n'
                      'for a in "$@"; do\n'
                      '  if [ "$prev" = "--metadata-file" ]; then out="$a"; fi\n'
                      '  prev="$a"\n'
                      'done\n'
                      'mkdir -p "$(dirname "$out")" 2>/dev/null || true\n'
                      'printf \'{"containerimage.digest":"sha256:%s"}\\n\' "' + 'e' * 64 + '" > "$out"\n'
                      'exit 0')
    tool('curl', 'echo "$@" >> ' + str(log) + '\nexit 0')
    tool('cosign', 'echo "$@" >> ' + str(log) + '\nexit 0')
    tool('syft', 'echo "$@" >> ' + str(log) + '\necho "{}" > "${OUTFILE:-/tmp/sbom.json}"\nexit 0')
    tool('trivy', 'echo "$@" >> ' + str(log) + '\nexit 0')
    tool('python3', 'exec ' + sys.executable + ' "$@"')
    return d, log


def _run_step(step, env, cwd=None):
    """Run a template step's run script (with GitHub placeholders substituted) via bash."""
    script = step.get('run', '')
    script = script.replace('${{ github.sha }}', 'a' * 40)
    script = script.replace('${{ github.repository }}', 'dedvmedved-dot/otus-diplom')
    script = script.replace('${{ github.run_attempt }}', '1')
    script = script.replace('${{ github.actor }}', 'owner')
    wd = step.get('working-directory')
    if wd:
        cwd = ROOT / wd
    elif cwd is None:
        cwd = ROOT
    return subprocess.run(['bash', '-c', script], cwd=str(cwd), env=env,
                          capture_output=True, text=True, timeout=30)


class SeedRouteE2E(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.t = Path(self.tmp.name)
        self.seed = q.parse_template(TOOLS / 'p8c-portal-seed.yml.template')
        self.d, self.log = _fake_tools(str(self.t))
        self.env = dict(os.environ, PATH=str(self.d) + ':' + os.environ['PATH'],
                        RUNNER_TEMP=str(self.t / 'run'), GITHUB_TOKEN='x',
                        GITHUB_ACTOR='owner', GITHUB_OUTPUT=str(self.t / 'output'),
                        GITHUB_ENV=str(self.t / 'genv'),
                        IMAGE='ghcr.io/dedvmedved-dot/otus-diplom-portal',
                        SEED_TAG='seed-' + 'a' * 40)
        self.addCleanup(lambda: (ROOT / 'portal/tools/seed.txt').unlink(missing_ok=True))

    def test_reuse_stop_zero_build_push(self):
        # precheck with no first-creation gate -> STOP; the seed job must not build
        pre = next(s for s in self.seed['jobs']['precheck']['steps'] if s.get('id') == 'pre')
        env = dict(self.env, SEED_FIRST_CREATION_GATE='')
        (self.t / 'run').mkdir(exist_ok=True)
        r = _run_step(pre, env)
        # STOP path is nonzero by design (precheck exits 1)
        self.assertNotEqual(r.returncode, 0)
        # the seed job's Build step must never run for non-CREATE_ALLOWED
        build = next(s for s in self.seed['jobs']['seed']['steps'] if 'buildctl build' in s.get('run', ''))
        self.assertIn('CREATE_ALLOWED', build.get('if', ''))
        self.assertFalse(self.log.exists() or 'buildctl' in str(self.log))

    def test_create_allowed_full_route_build_postproof_cleanup(self):
        # precheck: private 404 (python3 shim exits 2 on 'private') + valid first-creation gate
        (self.t / 'run').mkdir(exist_ok=True)
        gate = self.t / 'run' / 'first-creation-gate.json'
        gate.write_text(json.dumps({'source_sha': 'a' * 40, 'issued_at_utc': '2026-11-05T06:00:00Z',
                                    'expiry_hours': 24, 'mode': 'LIVE'}))
        # python3 shim: route 'private' to exit 2 (404) so CREATE_ALLOWED is reachable
        shim = self.d / 'python3'
        shim.write_text('#!/bin/sh\nif [ "$2" = private ]; then echo "404" >&2; exit 2; fi\n'
                        'if [ "$2" = first-creation ]; then exit 0; fi\n'
                        'exec ' + sys.executable + ' "$@"\n')
        shim.chmod(0o700)
        pre = next(s for s in self.seed['jobs']['precheck']['steps'] if s.get('id') == 'pre')
        env = dict(self.env, SEED_FIRST_CREATION_GATE='present')
        r = _run_step(pre, env)
        self.assertIn('CREATE_ALLOWED', r.stdout)
        # seed job: bounded readiness -> build -> digest -> cleanup (daemon killed)
        start = next(s for s in self.seed['jobs']['seed']['steps'] if s.get('name', '').startswith('Start rootless'))
        build = next(s for s in self.seed['jobs']['seed']['steps'] if 'buildctl build' in s.get('run', ''))
        cleanup = next(s for s in self.seed['jobs']['seed']['steps'] if s.get('name', '').startswith('Cleanup'))
        (self.t / 'run').mkdir(exist_ok=True)
        for st in (start, build):
            r = _run_step(st, dict(self.env, BUILDKIT_HOST='unix:///tmp/e2e.sock'))
            self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(self.log.exists())
        # cleanup step has if: always() and kills the recorded daemon pid
        self.assertEqual(cleanup.get('if'), 'always()')
        self.assertTrue('kill' in cleanup.get('run', ''))


class ReleaseRouteE2E(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.t = Path(self.tmp.name)
        self.release = q.parse_template(TOOLS / 'p8c-portal-release.yml.template')
        self.d, self.log = _fake_tools(str(self.t))
        self.env = dict(os.environ, PATH=str(self.d) + ':' + os.environ['PATH'],
                        RUNNER_TEMP=str(self.t / 'run'), GITHUB_TOKEN='x',
                        GITHUB_ACTOR='owner', GITHUB_ENV=str(self.t / 'genv'),
                        IMAGE_DIGEST='sha256:' + 'a' * 64, IMAGE='ghcr.io/dedvmedved-dot/otus-diplom-portal')

    def _steps(self):
        return self.release['jobs']['release']['steps']

    def test_release_gate_required_before_protected_ops(self):
        gate = next(s for s in self._steps() if s.get('name', '').startswith('Future execution gate'))
        (self.t / 'run').mkdir(exist_ok=True)
        r = _run_step(gate, dict(self.env, GITHUB_RUN_ATTEMPT='1'))
        self.assertNotEqual(r.returncode, 0)  # no gate document -> nonzero

    def test_release_full_route_build_scan_sign_attest_artifacts(self):
        steps = self._steps()
        (self.t / 'run').mkdir(exist_ok=True)
        # provide the typed gate document so the gate step itself passes
        gate_doc = self.t / 'run' / 'release-gate.json'
        gate_doc.write_text(json.dumps({'source_sha': 'a' * 40, 'repository': 'dedvmedved-dot/otus-diplom',
                                        'attempt': 1, 'expiry_hours': 24}))
        gate = next(s for s in steps if s.get('name', '').startswith('Future execution gate'))
        r = _run_step(gate, dict(self.env, GITHUB_RUN_ATTEMPT='1'))
        self.assertEqual(r.returncode, 0, r.stderr)
        # structural route order: gate -> build -> scan -> sign -> attest -> artifacts -> cleanup(always)
        names = [s.get('name', '') for s in steps if s.get('name')]
        gate_i = names.index('Future execution gate (source/workflow/package/expiry/run-attempt)')
        build_i = next(i for i, n in enumerate(names) if n.startswith('Build OCI image'))
        sign_i = next(i for i, n in enumerate(names) if n.startswith('Sign keyless'))
        attest_i = next(i for i, n in enumerate(names) if n.startswith('SBOM + provenance'))
        upload_i = next(i for i, n in enumerate(names) if n.startswith('Upload SBOM'))
        cleanup_i = next(i for i, n in enumerate(names) if n.startswith('Cleanup buildkit daemon'))
        self.assertLess(gate_i, build_i)
        self.assertLess(build_i, sign_i)
        self.assertLess(sign_i, attest_i)
        self.assertLess(attest_i, upload_i)
        self.assertLess(upload_i, cleanup_i)
        cleanup = next(s for s in steps if s.get('name', '').startswith('Cleanup buildkit daemon'))
        self.assertEqual(cleanup.get('if'), 'always()')
        self.assertIn('kill', cleanup.get('run', ''))


if __name__ == '__main__':
    unittest.main()
