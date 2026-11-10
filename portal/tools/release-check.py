#!/usr/bin/env python3
"""Fail-closed release metadata gates; never prints credentials or HTTP bodies.
Cryptographic verification is done by pinned cosign BEFORE this payload check.
These checks alone do not establish signatures, registry privacy or a release.
"""
import base64
import calendar
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
import urllib.request

REPO = 'dedvmedved-dot/otus-diplom'
IMAGE = 'ghcr.io/' + REPO + '-portal'
IDENTITY = 'https://github.com/' + REPO + '/.github/workflows/p8c-portal-release.yml@refs/heads/main'
SLSA = 'https://slsa.dev/provenance/v0.2'
SPDX = 'https://spdx.dev/Document'


class NotFound(Exception):
    pass


def digest(value):
    if not isinstance(value, str) or not re.fullmatch(r'sha256:[0-9a-f]{64}', value):
        raise ValueError('invalid sha256 digest')
    return value


def private_metadata(meta):
    if meta.get('name') != 'otus-diplom-portal' or meta.get('package_type') != 'container' or meta.get('visibility') != 'private' or meta.get('repository', {}).get('full_name') != REPO:
        raise ValueError('existing private package linked to exact repository required')
    return {'name': meta['name'], 'package_type': 'container', 'visibility': 'private', 'repository': REPO}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError('redirect forbidden')


def request(url, headers):
    # Caller supplies only fixed GitHub/GHCR origins; bounded response bytes.
    with urllib.request.build_opener(NoRedirect).open(urllib.request.Request(url, headers=headers), timeout=30) as response:
        data = response.read(8 * 1024 * 1024 + 1)
        if len(data) > 8 * 1024 * 1024:
            raise ValueError('metadata response too large')
        return data, response.headers


def predicate(source):
    if not re.fullmatch('[0-9a-f]{40}', source):
        raise ValueError('invalid source revision')
    return {'builder': {'id': IDENTITY}, 'buildType': 'https://github.com/Attestations/GitHubActionsWorkflow@v1',
            'invocation': {'configSource': {'uri': 'git+https://github.com/' + REPO + '@refs/heads/main', 'digest': {'sha1': source}}}}


def statements(text):
    decoder = json.JSONDecoder()
    values = []
    while text.strip():
        item, end = decoder.raw_decode(text.lstrip())
        values.extend(item if isinstance(item, list) else [item])
        text = text.lstrip()[end:]
    return values


def check_attestations(text, expected_digest, source, typ, sbom=None):
    expected_digest = digest(expected_digest)
    for envelope in statements(text):
        statement = json.loads(base64.b64decode(envelope['payload'], validate=True))
        if statement.get('_type') not in ('https://in-toto.io/Statement/v0.1', 'https://in-toto.io/Statement/v1'):
            continue
        if statement.get('predicateType') != typ:
            continue
        if statement.get('subject') != [{'name': IMAGE, 'digest': {'sha256': expected_digest[7:]}}]:
            continue
        if typ == SLSA:
            actual = statement.get('predicate', {})
            want = predicate(source)
            if any(actual.get(key) != value for key, value in want.items()):
                continue
        elif typ == SPDX:
            if sbom is None or statement.get('predicate') != sbom:
                continue
        else:
            raise ValueError('unknown predicate type')
        return
    raise ValueError('verified attestation does not bind exact image/source/predicate')


def check_signature(text, expected_digest, source):
    for signature in statements(text):
        c = signature.get('critical', {})
        if c.get('image', {}).get('docker-manifest-digest') == digest(expected_digest) and c.get('identity', {}).get('docker-reference') == IMAGE and signature.get('optional', {}).get('ref') == source:
            return
    raise ValueError('signature payload does not bind image/source')


