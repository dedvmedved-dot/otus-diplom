#!/usr/bin/env python3
"""P8C RV-02 — read-only inventory collector (allowlist-projected).

Issues ONLY fixed `kubectl get` / `--raw` discovery reads. Full objects are
projected to an explicit per-kind field allowlist (identity/labels/selectors/
ports/endpoints/conditions) — arbitrary spec/status fields, embedded pod
templates, env, inline config and credentials never enter evidence. URL facts
retain only scheme/host[:port]/path (userinfo/query/fragment removed).

Malformed or wrong-shape JSON fails closed (PARSE_ERROR, empty output, nonzero
exit) — no raw-body fallback. Errors are classified into safe categories.

Run in the authorized operator session:
  python3 portal/networkpolicy/inventory.py --context "<approved>" --output "<new-dir>"
"""
import argparse
import datetime
import json
from pathlib import Path
import shutil
import subprocess
import sys
from urllib.parse import urlsplit

# --- safe URL + field sanitizers ------------------------------------------------

def sanitize_url(v):
    """Keep scheme://host[:port]/path; drop userinfo, query, fragment."""
    if not isinstance(v, str):
        return v
    if not v.startswith(('http://', 'https://', 's3://', 'tcp://', 'udp://')):
        return v
    try:
        p = urlsplit(v)
        host = p.hostname or ''
        if p.port is not None:
            host = f"{host}:{p.port}"
        path = p.path or ''
        return f"{p.scheme}://{host}{path}"
    except ValueError:
        return v


def _meta(obj):
    md = obj.get('metadata') or {}
    return {
        'name': md.get('name'),
        'namespace': md.get('namespace'),
        'labels': {k: sanitize_url(v) for k, v in (md.get('labels') or {}).items()},
    }


def _conditions(status):
    conds = (status or {}).get('conditions') or []
    out = []
    for c in conds:
        if not isinstance(c, dict):
            continue
        out.append({'type': c.get('type'), 'status': c.get('status'), 'reason': c.get('reason')})
    return out


def _selector(sel):
    if not isinstance(sel, dict):
        return {}
    return {'matchLabels': sel.get('matchLabels') or {},
            'matchExpressions': sel.get('matchExpressions') or []}


def _peer(p):
    if not isinstance(p, dict):
        return {}
    out = {}
    if 'podSelector' in p:
        out['podSelector'] = _selector(p['podSelector'])
    if 'namespaceSelector' in p:
        out['namespaceSelector'] = _selector(p['namespaceSelector'])
    if 'ipBlock' in p:
        ib = p['ipBlock'] or {}
        out['ipBlock'] = {'cidr': ib.get('cidr'), 'except': ib.get('except') or []}
    return out


def _port(p):
    if not isinstance(p, dict):
        return {}
    return {'port': p.get('port'), 'protocol': p.get('protocol')}


def _rule(r):
    if not isinstance(r, dict):
        return {}
    out = {}
    if 'ports' in r:
        out['ports'] = [_port(x) for x in (r['ports'] or [])]
    if 'from' in r:
        out['from'] = [_peer(x) for x in (r['from'] or [])]
    if 'to' in r:
        out['to'] = [_peer(x) for x in (r['to'] or [])]
    return out


# --- per-kind projectors (explicit allowlists, no spec/status passthrough) -------

def project_networkpolicy(obj):
    spec = obj.get('spec') or {}
    return {'kind': 'NetworkPolicy', 'metadata': _meta(obj), 'spec': {
        'podSelector': _selector(spec.get('podSelector')),
        'policyTypes': spec.get('policyTypes') or [],
        'ingress': [_rule(x) for x in (spec.get('ingress') or [])],
        'egress': [_rule(x) for x in (spec.get('egress') or [])],
    }}


def project_gatewayclass(obj):
    spec = obj.get('spec') or {}
    return {'kind': 'GatewayClass', 'metadata': _meta(obj), 'spec': {
        'controllerName': spec.get('controllerName'),
    }}


