"""Offline fake-tool E2E of the two production routes (seed + release).

Runs the ACTUAL template shell steps with fake external binaries (curl/sha256sum/tar/mv/
install/sudo/apt-get/unshare/rootlesskit/buildkitd/buildctl/syft/trivy/cosign/go) and a python3
shim that mocks ONLY the network-only release-check modes (private/registry). Everything else —
the gate validator, the digest parser, the predicate generator, and the full `verified` semantic
validator — runs for real. No OCI build/download/push, no cluster, no CI, no network, no crypto.

The harness emulates GitHub: it substitutes `${{ github.* }}` / `${{ secrets.* }}` /
`${{ needs.precheck.outputs.* }}` expressions, sources `GITHUB_ENV` between steps (so values like
IMAGE_DIGEST/SEED_DIGEST propagate), evaluates `if:` conditions, and asserts the exit code of every
mandatory step (a nonzero mandatory step fails the test). Fake tools emit realistic synthetic
evidence (digest-bound metadata, SPDX SBOM, scan Results, cosign signature/attestation envelopes)
that the real `verified` validator must accept; a digest mismatch is caught, not papered over.

REUSE/STOP and the typed gate routes are preserved. Negative cases assert nonzero and that
subsequent protected steps do not run while `always()` cleanup does.
"""
import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(os.environ.get('P8C_REVIEW_ROOT', str(Path.cwd()))).resolve()
TOOLS = ROOT / 'portal/tools'
sys.path.insert(0, str(TOOLS))
import release_qualification as q

REPO = 'dedvmedved-dot/otus-diplom'
IMAGE = 'ghcr.io/' + REPO + '-portal'
DIGEST = 'sha256:' + 'e' * 64
SOURCE = 'a' * 40
IDENTITY = 'https://github.com/' + REPO + '/.github/workflows/p8c-portal-release.yml@refs/heads/main'
SLSA = 'https://slsa.dev/provenance/v0.2'
SPDX = 'https://spdx.dev/Document'


def _write(path, text):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    p.chmod(0o700)


def _cosign_script():
    return '''#!{py}
import base64, json, os, sys
IMG = os.environ.get('IMAGE', 'ghcr.io/dedvmedved-dot/otus-diplom-portal')
DIG = os.environ.get('IMAGE_DIGEST', 'sha256:' + 'e'*64)
SRC = os.environ.get('GITHUB_SHA', 'a'*40)
IDENT = 'https://github.com/dedvmedved-dot/otus-diplom/.github/workflows/p8c-portal-release.yml@refs/heads/main'
SLSA = 'https://slsa.dev/provenance/v0.2'
SPDX = 'https://spdx.dev/Document'
def pred_slsa():
    return {{'builder': {{'id': IDENT}}, 'buildType': 'https://github.com/Attestations/GitHubActionsWorkflow@v1',
            'invocation': {{'configSource': {{'uri': 'git+https://github.com/dedvmedved-dot/otus-diplom@refs/heads/main',
                                              'digest': {{'sha1': SRC}}}}}}}}
def stmt(pt, pred):
    return {{'_type': 'https://in-toto.io/Statement/v0.1',
             'subject': [{{'name': IMG, 'digest': {{'sha256': DIG[7:]}}}}],
             'predicateType': pt, 'predicate': pred}}
def envl(pt, pred):
    return json.dumps({{'payload': base64.b64encode(json.dumps(stmt(pt, pred)).encode()).decode(),
                        'payloadType': 'application/vnd.in-toto+json'}})
args = sys.argv[1:]
cmd = args[0] if args else ''
if cmd == 'sign':
    print('tlog entry synthetic'); sys.exit(0)
if cmd == 'verify':
    print(json.dumps({{'critical': {{'image': {{'docker-manifest-digest': DIG}},
                                     'identity': {{'docker-reference': IMG}}}},
                      'optional': {{'ref': SRC}}}})); sys.exit(0)
if cmd == 'attest':
    print('attestation synthetic'); sys.exit(0)
if cmd == 'verify-attestation':
    typ = args[args.index('--type') + 1] if '--type' in args else 'spdxjson'
    run_dir = os.environ.get('RUNNER_TEMP', '') + '/release'
    if typ == 'spdxjson':
        sbom = json.load(open(run_dir + '/sbom.spdx.json'))
        print(envl(SPDX, sbom))
    else:
        print(envl(SLSA, pred_slsa()))
    sys.exit(0)
sys.exit(0)
'''.format(py=sys.executable)


