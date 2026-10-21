#!/usr/bin/env python3
"""Fail-closed release metadata gates; never prints credentials or HTTP bodies.
Cryptographic verification is done by pinned cosign BEFORE this payload check.
These checks alone do not establish signatures, registry privacy or a release.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import urllib.request

REPO = 'dedvmedved-dot/otus-diplom'
IMAGE = 'ghcr.io/' + REPO + '-portal'
IDENTITY = 'https://github.com/' + REPO + '/.github/workflows/p8c-portal-release.yml@refs/heads/main'
SLSA = 'https://slsa.dev/provenance/v0.2'
SPDX = 'https://spdx.dev/Document'


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
    elif mode == 'predicate':
        print(json.dumps(predicate(sys.argv[2]), sort_keys=True))
    elif mode == 'private':
        token = os.environ['GITHUB_TOKEN']
        data, _ = request('https://api.github.com/users/dedvmedved-dot/packages/container/otus-diplom-portal', {'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'})
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
            if not (directory / name).is_file() or (directory / name).stat().st_size == 0:
                raise ValueError('missing release artifact: ' + name)
        check_signature((directory / 'signature.json').read_text(), expected, source)
        check_attestations((directory / 'attestation-provenance.jsonl').read_text(), expected, source, SLSA)
        check_attestations((directory / 'attestation-sbom.jsonl').read_text(), expected, source, SPDX, json.loads((directory / 'sbom.spdx.json').read_text()))
        print(json.dumps({'image': IMAGE, 'digest': expected, 'source': source, 'payloadBinding': 'PASS'}))
    else:
        raise ValueError('unknown check')


if __name__ == '__main__':
    try:
        main()
    except Exception:
        print('STOP: release metadata gate failed; no credential-bearing diagnostics', file=sys.stderr)
        sys.exit(1)