def project_gateway(obj):
    spec = obj.get('spec') or {}
    listeners = []
    for l in (spec.get('listeners') or []):
        if not isinstance(l, dict):
            continue
        listeners.append({'name': l.get('name'), 'port': l.get('port'), 'protocol': l.get('protocol')})
    return {'kind': 'Gateway', 'metadata': _meta(obj), 'spec': {
        'gatewayClassName': spec.get('gatewayClassName'), 'listeners': listeners,
    }, 'status': {'conditions': _conditions(obj.get('status'))}}


def project_envoyproxy(obj):
    return {'kind': 'EnvoyProxy', 'metadata': _meta(obj),
            'status': {'conditions': _conditions(obj.get('status'))}}


def project_cnpg_cluster(obj):
    spec = obj.get('spec') or {}
    backup = (spec.get('backup') or {})
    barman = backup.get('barmanObjectStore') or {}
    return {'kind': 'Cluster', 'metadata': _meta(obj), 'spec': {
        'instances': spec.get('instances'),
        'storageSize': (spec.get('storage') or {}).get('size'),
        'walStorageSize': (spec.get('walStorage') or {}).get('size'),
        'barmanObjectStoreName': barman.get('name'),
        'monitoring': (spec.get('monitoring') or {}).get('enablePodMonitor'),
    }, 'status': {
        'phase': (obj.get('status') or {}).get('phase'),
        'readyInstances': (obj.get('status') or {}).get('readyInstances'),
        'conditions': _conditions(obj.get('status')),
    }}


def project_objectstore(obj):
    data = (obj.get('spec') or {}).get('data') or {}
    s3 = data.get('s3Credentials') or {}
    return {'kind': 'ObjectStore', 'metadata': _meta(obj), 'spec': {'data': {
        'destinationPath': data.get('destinationPath'),
        'endpointURL': sanitize_url(data.get('endpointURL')),
        'endpointCA': data.get('endpointCA') is not None,  # presence only, not content
        's3CredentialsName': s3.get('name'),
    }}}


FULL_OBJECT_PROJECTORS = {
    'networkpolicies.networking.k8s.io': project_networkpolicy,
    'gatewayclasses.gateway.networking.k8s.io': project_gatewayclass,
    'gateways.gateway.networking.k8s.io': project_gateway,
    'envoyproxies.gateway.envoyproxy.io': project_envoyproxy,
    'clusters.postgresql.cnpg.io': project_cnpg_cluster,
    'objectstores.barmancloud.cnpg.io': project_objectstore,
}


def project_list(resource, raw_json):
    """Parse a kubectl -o json list, validate shape, project each item."""
    data = json.loads(raw_json)  # raises JSONDecodeError -> PARSE_ERROR upstream
    if not isinstance(data, dict):
        raise ValueError('expected object, got ' + type(data).__name__)
    items = data.get('items')
    if items is None:
        # single object (non-list), still projectable
        items = [data]
    if not isinstance(items, list):
        raise ValueError('expected items list, got ' + type(items).__name__)
    projector = FULL_OBJECT_PROJECTORS[resource]
    projected = []
    for it in items:
        if not isinstance(it, dict):
            raise ValueError('item not an object')
        projected.append(projector(it))
    return json.dumps(projected)


# --- safe read-only commands -----------------------------------------------------

PODS = '{range .items[*]}{.metadata.namespace}{"\\t"}{.metadata.name}{"\\t"}{.metadata.labels}{"\\t"}{range .spec.containers[*]}{.name}{":"}{.ports}{";"}{end}{"\\n"}{end}'
SERVICES = '{range .items[*]}{.metadata.namespace}{"\\t"}{.metadata.name}{"\\t"}{.spec.clusterIP}{"\\t"}{.spec.selector}{"\\t"}{.spec.ports}{"\\n"}{end}'
ENDPOINTS = '{range .items[*]}{.metadata.namespace}{"\\t"}{.metadata.name}{"\\t"}{.metadata.labels}{"\\t"}{.ports}{"\\t"}{range .endpoints[*]}{.addresses}{":"}{.conditions}{":"}{.targetRef.kind}{"/"}{.targetRef.name}{";"}{end}{"\\n"}{end}'
NAMESPACES = '{range .items[*]}{.metadata.name}{"\\t"}{.metadata.labels}{"\\n"}{end}'
PODMONITOR = '{range .items[*]}{.metadata.namespace}{"\\t"}{.metadata.name}{"\\t"}{.spec.selector}{"\\t"}{.spec.namespaceSelector}{"\\t"}{range .spec.podMetricsEndpoints[*]}{.port}{":"}{.path}{";"}{end}{"\\n"}{end}'