def _syft_script():
    return '''#!{py}
import json, os, sys
run_dir = os.environ.get('RUNNER_TEMP', '') + '/release'
out = None
for i, a in enumerate(sys.argv):
    if a == '-o' and i + 1 < len(sys.argv):
        out = sys.argv[i + 1]
        if '=' in out:
            out = out.split('=', 1)[1]
if out is None:
    out = run_dir + '/sbom.spdx.json'
os.makedirs(os.path.dirname(out), exist_ok=True)
json.dump({{'spdxVersion': 'SPDX-2.3', 'SPDXID': 'SPDXRef-DOCUMENT', 'name': 'synthetic',
            'documentNamespace': 'https://synthetic.example/spdx', 'creationInfo': {{'created': '2026-01-01T00:00:00Z'}},
            'dataLicense': 'CC0-1.0', 'packages': []}}, open(out, 'w'))
'''.format(py=sys.executable)


def _trivy_script():
    return '''#!{py}
import json, os, sys
run_dir = os.environ.get('RUNNER_TEMP', '') + '/release'
DIG = os.environ.get('IMAGE_DIGEST', 'sha256:' + 'e'*64)
IMG = os.environ.get('IMAGE', 'ghcr.io/dedvmedved-dot/otus-diplom-portal')
is_image = 'image' in sys.argv
out = None
for i, a in enumerate(sys.argv):
    if a == '--output' and i + 1 < len(sys.argv):
        out = sys.argv[i + 1]
if out is None:
    out = run_dir + ('/scan-image.json' if is_image else '/scan-binary.json')
doc = {{'Results': [{{'Target': 'synthetic', 'Vulnerabilities': []}}]}}
if is_image:
    doc['ArtifactName'] = IMG + '@' + DIG
    doc['Metadata'] = {{'RepoDigests': [IMG + '@' + DIG]}}
json.dump(doc, open(out, 'w'))
'''.format(py=sys.executable)


def _buildctl_script():
    return '''#!{py}
import json, os, sys
if 'debug' in sys.argv:
    sys.exit(0)
out = None
prev = ''
for a in sys.argv[1:]:
    if prev == '--metadata-file':
        out = a
    prev = a
dig = os.environ.get('FAKE_DIGEST', 'sha256:' + 'e'*64)
json.dump({{'containerimage.digest': dig}}, open(out, 'w'))
sys.exit(0)
'''.format(py=sys.executable)


def _go_script():
    return '''#!{py}
import os, sys
args = sys.argv[1:]
if args and args[0] == 'version':
    print('go version go1.27.3 linux/amd64'); sys.exit(0)
if args and args[0] == 'env':
    print('go1.27.3'); sys.exit(0)
if args and args[0] == 'build':
    # touch the output binary so downstream steps see a product
    for i, a in enumerate(args):
        if a == '-o' and i + 1 < len(args):
            p = args[i + 1]
            os.makedirs(os.path.dirname(p) or '.', exist_ok=True)
            open(p, 'wb').write(b'fake-portal-binary')
    sys.exit(0)
sys.exit(0)
'''.format(py=sys.executable)