def main():
    mode = sys.argv[1]
    if mode == 'digest':
        print(digest(json.loads(Path(sys.argv[2]).read_text())['containerimage.digest']))
    elif mode == 'release-gate':
        # typed release gate document: source/workflow/package/mode/issued_at/expiry/attempt are
        # all mandatory and must bind to the actual run (single attempt).
        gate_path, source, repository, attempt = Path(sys.argv[2]), sys.argv[3], sys.argv[4], sys.argv[5]
        try:
            g = json.loads(gate_path.read_text())
        except Exception:
            raise ValueError('release-gate unreadable')
        if not isinstance(g, dict):
            raise ValueError('release-gate not object')
        if g.get('source_sha') != source:
            raise ValueError('release-gate source_sha not bound')
        if g.get('repository') != repository:
            raise ValueError('release-gate repository not bound')
        if g.get('package') != IMAGE:
            raise ValueError('release-gate package not bound')
        wf = g.get('workflow_sha')
        if not isinstance(wf, str) or not re.fullmatch('[0-9a-f]{40}', wf):
            raise ValueError('release-gate workflow_sha missing/invalid')
        # workflow_sha must bind to the ACTUAL workflow (GITHUB_WORKFLOW_SHA), not just be a 40-hex
        # string; a missing runtime binding is not authorization.
        expected_wf = os.environ.get('GITHUB_WORKFLOW_SHA')
        if not expected_wf or wf != expected_wf:
            raise ValueError('release-gate workflow_sha not bound to actual workflow')
        if g.get('mode') != 'LIVE':
            raise ValueError('release-gate mode must be LIVE')
        issued = g.get('issued_at_utc')
        if not isinstance(issued, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z', issued):
            raise ValueError('release-gate issued_at_utc missing/invalid')
        expiry = g.get('expiry_hours')
        if not isinstance(expiry, int) or not (0 < expiry <= 24):
            raise ValueError('release-gate expiry_hours invalid')
        try:
            issued_epoch = calendar.timegm(time.strptime(issued, '%Y-%m-%dT%H:%M:%SZ'))
        except Exception:
            raise ValueError('release-gate issued_at_utc unparseable')
        now = time.time()
        if issued_epoch > now:
            raise ValueError('release-gate issued_at_utc not yet active (future)')
        if issued_epoch + expiry * 3600 < now:
            raise ValueError('release-gate expired')
        # single attempt: the gate must declare attempt=1 AND the actual run attempt must be 1
        # (a real second run is rejected, not silently accepted).
        if g.get('attempt') != 1 or str(attempt) != '1':
            raise ValueError('release-gate single-attempt only (attempt and run_attempt must be 1)')
        print(json.dumps({'gate': 'bound', 'source': source, 'repository': repository, 'attempt': attempt}))
    elif mode == 'predicate':
        print(json.dumps(predicate(sys.argv[2]), sort_keys=True))
    elif mode == 'first-creation':
        # Typed first-creation gate: repository/package/workflow are MANDATORY and must bind to
        # the actual source + target artifacts (404 alone is not a basis).
        gate_path = Path(sys.argv[2])
        try:
            g = json.loads(gate_path.read_text())
        except Exception:
            raise ValueError('first-creation gate unreadable')
        if not isinstance(g, dict) or not re.fullmatch('[0-9a-f]{40}', str(g.get('source_sha', ''))) \
                or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z', str(g.get('issued_at_utc', ''))) \
                or not isinstance(g.get('expiry_hours'), int) or not (0 < g['expiry_hours'] <= 24):
            raise ValueError('first-creation gate incomplete/invalid')
        if g.get('mode') != 'LIVE':
            raise ValueError('first-creation requires mode=LIVE (not TEST_ONLY)')
        # single-attempt: the actual run_attempt must be 1 when it is bound (a real second seed
        # run is rejected); the gate's own attempt field, when present, must also be 1.
        run_attempt = os.environ.get('GITHUB_RUN_ATTEMPT')
        if (run_attempt is not None and run_attempt != '1') or (g.get('attempt') is not None and g.get('attempt') != 1):
            raise ValueError('first-creation single-attempt only (attempt and run_attempt must be 1)')
        github_sha = os.environ.get('GITHUB_SHA')
        if not github_sha or g.get('source_sha') != github_sha:
            raise ValueError('first-creation source_sha not bound to GITHUB_SHA')
        if os.environ.get('GITHUB_REPOSITORY') != REPO:
            raise ValueError('first-creation repository not the expected repo')
        if g.get('repository') != REPO:
            raise ValueError('first-creation gate.repository not bound')
        if g.get('package') != IMAGE:
            raise ValueError('first-creation gate.package not bound')
        wf = g.get('workflow_sha')
        expected_wf = os.environ.get('GITHUB_WORKFLOW_SHA')
        # workflow_sha is MANDATORY and must bind to the actual workflow; a missing runtime
        # binding is NOT authorization (unlike the prior "only if env present").
        if not isinstance(wf, str) or not re.fullmatch('[0-9a-f]{40}', wf) or not expected_wf or wf != expected_wf:
            raise ValueError('first-creation gate.workflow_sha not bound to actual workflow')
        try:
            issued = calendar.timegm(time.strptime(g['issued_at_utc'], '%Y-%m-%dT%H:%M:%SZ'))
        except Exception:
            raise ValueError('first-creation issued_at unparseable')
        now = time.time()
        if issued > now:
            raise ValueError('first-creation issued_at not yet active (future)')
        if issued + g['expiry_hours'] * 3600 < now:
            raise ValueError('first-creation gate expired')
        print(json.dumps({'first_creation': 'VERIFIED', 'source_sha': g['source_sha']}))
    elif mode == 'private':
        token = os.environ['GITHUB_TOKEN']
        try:
            data, _ = request('https://api.github.com/users/dedvmedved-dot/packages/container/otus-diplom-portal', {'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'})
        except urllib.request.HTTPError as e:
            if e.code == 404:
                raise NotFound('private package does not exist')
            raise
        print(json.dumps(private_metadata(json.loads(data)), sort_keys=True))
    elif mode == 'registry':
        expected = digest(sys.argv[2])
        credentials = base64.b64encode((os.environ['GITHUB_ACTOR'] + ':' + os.environ['GITHUB_TOKEN']).encode()).decode()
        data, _ = request('https://ghcr.io/token?service=ghcr.io&scope=repository:dedvmedved-dot/otus-diplom-portal:pull', {'Authorization': 'Basic ' + credentials})
        token = json.loads(data)['token']
        body, headers = request('https://ghcr.io/v2/dedvmedved-dot/otus-diplom-portal/manifests/' + expected, {'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.oci.image.manifest.v1+json, application/vnd.oci.image.index.v1+json, application/vnd.docker.distribution.manifest.v2+json'})
        if 'sha256:' + hashlib.sha256(body).hexdigest() != expected or headers.get('Docker-Content-Digest') != expected:
            raise ValueError('registry digest mismatch')
        print(json.dumps({'image': IMAGE, 'digest': expected, 'manifestVerified': True}))
    elif mode == 'verified':
        directory, expected, source = Path(sys.argv[2]), digest(sys.argv[3]), sys.argv[4]
        required = ['sbom.spdx.json', 'provenance.json', 'build-metadata.json', 'scan-binary.json', 'scan-image.json', 'signature.json', 'attestation-sbom.jsonl', 'attestation-provenance.jsonl', 'private-before.json', 'private-after.json', 'registry.json', 'sign.txt', 'attest-sbom.txt', 'attest-provenance.txt', 'go-version.txt', 'go-binary.sha256']
        for name in required:
            p = directory / name
            if not p.is_file() or p.stat().st_size == 0:
                raise ValueError('missing release artifact: ' + name)
        # parse/bind the JSON artifacts (not just size>0): schema/identity/source/digest
        try:
            build = json.loads((directory / 'build-metadata.json').read_text())
        except Exception:
            raise ValueError('build-metadata.json not valid JSON')
        if build.get('containerimage.digest') != expected:
            raise ValueError('build-metadata digest does not bind expected image')
        for name in ('scan-binary.json', 'scan-image.json', 'registry.json', 'private-before.json', 'private-after.json'):
            try:
                obj = json.loads((directory / name).read_text())
            except Exception:
                raise ValueError(name + ' not valid JSON')
            if name in ('private-before.json', 'private-after.json'):
                if obj.get('visibility') != 'private':
                    raise ValueError(name + ' not private')
                if obj.get('repository') != REPO:
                    raise ValueError(name + ' wrong repository')
            elif name == 'registry.json':
                if obj.get('image') != IMAGE:
                    raise ValueError('registry image binding mismatch')
                if obj.get('digest') != expected:
                    raise ValueError('registry digest mismatch')
                if obj.get('manifestVerified') is not True:
                    raise ValueError('registry manifestVerified false')
            else:  # scan-binary/image
                if not isinstance(obj, dict) or not isinstance(obj.get('Results'), list):
                    raise ValueError(name + ' invalid scan shape')
                if name == 'scan-image.json':
                    artifact = str(obj.get('ArtifactName') or '')
                    repodigests = (obj.get('Metadata') or {}).get('RepoDigests', []) or []
                    expected_ref = IMAGE + '@' + expected
                    for ref in [artifact] + [str(rd) for rd in repodigests]:
                        if ref and expected_ref not in ref:
                            raise ValueError(name + ' references a different image/digest')
                for res in obj['Results']:
                    if not isinstance(res, dict):
                        raise ValueError(name + ' invalid scan result')
                    for vuln in res.get('Vulnerabilities', []):
                        if not isinstance(vuln, dict):
                            raise ValueError(name + ' malformed vulnerability leaf')
                        if vuln.get('Severity') in ('CRITICAL', 'HIGH'):
                            raise ValueError(name + ' has HIGH/CRITICAL vulnerability')
        try:
            sbom = json.loads((directory / 'sbom.spdx.json').read_text())
        except Exception:
            raise ValueError('sbom.spdx.json not valid JSON')
        if not isinstance(sbom, dict) or not sbom.get('spdxVersion'):
            raise ValueError('sbom.spdx.json missing spdxVersion')
        try:
            prov = json.loads((directory / 'provenance.json').read_text())
        except Exception:
            raise ValueError('provenance.json not valid JSON')
        if prov.get('builder', {}).get('id') != IDENTITY or prov.get('invocation', {}).get('configSource', {}).get('digest', {}).get('sha1') != source:
            raise ValueError('provenance does not bind workflow/source')
        check_signature((directory / 'signature.json').read_text(), expected, source)
        check_attestations((directory / 'attestation-provenance.jsonl').read_text(), expected, source, SLSA)
        check_attestations((directory / 'attestation-sbom.jsonl').read_text(), expected, source, SPDX, sbom)
        print(json.dumps({'image': IMAGE, 'digest': expected, 'source': source, 'payloadBinding': 'PASS'}))
    else:
        raise ValueError('unknown check')


if __name__ == '__main__':
    try:
        main()
    except NotFound:
        print('STOP: private package not found', file=sys.stderr)
        sys.exit(2)
    except Exception:
        print('STOP: release metadata gate failed; no credential-bearing diagnostics', file=sys.stderr)
        sys.exit(1)