# (resource, projectable?) — projectable resources are parsed + allowlist-projected.
FULL_OBJECT_RESOURCES = [
    ('networkpolicies.networking.k8s.io', '-A'),
    ('gatewayclasses.gateway.networking.k8s.io', ''),
    ('gateways.gateway.networking.k8s.io', '-A'),
    ('envoyproxies.gateway.envoyproxy.io', '-A'),
    ('clusters.postgresql.cnpg.io', '-A'),
    ('objectstores.barmancloud.cnpg.io', '-A'),
]

COMMANDS = []  # built below: list of (argv, resource-or-None)


def _build_commands():
    c = []
    c.append((['get', 'pods', '-A', '-o', 'jsonpath=' + PODS], None))
    c.append((['get', 'services', '-A', '-o', 'jsonpath=' + SERVICES], None))
    c.append((['get', 'endpointslices.discovery.k8s.io', '-A', '-o', 'jsonpath=' + ENDPOINTS], None))
    c.append((['get', 'namespaces', '-o', 'jsonpath=' + NAMESPACES], None))
    for res, scope in FULL_OBJECT_RESOURCES:
        argv = ['get', res]
        if scope:
            argv.append(scope)
        argv += ['-o', 'json']
        c.append((argv, res))
    c.append((['get', 'servicemonitors.monitoring.coreos.com', '-A', '-o',
               'jsonpath={range .items[*]}{.metadata.namespace}{"\\t"}{.metadata.name}{"\\t"}{.spec.selector}{"\\t"}{.spec.namespaceSelector}{"\\t"}{range .spec.endpoints[*]}{.port}{";"}{end}{"\\n"}{end}'], None))
    c.append((['get', 'podmonitors.monitoring.coreos.com', '-A', '-o', 'jsonpath=' + PODMONITOR], None))
    c.append((['get', '--raw', '/apis/monitoring.coreos.com/v1'], None))
    c.append((['get', '--raw', '/apis'], None))
    # Nodes projected for CNI/annotations (non-secret, via jsonpath).
    c.append((['get', 'nodes', '-o',
               'jsonpath={range .items[*]}{.metadata.name}{"\\t"}{.metadata.annotations}{"\\n"}{end}'], None))
    return c


COMMANDS = _build_commands()


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
    if 'connection' in low or 'refused' in low or 'unable to connect' in low or 'deadline' in low:
        return 'CONNECTION'
    return 'GET_FAILED'


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--context', required=True)
    p.add_argument('--output', required=True)
    args = p.parse_args()
    if not shutil.which('kubectl'):
        raise SystemExit('BLOCKED: kubectl unavailable; no platform reads executed')
    directory = Path(args.output)
    directory.mkdir(parents=True, exist_ok=False)
    failures = 0
    with (directory / 'inventory.jsonl').open('x') as log:
        for argv_tail, resource in COMMANDS:
            argv = ['kubectl', '--context', args.context, '--request-timeout=15s'] + argv_tail
            start = datetime.datetime.now(datetime.timezone.utc).isoformat()
            timed_out = False
            parse_error = False
            result = None
            try:
                result = subprocess.run(argv, capture_output=True, text=True, timeout=20)
            except subprocess.TimeoutExpired:
                timed_out = True
            except OSError:
                pass
            category = None
            output = ''
            if result is not None and result.returncode == 0:
                if resource is not None:
                    try:
                        output = project_list(resource, result.stdout)
                    except (json.JSONDecodeError, ValueError, KeyError, TypeError):
                        parse_error = True
                else:
                    output = result.stdout
            category = classify(None if result is None else result.returncode,
                                '' if result is None else result.stderr,
                                timed_out, parse_error)
            if category is not None:
                failures += 1
            record = {
                'start': start,
                'argv': argv,
                'exit': None if result is None else result.returncode,
                'category': category,
                'output': output,
                'end': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            }
            log.write(json.dumps(record) + '\n')
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