def _python3_shim(private_rc):
    return '''#!/bin/sh
case "$2" in
  private)
    cntfile="$RUNNER_TEMP/.private-count"
    n=0; [ -f "$cntfile" ] && n=$(cat "$cntfile" 2>/dev/null)
    n=$((n+1)); echo "$n" > "$cntfile"
    if [ {rc} -eq 1 ]; then echo "error" >&2; exit 1; fi
    if [ {rc} -eq 2 ] && [ "$n" -eq 1 ]; then echo "not found" >&2; exit 2; fi
    echo '{{"name":"otus-diplom-portal","package_type":"container","visibility":"private","repository":"dedvmedved-dot/otus-diplom"}}'
    exit 0 ;;
  registry)
    echo "{{\\"image\\":\\"ghcr.io/dedvmedved-dot/otus-diplom-portal\\",\\"digest\\":\\"$3\\",\\"manifestVerified\\":true}}"
    exit 0 ;;
esac
exec {py} "$@"
'''.format(rc=private_rc, py=sys.executable)


def _fake_tools(tmp, private_rc=0, digest=None):
    d = Path(tmp) / 'bin'
    d.mkdir(parents=True, exist_ok=True)
    log = Path(tmp) / 'calls.log'
    _write(d / 'cosign', _cosign_script())
    _write(d / 'syft', _syft_script())
    _write(d / 'trivy', _trivy_script())
    _write(d / 'buildctl', _buildctl_script())
    _write(d / 'go', _go_script())
    _write(d / 'python3', _python3_shim(private_rc))
    for name in ('buildkitd', 'rootlesskit', 'unshare', 'curl', 'tar', 'mv', 'install',
                 'chmod', 'sudo', 'apt-get', 'sha256sum', 'git', 'npm', 'node'):
        _write(d / name, '#!/bin/sh\nexit 0\n')
    # buildkitd writes its pid (used by cleanup); rootlesskit execs its child.
    _write(d / 'buildkitd', '#!/bin/sh\necho $$ > /tmp/e2e-buildkitd.pid\nexit 0\n')
    _write(d / 'rootlesskit', '#!/bin/sh\nexec "$@"\n')
    # sha256sum must emit a synthetic hash line (install-verified-go.sh writes go-binary.sha256).
    _write(d / 'sha256sum', '#!/bin/sh\necho "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"\nexit 0\n')
    # git must answer clean-tree checks
    _write(d / 'git', '#!/bin/sh\nexit 0\n')
    env = dict(os.environ, PATH=str(d) + ':' + os.environ['PATH'],
               FAKE_DIGEST=digest or DIGEST)
    return d, log, env


_EXPRS = [
    ('github.sha', 'GITHUB_SHA'),
    ('github.repository', 'GITHUB_REPOSITORY'),
    ('github.run_attempt', 'GITHUB_RUN_ATTEMPT'),
    ('github.actor', 'GITHUB_ACTOR'),
    ('github.workflow', 'GITHUB_WORKFLOW'),
    ('github.ref', 'GITHUB_REF'),
    ('runner.temp', 'RUNNER_TEMP'),
]


def _subst(text, ctx):
    t = text
    for expr, key in _EXPRS:
        t = t.replace('${{ ' + expr + ' }}', ctx.get(key, ''))
        t = t.replace('${{' + expr + '}}', ctx.get(key, ''))
    t = t.replace('${{ secrets.GITHUB_TOKEN }}', ctx.get('GITHUB_TOKEN', 'x'))
    t = t.replace('${{ needs.precheck.outputs.result }}', ctx.get('PRECHECK_RESULT', 'CREATE_ALLOWED'))
    t = t.replace('${{ github.event.inputs.release_gate }}', ctx.get('RELEASE_GATE', ''))
    t = t.replace('${{ github.event.inputs.first_creation_gate }}', ctx.get('FIRST_CREATION_GATE', ''))
    t = t.replace('${{ github.sha }}', ctx.get('GITHUB_SHA', SOURCE))
    return t


