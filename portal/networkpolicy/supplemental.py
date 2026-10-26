#!/usr/bin/env python3
"""P8C RV-02 Phase-2 — supplemental read-only collector (OFFLINE-ONLY, NOT approved to run).

Addresses LI-01..04. Separate from the approved base inventory.py; this script is
NOT authorized for live execution until an exact-script Architect approval
(PHASE2_LIVE_READS_APPROVED=NO, OWNER_PHASE2_HANDOFF_ALLOWED=NO).

Adds the projections the base collector lacked:
  - ObjectStore spec.configuration (endpointURL/destinationPath origin-only,
    s3Credentials/endpointCA secret-ref NAME+key only — never values);
  - CNPG Cluster spec.plugins[] (name/isWALArchiver/parameters.barmanObjectName);
  - Calico policy scope + policy.networking.k8s.io discovery (bounded, no guess).

Two-phase: (1) bounded discovery of actually-served versions/resources; (2)
conditional projections only after discovered identity matches the reviewed
contract; otherwise STOP/UNKNOWN. Never reads Secret resources or ConfigMaps.
"""
import argparse
import datetime
import json
from pathlib import Path
import shutil
import subprocess
import sys
from urllib.parse import urlsplit

# --- URL + typed helpers (same safety contract as base inventory.py) -------------

def origin_only(v):
    if v is None or not isinstance(v, str):
        return None
    try:
        p = urlsplit(v)
        scheme = (p.scheme or '').lower()
        if scheme not in ('http', 'https', 's3', 'tcp', 'udp'):
            return None
        host = p.hostname or ''
        if not host or any(ord(c) < 0x21 or ord(c) == 0x7f for c in host):
            return None
        if ':' in host:
            host = f"[{host}]"
        if p.port is not None:
            host = f"{host}:{p.port}"
        return f"{scheme}://{host}"
    except (ValueError, TypeError):
        return None


def _dict(v, field):
    if v is None:
        return {}
    if not isinstance(v, dict):
        raise ValueError(field + ' not an object')
    return v


def _str(v, field, allow_none=False):
    if v is None:
        if allow_none:
            return None
        raise ValueError(field + ' required')
    if not isinstance(v, str):
        raise ValueError(field + ' not a string')
    return v


def _bool(v, field, allow_none=False):
    if v is None:
        if allow_none:
            return None
        raise ValueError(field + ' required')
    if not isinstance(v, bool):
        raise ValueError(field + ' not a boolean')
    return v


def _secret_ref(v, field):
    """Secret reference: NAME (+key) only, never value/data."""
    d = _dict(v, field)
    return {'name': _str(d.get('name'), field + '.name'), 'key': _str(d.get('key'), field + '.key', allow_none=True)}


def _require_kind(obj, expected):
    k = obj.get('kind')
    if k != expected:
        raise ValueError(f'kind {k!r} != {expected}')


def _meta(obj, namespaced=True):
    md = _dict(obj.get('metadata'), 'metadata')
    name = _str(md.get('name'), 'metadata.name')
    if not name:
        raise ValueError('metadata.name empty')
    ns = md.get('namespace')
    if namespaced:
        ns = _str(ns, 'metadata.namespace')
    elif ns is not None:
        ns = _str(ns, 'metadata.namespace')
    return {'name': name, 'namespace': ns, 'labels': {}}


# --- NEW projections (LI-01) ------------------------------------------------------

def project_objectstore_configuration(obj):
    """ObjectStore spec.configuration — the REAL field path (source: manifests/
    barman-cloud/v0.13.0/objectstore-portal-db.yaml)."""
    _require_kind(obj, 'ObjectStore')
    spec = _dict(obj.get('spec'), 'spec')
    cfg = _dict(spec.get('configuration'), 'spec.configuration')
    s3 = _dict(cfg.get('s3Credentials'), 'spec.configuration.s3Credentials')
    endpoint_ca = _dict(cfg.get('endpointCA'), 'spec.configuration.endpointCA')
    return {'kind': 'ObjectStore', 'metadata': _meta(obj), 'spec': {'configuration': {
        'endpointURL': origin_only(cfg.get('endpointURL')),
        'destinationPath': origin_only(cfg.get('destinationPath')),
        'endpointCAName': _str(endpoint_ca.get('name'), 'endpointCA.name', allow_none=True),
        's3AccessKeyIdRef': _secret_ref(s3.get('accessKeyId'), 'accessKeyId') if s3.get('accessKeyId') else None,
        's3SecretAccessKeyRef': _secret_ref(s3.get('secretAccessKey'), 'secretAccessKey') if s3.get('secretAccessKey') else None,
        's3RegionRef': _secret_ref(s3.get('region'), 'region') if s3.get('region') else None,
    }}}


def project_cluster_plugins(obj):
    """CNPG Cluster spec.plugins[] — the REAL plugin mapping (source: manifests/
    cnpg/v1.30.1/portal-db-cluster.yaml)."""
    _require_kind(obj, 'Cluster')
    spec = _dict(obj.get('spec'), 'spec')
    plugins = spec.get('plugins')
    out_plugins = []
    if plugins is not None:
        if not isinstance(plugins, list):
            raise ValueError('spec.plugins not a list')
        for pl in plugins:
            if not isinstance(pl, dict):
                raise ValueError('plugin not an object')
            params = _dict(pl.get('parameters'), 'plugin.parameters')
            out_plugins.append({
                'name': _str(pl.get('name'), 'plugin.name'),
                'isWALArchiver': _bool(pl.get('isWALArchiver'), 'plugin.isWALArchiver', allow_none=True),
                'barmanObjectName': _str(params.get('barmanObjectName'), 'plugin.parameters.barmanObjectName', allow_none=True),
            })
    return {'kind': 'Cluster', 'metadata': _meta(obj), 'spec': {'plugins': out_plugins,
            'imageName': _str(spec.get('imageName'), 'spec.imageName', allow_none=True)}}


