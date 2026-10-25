#!/usr/bin/env python3
"""P8C RV-02 — read-only inventory collector (allowlist + typed-output contract).

Issues ONLY fixed `kubectl get` / `--raw` discovery reads. Full objects are
projected to an explicit per-kind field allowlist; every exported leaf is
type-validated (strings, ints, bools, enums, string maps/lists). Arbitrary or
malformed spec/status fields, pod templates, env, inline config and credentials
never enter evidence. URL fields are strict: origin-only, invalid scheme/type/
authority/port is omitted (None), never the raw value.

Malformed or wrong-shape JSON fails closed (PARSE_ERROR, empty output, nonzero
exit). kind must match the resource and must be present.

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

# --- strict URL sanitizer --------------------------------------------------------

def sanitize_url(v):
    """Strict URL-field sanitizer. Returns origin-only scheme://host[:port] with
    IPv6 brackets preserved, or None for unsupported scheme / non-string / bad
    authority / bad port / whitespace/control in host. Never returns raw value;
    path/query/fragment and userinfo are always dropped."""
    if v is None:
        return None
    if not isinstance(v, str):
        return None
    try:
        p = urlsplit(v)
        scheme = (p.scheme or '').lower()
        if scheme not in ('http', 'https', 's3', 'tcp', 'udp'):
            return None
        host = p.hostname or ''
        if not host:
            return None
        if any(ord(c) < 0x21 or ord(c) == 0x7f for c in host):
            return None  # whitespace / control character in authority
        if ':' in host:
            host = f"[{host}]"
        if p.port is not None:
            host = f"{host}:{p.port}"
        return f"{scheme}://{host}"
    except (ValueError, TypeError):
        return None


# --- typed primitive helpers ------------------------------------------------------

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


def _int(v, field, allow_none=False, lo=None, hi=None):
    if v is None:
        if allow_none:
            return None
        raise ValueError(field + ' required')
    if isinstance(v, bool) or not isinstance(v, int):
        raise ValueError(field + ' not an integer')
    if lo is not None and v < lo:
        raise ValueError(field + ' out of range')
    if hi is not None and v > hi:
        raise ValueError(field + ' out of range')
    return v


def _bool(v, field, allow_none=False):
    if v is None:
        if allow_none:
            return None
        raise ValueError(field + ' required')
    if not isinstance(v, bool):
        raise ValueError(field + ' not a boolean')
    return v


def _str_map(v, field, allow_none=True):
    if v is None:
        return {} if allow_none else _str(None, field)
    m = _dict(v, field)
    out = {}
    for k, val in m.items():
        if not isinstance(val, str):
            raise ValueError(field + ' value not a string')
        out[k] = val
    return out


def _str_list(v, field):
    if v is None:
        return []
    if not isinstance(v, list):
        raise ValueError(field + ' not a list')
    for x in v:
        if not isinstance(x, str):
            raise ValueError(field + ' item not a string')
    return v


def _enum(v, field, allowed):
    if v is None:
        return None
    if not isinstance(v, str) or v not in allowed:
        raise ValueError(field + ' invalid enum value')
    return v


def _require_kind(obj, expected):
    k = obj.get('kind')
    if k != expected:
        raise ValueError(f'kind {k!r} does not match resource {expected}')


def _meta(obj):
    md = _dict(obj.get('metadata'), 'metadata')
    name = _str(md.get('name'), 'metadata.name')
    ns = md.get('namespace')
    if ns is not None:
        ns = _str(ns, 'metadata.namespace')
    labels = _str_map(md.get('labels'), 'metadata.labels')
    return {'name': name, 'namespace': ns, 'labels': labels}


def _conditions(status):
    conds = _dict(status, 'status').get('conditions')
    if conds is None:
        return []
    if not isinstance(conds, list):
        raise ValueError('status.conditions not a list')
    out = []
    for c in conds:
        if not isinstance(c, dict):
            raise ValueError('condition not an object')
        out.append({
            'type': _str(c.get('type'), 'condition.type'),
            'status': _enum(c.get('status'), 'condition.status', ('True', 'False', 'Unknown')),
            'reason': _str(c.get('reason'), 'condition.reason', allow_none=True),
        })
    return out


def _selector(sel):
    sel = _dict(sel, 'selector')
    me = sel.get('matchExpressions')
    match_expressions = []
    if me is not None:
        if not isinstance(me, list):
            raise ValueError('matchExpressions not a list')
        for e in me:
            if not isinstance(e, dict):
                raise ValueError('matchExpression not an object')
            match_expressions.append({
                'key': _str(e.get('key'), 'matchExpression.key'),
                'operator': _enum(e.get('operator'), 'matchExpression.operator',
                                  ('In', 'NotIn', 'Exists', 'DoesNotExist')),
                'values': _str_list(e.get('values'), 'matchExpression.values'),
            })
    return {'matchLabels': _str_map(sel.get('matchLabels'), 'matchLabels'),
            'matchExpressions': match_expressions}


def _peer(p):
    p = _dict(p, 'peer')
    out = {}
    if 'podSelector' in p:
        out['podSelector'] = _selector(p['podSelector'])
    if 'namespaceSelector' in p:
        out['namespaceSelector'] = _selector(p['namespaceSelector'])
    if 'ipBlock' in p:
        ib = _dict(p['ipBlock'], 'ipBlock')
        out['ipBlock'] = {
            'cidr': _str(ib.get('cidr'), 'ipBlock.cidr'),
            'except': _str_list(ib.get('except'), 'ipBlock.except'),
        }
    return out


def _port_value(v, field):
    if isinstance(v, bool):
        raise ValueError(field + ' not an integer or named string')
    if isinstance(v, int):
        return _int(v, field, lo=1, hi=65535)
    if isinstance(v, str):
        return v
    raise ValueError(field + ' not an integer or named string')


def _port(p):
    p = _dict(p, 'port')
    port = p.get('port')
    if port is not None:
        port = _port_value(port, 'port')
    protocol = _enum(p.get('protocol'), 'protocol', ('TCP', 'UDP', 'SCTP'))
    ep = p.get('endPort')
    if ep is not None:
        ep = _int(ep, 'endPort', lo=1, hi=65535)
        if isinstance(port, int) and ep < port:
            raise ValueError('endPort < port')
    out = {'port': port, 'protocol': protocol}
    if ep is not None:
        out['endPort'] = ep
    return out


def _rule(r):
    r = _dict(r, 'rule')
    out = {}
    if 'ports' in r:
        ports = r['ports']
        if not isinstance(ports, list):
            raise ValueError('rule.ports not a list')
        out['ports'] = [_port(x) for x in ports]
    if 'from' in r:
        if not isinstance(r['from'], list):
            raise ValueError('rule.from not a list')
        out['from'] = [_peer(x) for x in r['from']]
    if 'to' in r:
        if not isinstance(r['to'], list):
            raise ValueError('rule.to not a list')
        out['to'] = [_peer(x) for x in r['to']]
    return out


# --- per-kind projectors (explicit allowlists + typed leaves) ---------------------

def project_networkpolicy(obj):
    _require_kind(obj, 'NetworkPolicy')
    spec = _dict(obj.get('spec'), 'spec')
    pt = spec.get('policyTypes')
    if pt is not None:
        pt = _str_list(pt, 'policyTypes')
        for t in pt:
            _enum(t, 'policyTypes item', ('Ingress', 'Egress'))
    return {'kind': 'NetworkPolicy', 'metadata': _meta(obj), 'spec': {
        'podSelector': _selector(spec.get('podSelector')),
        'policyTypes': pt or [],
        'ingress': [_rule(x) for x in (spec.get('ingress') or [])],
        'egress': [_rule(x) for x in (spec.get('egress') or [])],
    }}


def project_gatewayclass(obj):
    _require_kind(obj, 'GatewayClass')
    spec = _dict(obj.get('spec'), 'spec')
    return {'kind': 'GatewayClass', 'metadata': _meta(obj), 'spec': {
        'controllerName': _str(spec.get('controllerName'), 'controllerName'),
    }}


def project_gateway(obj):
    _require_kind(obj, 'Gateway')
    spec = _dict(obj.get('spec'), 'spec')
    listeners = []
    for l in (spec.get('listeners') or []):
        if not isinstance(l, dict):
            raise ValueError('listener not an object')
        listeners.append({
            'name': _str(l.get('name'), 'listener.name'),
            'port': _int(l.get('port'), 'listener.port', lo=1, hi=65535),
            'protocol': _str(l.get('protocol'), 'listener.protocol'),
        })
    return {'kind': 'Gateway', 'metadata': _meta(obj), 'spec': {
        'gatewayClassName': _str(spec.get('gatewayClassName'), 'gatewayClassName'),
        'listeners': listeners,
    }, 'status': {'conditions': _conditions(obj.get('status'))}}


def project_envoyproxy(obj):
    _require_kind(obj, 'EnvoyProxy')
    return {'kind': 'EnvoyProxy', 'metadata': _meta(obj),
            'status': {'conditions': _conditions(obj.get('status'))}}


def project_cnpg_cluster(obj):
    _require_kind(obj, 'Cluster')
    spec = _dict(obj.get('spec'), 'spec')
    backup = _dict(spec.get('backup'), 'spec.backup')
    barman = _dict(backup.get('barmanObjectStore'), 'spec.backup.barmanObjectStore')
    monitoring = _dict(spec.get('monitoring'), 'spec.monitoring')
    storage = _dict(spec.get('storage'), 'spec.storage')
    wal_storage = _dict(spec.get('walStorage'), 'spec.walStorage')
    status = _dict(obj.get('status'), 'status')
    return {'kind': 'Cluster', 'metadata': _meta(obj), 'spec': {
        'instances': _int(spec.get('instances'), 'instances', lo=1),
        'storageSize': _str(storage.get('size'), 'storage.size', allow_none=True),
        'walStorageSize': _str(wal_storage.get('size'), 'walStorage.size', allow_none=True),
        'barmanObjectStoreName': _str(barman.get('name'), 'barmanObjectStore.name', allow_none=True),
        'monitoring': _bool(monitoring.get('enablePodMonitor'), 'monitoring.enablePodMonitor', allow_none=True),
    }, 'status': {
        'phase': _str(status.get('phase'), 'status.phase', allow_none=True),
        'readyInstances': _int(status.get('readyInstances'), 'readyInstances', allow_none=True, lo=0),
        'conditions': _conditions(obj.get('status')),
    }}


def project_objectstore(obj):
    _require_kind(obj, 'ObjectStore')
    spec = _dict(obj.get('spec'), 'spec')
    data = _dict(spec.get('data'), 'spec.data')
    s3 = _dict(data.get('s3Credentials'), 'spec.data.s3Credentials')
    return {'kind': 'ObjectStore', 'metadata': _meta(obj), 'spec': {'data': {
        'destinationPath': sanitize_url(data.get('destinationPath')),
        'endpointURL': sanitize_url(data.get('endpointURL')),
        'endpointCA': data.get('endpointCA') is not None,  # presence only, not content
        's3CredentialsName': _str(s3.get('name'), 's3Credentials.name', allow_none=True),
    }}}


KIND_BY_RESOURCE = {
    'networkpolicies.networking.k8s.io': 'NetworkPolicy',
    'gatewayclasses.gateway.networking.k8s.io': 'GatewayClass',
    'gateways.gateway.networking.k8s.io': 'Gateway',
    'envoyproxies.gateway.envoyproxy.io': 'EnvoyProxy',
    'clusters.postgresql.cnpg.io': 'Cluster',
    'objectstores.barmancloud.cnpg.io': 'ObjectStore',
}

FULL_OBJECT_PROJECTORS = {
    'networkpolicies.networking.k8s.io': project_networkpolicy,
    'gatewayclasses.gateway.networking.k8s.io': project_gatewayclass,
    'gateways.gateway.networking.k8s.io': project_gateway,
    'envoyproxies.gateway.envoyproxy.io': project_envoyproxy,
    'clusters.postgresql.cnpg.io': project_cnpg_cluster,
    'objectstores.barmancloud.cnpg.io': project_objectstore,
}


def project_list(resource, raw_json):
    data = json.loads(raw_json)
    if not isinstance(data, dict):
        raise ValueError('expected object, got ' + type(data).__name__)
    items = data.get('items')
    if not isinstance(items, list):
        raise ValueError('expected items list, got ' + type(items).__name__)
    projector = FULL_OBJECT_PROJECTORS[resource]
    expected_kind = KIND_BY_RESOURCE[resource]
    projected = []
    for it in items:
        if not isinstance(it, dict):
            raise ValueError('item not an object')
        _require_kind(it, expected_kind)
        projected.append(projector(it))
    return json.dumps(projected)


# --- safe read-only commands -----------------------------------------------------

PODS = '{range .items[*]}{.metadata.namespace}{"\\t"}{.metadata.name}{"\\t"}{.metadata.labels}{"\\t"}{range .spec.containers[*]}{.name}{":"}{.ports}{";"}{end}{"\\n"}{end}'
SERVICES = '{range .items[*]}{.metadata.namespace}{"\\t"}{.metadata.name}{"\\t"}{.spec.clusterIP}{"\\t"}{.spec.selector}{"\\t"}{.spec.ports}{"\\n"}{end}'
ENDPOINTS = '{range .items[*]}{.metadata.namespace}{"\\t"}{.metadata.name}{"\\t"}{.metadata.labels}{"\\t"}{.ports}{"\\t"}{range .endpoints[*]}{.addresses}{":"}{.conditions}{":"}{.targetRef.kind}{"/"}{.targetRef.name}{";"}{end}{"\\n"}{end}'
NAMESPACES = '{range .items[*]}{.metadata.name}{"\\t"}{.metadata.labels}{"\\n"}{end}'
PODMONITOR = '{range .items[*]}{.metadata.namespace}{"\\t"}{.metadata.name}{"\\t"}{.spec.selector}{"\\t"}{.spec.namespaceSelector}{"\\t"}{range .spec.podMetricsEndpoints[*]}{.port}{":"}{.path}{";"}{end}{"\\n"}{end}'

FULL_OBJECT_RESOURCES = [
    ('networkpolicies.networking.k8s.io', '-A'),
    ('gatewayclasses.gateway.networking.k8s.io', ''),
    ('gateways.gateway.networking.k8s.io', '-A'),
    ('envoyproxies.gateway.envoyproxy.io', '-A'),
    ('clusters.postgresql.cnpg.io', '-A'),
    ('objectstores.barmancloud.cnpg.io', '-A'),
]


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
    # Nodes: name + addresses + podCIDRs only (NO annotations).
    c.append((['get', 'nodes', '-o',
               'jsonpath={range .items[*]}{.metadata.name}{"\\t"}{.status.addresses}{"\\t"}{.spec.podCIDRs}{"\\n"}{end}'], None))
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