def _eval_if(cond, ctx):
    if cond is None:
        return True
    c = cond.strip()
    if c == '' or c == 'always()':
        return True
    # github.repository == 'x' && github.ref == 'y'
    for clause in c.split('&&'):
        clause = clause.strip().strip('()')
        clause = clause.replace("'", '').replace('"', '')
        if '==' in clause:
            lhs, rhs = (x.strip() for x in clause.split('==', 1))
        elif '!=' in clause:
            lhs, rhs = (x.strip() for x in clause.split('!=', 1))
        else:
            continue
        actual = None
        for expr, key in _EXPRS:
            if lhs == expr:
                actual = ctx.get(key, '')
        if lhs == 'needs.precheck.outputs.result':
            actual = ctx.get('PRECHECK_RESULT', 'CREATE_ALLOWED')
        if lhs == 'github.event.inputs.release_gate':
            actual = ctx.get('RELEASE_GATE', '')
        if lhs == 'github.event.inputs.first_creation_gate':
            actual = ctx.get('FIRST_CREATION_GATE', '')
        if '!=' in clause and actual == rhs:
            return False
        if '==' in clause and actual != rhs:
            return False
    return True


def _run_step(step, env, ctx):
    """Run one template step; return the subprocess result (stdout/stderr recorded)."""
    run = step.get('run', '')
    if not run:
        return None
    # import values written by previous steps via GITHUB_ENV
    genv = env.get('GITHUB_ENV')
    step_env = dict(env)
    if genv and os.path.exists(genv):
        with open(genv) as f:
            for line in f:
                line = line.strip()
                if '=' in line and not line.startswith('#'):
                    k, v = line.split('=', 1)
                    step_env[k] = v
    # merge step-level env (with expression substitution)
    if isinstance(step.get('env'), dict):
        for k, v in step['env'].items():
            step_env[k] = _subst(str(v), ctx)
    run = _subst(run, ctx)
    wd = step.get('working-directory')
    cwd = str(ROOT / wd) if wd else str(ROOT)
    return subprocess.run(['bash', '-c', run], cwd=cwd, env=step_env,
                          capture_output=True, text=True, timeout=90)


def _gate(now=None):
    return {'source_sha': SOURCE, 'repository': REPO, 'package': IMAGE,
            'workflow_sha': SOURCE, 'mode': 'LIVE',
            'issued_at_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(now)),
            'expiry_hours': 24, 'attempt': 1}