def project_policy_selector_only(obj, kind):
    """Calico / k8s-like policy: selector + rules only (no annotations/env)."""
    _require_kind(obj, kind)
    spec = _dict(obj.get('spec'), 'spec')
    return {'kind': kind, 'metadata': _meta(obj), 'spec': {
        'selector': spec.get('selector', {}),
        'order': spec.get('order'),
        'ingress': spec.get('ingress', []),
        'egress': spec.get('egress', []),
        'types': spec.get('types', []),
    }}


# --- read-contract (exact commands; NOT executed offline) ------------------------

# (phase, id, argv_tail, resource_key) — resource_key None = discovery (raw json).
READ_CONTRACT = [
    # Phase-1: bounded discovery of served versions/resources.
    ('discover', 'P2-D1', ['get', '--raw', '/apis/crd.projectcalico.org/v1'], 'calico_api'),
    ('discover', 'P2-D2', ['get', '--raw', '/apis/policy.networking.k8s.io/v1alpha2'], 'policy_api'),
    # Phase-2: conditional projections (only after D1/D2 identity matches contract).
    ('config', 'P2-C1', ['get', 'objectstores.barmancloud.cnpg.io', '-A', '-o', 'json'], 'objectstore_configuration'),
    ('config', 'P2-C2', ['get', 'clusters.postgresql.cnpg.io', '-A', '-o', 'json'], 'cluster_plugins'),
    ('config', 'P2-C3', ['get', 'networkpolicies.crd.projectcalico.org', '-A', '-o', 'json'], 'calico_np'),
    ('config', 'P2-C4', ['get', 'globalnetworkpolicies.crd.projectcalico.org', '-o', 'json'], 'calico_gnp'),
]

PROJECTORS = {
    'objectstore_configuration': project_objectstore_configuration,
    'cluster_plugins': project_cluster_plugins,
    'calico_np': lambda o: project_policy_selector_only(o, 'NetworkPolicy'),
    'calico_gnp': lambda o: project_policy_selector_only(o, 'GlobalNetworkPolicy'),
}


def project_list(resource_key, raw_json):
    data = json.loads(raw_json)
    if not isinstance(data, dict):
        raise ValueError('expected object')
    items = data.get('items')
    if not isinstance(items, list):
        raise ValueError('expected items list')
    proj = PROJECTORS[resource_key]
    return json.dumps([proj(it) for it in items if isinstance(it, dict)])


def classify(returncode, stderr, timed_out, parse_error=False):
    if parse_error:
        return 'PARSE_ERROR'
    if timed_out:
        return 'TIMEOUT'
    if returncode == 0:
        return None
    low = (stderr or '').lower()
    if 'forbidden' in low or 'unauthorized' in low:
        return 'FORBIDDEN'
    if 'could not find' in low or 'no matches for kind' in low or "doesn't have a resource" in low:
        return 'API_NOT_SERVED'
    if 'deadline' in low or 'timed out' in low or 'context deadline exceeded' in low:
        return 'TIMEOUT'
    if 'connection' in low or 'refused' in low or 'unable to connect' in low:
        return 'CONNECTION'
    return 'GET_FAILED'


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--context', required=True)
    p.add_argument('--output', required=True)
    args = p.parse_args()
    if not shutil.which('kubectl'):
        raise SystemExit('BLOCKED: kubectl unavailable')
    directory = Path(args.output)
    directory.mkdir(parents=True, exist_ok=False)
    failures = 0
    with (directory / 'supplemental.jsonl').open('x') as log:
        for phase, rid, argv_tail, resource_key in READ_CONTRACT:
            argv = ['kubectl', '--context', args.context, '--request-timeout=15s'] + argv_tail
            start = datetime.datetime.now(datetime.timezone.utc).isoformat()
            timed_out = parse_error = False
            result = None
            try:
                result = subprocess.run(argv, capture_output=True, text=True, timeout=20)
            except subprocess.TimeoutExpired:
                timed_out = True
            except OSError:
                pass
            output = ''
            if result is not None and result.returncode == 0:
                if phase == 'config':
                    try:
                        output = project_list(resource_key, result.stdout)
                    except (json.JSONDecodeError, ValueError, KeyError, TypeError):
                        parse_error = True
                else:
                    output = result.stdout  # discovery: raw group/resource listing (non-secret)
            category = classify(None if result is None else result.returncode,
                                '' if result is None else result.stderr, timed_out, parse_error)
            if category is not None:
                failures += 1
            log.write(json.dumps({'phase': phase, 'id': rid, 'start': start, 'argv': argv,
                                  'exit': None if result is None else result.returncode,
                                  'category': category, 'output': output,
                                  'end': datetime.datetime.now(datetime.timezone.utc).isoformat()}) + '\n')
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