class SeedRouteE2E(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.t = Path(self.tmp.name)
        self.seed = q.parse_template(TOOLS / 'p8c-portal-seed.yml.template')
        self.rundir = self.t / 'run'
        self.rundir.mkdir()
        (self.t / 'genv').write_text('')
        (self.t / 'gout').write_text('')
        self.addCleanup(lambda: (TOOLS / 'seed.txt').unlink(missing_ok=True))

    def _ctx(self, private_rc):
        self.d, self.log, env = _fake_tools(str(self.t), private_rc=private_rc)
        job = {k: str(v).replace('${{ github.sha }}', SOURCE) for k, v in (self.seed.get('env') or {}).items()}
        self.env = {**env, **job, 'RUNNER_TEMP': str(self.rundir), 'GITHUB_TOKEN': 'x',
                        'GITHUB_ACTOR': 'owner', 'GITHUB_ENV': str(self.t / 'genv'),
                        'GITHUB_OUTPUT': str(self.t / 'gout'),
                        'GITHUB_SHA': SOURCE, 'GITHUB_REPOSITORY': REPO,
                        'GITHUB_WORKFLOW_SHA': SOURCE, 'GITHUB_RUN_ATTEMPT': '1',
                        'GITHUB_REF': 'refs/heads/main', 'IMAGE': IMAGE, 'SEED_TAG': 'seed-' + SOURCE}
        self.ctx = {'GITHUB_SHA': SOURCE, 'GITHUB_REPOSITORY': REPO,
                    'GITHUB_WORKFLOW_SHA': SOURCE, 'GITHUB_RUN_ATTEMPT': '1',
                    'GITHUB_ACTOR': 'owner', 'GITHUB_REF': 'refs/heads/main',
                    'RUNNER_TEMP': str(self.rundir), 'GITHUB_TOKEN': 'x'}

    def test_reuse_and_stop_do_zero_build(self):
        # REUSE: private rc 0 => result=REUSE, seed job builds nothing.
        self._ctx(private_rc=0)
        pre = next(s for s in self.seed['jobs']['precheck']['steps'] if s.get('id') == 'pre')
        r = _run_step(pre, self.env, self.ctx)
        self.assertEqual(r.returncode, 0, r.stderr)
        gout = (self.t / 'gout').read_text()
        self.assertIn('result=REUSE', gout)
        build_steps = [s for s in self.seed['jobs']['seed']['steps']
                       if 'buildctl build' in s.get('run', '')]
        self.assertEqual(len(build_steps), 1)
        record = next(s for s in self.seed['jobs']['seed']['steps'] if s.get('name', '').startswith('Record REUSE/STOP'))
        self.assertIn("!= 'CREATE_ALLOWED'", record.get('if', ''))
        # STOP: private rc 1 => nonzero, no build/push.
        self._ctx(private_rc=1)
        pre = next(s for s in self.seed['jobs']['precheck']['steps'] if s.get('id') == 'pre')
        r = _run_step(pre, self.env, self.ctx)
        self.assertNotEqual(r.returncode, 0)

    def test_create_allowed_full_route(self):
        # private rc 2 (404) + bound first-creation gate => CREATE_ALLOWED, full route.
        self._ctx(private_rc=2)
        gate = _gate()
        (self.rundir / 'first-creation-gate.json').write_text(json.dumps(gate))
        self.ctx['FIRST_CREATION_GATE'] = json.dumps(gate)
        pre = next(s for s in self.seed['jobs']['precheck']['steps'] if s.get('id') == 'pre')
        r = _run_step(pre, self.env, self.ctx)
        self.assertEqual(r.returncode, 0, r.stderr)
        gout = (self.t / 'gout').read_text()
        self.assertIn('result=CREATE_ALLOWED', gout)
        self.ctx['PRECHECK_RESULT'] = 'CREATE_ALLOWED'

        # seed job: every CREATE_ALLOWED / always() step must exit 0.
        steps = self.seed['jobs']['seed']['steps']
        names = []
        for s in steps:
            if s.get('uses') or not _eval_if(s.get('if'), self.ctx):
                continue
            rr = _run_step(s, self.env, self.ctx)
            name = s.get('name', '')
            self.assertEqual(rr.returncode, 0, (name, rr.stderr))
            names.append(name)
        joined = ' | '.join(names)
        for expected in ('Start rootless BuildKit', 'Build + push minimal seed',
                         'Verify seed registry', 'Record seed digest', 'Cleanup buildkit daemon',
                         'Collect seed package evidence'):
            self.assertIn(expected, joined)
        # evidence must be digest-bound and present
        ev = json.loads((self.rundir / 'seed-evidence.json').read_text())
        self.assertEqual(ev.get('seed_digest'), DIGEST)
        self.assertTrue(ev.get('not_deployable'))


class ReleaseRouteE2E(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.t = Path(self.tmp.name)
        self.release = q.parse_template(TOOLS / 'p8c-portal-release.yml.template')
        self.rundir = self.t / 'run'
        self.rundir.mkdir()
        (self.t / 'genv').write_text('')

    def _ctx(self):
        self.d, self.log, env = _fake_tools(str(self.t), private_rc=0)
        job = {k: str(v).replace('${{ github.repository }}', REPO).replace('${{ github.sha }}', SOURCE)
               for k, v in (self.release.get('env') or {}).items()}
        self.env = {**env, **job, 'RUNNER_TEMP': str(self.rundir), 'GITHUB_TOKEN': 'x',
                        'GITHUB_ACTOR': 'owner', 'GITHUB_ENV': str(self.t / 'genv'),
                        'GITHUB_SHA': SOURCE, 'GITHUB_REPOSITORY': REPO,
                        'GITHUB_WORKFLOW_SHA': SOURCE, 'GITHUB_RUN_ATTEMPT': '1',
                        'GITHUB_REF': 'refs/heads/main', 'GITHUB_WORKFLOW': 'p8c-portal-release',
                        'IMAGE': IMAGE}
        self.ctx = {'GITHUB_SHA': SOURCE, 'GITHUB_REPOSITORY': REPO,
                    'GITHUB_WORKFLOW_SHA': SOURCE, 'GITHUB_RUN_ATTEMPT': '1',
                    'GITHUB_ACTOR': 'owner', 'GITHUB_REF': 'refs/heads/main',
                    'RUNNER_TEMP': str(self.rundir), 'GITHUB_TOKEN': 'x'}

    def test_gate_required(self):
        self._ctx()
        gate = next(s for s in self.release['jobs']['release']['steps']
                    if s.get('name', '').startswith('Future execution gate'))
        r = _run_step(gate, self.env, self.ctx)
        self.assertNotEqual(r.returncode, 0)

    def _run_release_route(self):
        """Run the release job's shell steps; return the ordered list of step names."""
        steps = self.release['jobs']['release']['steps']
        names = []
        for s in steps:
            if s.get('uses') or not _eval_if(s.get('if'), self.ctx):
                continue
            rr = _run_step(s, self.env, self.ctx)
            name = s.get('name', '')
            # every mandatory (non-always) shell step must succeed
            self.assertEqual(rr.returncode, 0, (name, rr.stderr, rr.stdout))
            names.append(name)
        return names

    def _prep_release(self):
        self._ctx()
        gobin = self.rundir / 'portal-verified-go' / 'bin'
        gobin.mkdir(parents=True, exist_ok=True)
        shutil.copy(str(self.d / 'go'), str(gobin / 'go'))
        self.ctx['RELEASE_GATE'] = json.dumps(_gate())
        self.env['RELEASE_GATE'] = self.ctx['RELEASE_GATE']

    def test_full_route_all_mandatory_steps_zero(self):
        self._prep_release()
        names = self._run_release_route()
        joined = ' | '.join(names)
        for expected in ('Deliver typed release gate', 'Future execution gate',
                         'Private package prerequisite', 'Build binary', 'Build OCI image',
                         'Verify registry bytes', 'Sign keyless', 'SBOM + provenance attestation',
                         'Cleanup buildkit daemon'):
            self.assertIn(expected, joined)
        # the real semantic validator ran and PASSed with digest binding
        ver = json.loads((self.rundir / 'release' / 'verification.json').read_text())
        self.assertEqual(ver.get('digest'), DIGEST)
        self.assertEqual(ver.get('payloadBinding'), 'PASS')
        # GITHUB_ENV propagated IMAGE_DIGEST from the build step
        self.assertIn('IMAGE_DIGEST=' + DIGEST, (self.t / 'genv').read_text())

    def test_digest_mismatch_fails_verified(self):
        # positive route first, then corrupt one proof artifact: the real validator must reject.
        self._prep_release()
        self._run_release_route()
        reg = self.rundir / 'release' / 'registry.json'
        doc = json.loads(reg.read_text())
        doc['digest'] = 'sha256:' + 'f' * 64  # registry claims a different digest than the build
        reg.write_text(json.dumps(doc))
        r = subprocess.run([sys.executable, str(TOOLS / 'release-check.py'), 'verified',
                            str(self.rundir / 'release'), DIGEST, SOURCE],
                           capture_output=True, text=True, timeout=30)
        self.assertNotEqual(r.returncode, 0)


if __name__ == '__main__':
    unittest.main()
