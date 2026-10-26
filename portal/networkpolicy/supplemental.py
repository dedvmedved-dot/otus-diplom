#!/usr/bin/env python3
"""P8C RV-02 Phase-2 — supplemental read-only collector (OFFLINE-ONLY, NOT approved to run).

PHASE2_LIVE_READS_APPROVED=NO; OWNER_PHASE2_HANDOFF_ALLOWED=NO.

Addresses SP-01..04. Key properties:
  - discovery is a GATE: a config read whose dependency discovery did not match
    the reviewed groupVersion/resources is NOT executed (BLOCKED_NOT_EXECUTED record).
  - discovery responses are validated + projected (kind/groupVersion/resources),
    never persisted raw; malformed/wrong-identity → safe error, dependent reads blocked.
  - per-kind apiVersion/kind/scope/identity contract; invalid list elements reject
    (not silently dropped); cluster-scoped GlobalNetworkPolicy omits namespace.
  - typed recursive policy projection (no arbitrary nested content); secret refs are
    name+key only; false/0/string/unknown members never collapse to null/empty.
"""
import argparse
import datetime
import json
from pathlib import Path
import shutil
import subprocess
import sys
from urllib.parse import urlsplit

# --- URL + typed helpers ---------------------------------------------------------

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


def _dict_req(v, field):
    if not isinstance(v, dict):
        raise ValueError(field + ' not an object (required)')
    return v


def _str(v, field, allow_none=False):
    if v is None:
        if allow_none:
            return None
        raise ValueError(field + ' required')
    if not isinstance(v, str):
        raise ValueError(field + ' not a string')
    return v


def _nonempty(v, field, allow_none=False):
    s = _str(v, field, allow_none=allow_none)
    if s is not None and s == '':
        raise ValueError(field + ' must be nonempty')
    return s


def _bool(v, field, allow_none=False):
    if v is None:
        if allow_none:
            return None
        raise ValueError(field + ' required')
    if not isinstance(v, bool):
        raise ValueError(field + ' not a boolean')
    return v


def _num(v, field, allow_none=False):
    if v is None:
        if allow_none:
            return None
        raise ValueError(field + ' required')
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise ValueError(field + ' not a number')
    return v


def _enum(v, field, allowed, allow_none=False):
    if v is None:
        if allow_none:
            return None
        raise ValueError(field + ' required')
    if not isinstance(v, str) or v not in allowed:
        raise ValueError(field + ' invalid enum')
    return v


def _str_list(v, field):
    if v is None:
        return []
    if not isinstance(v, list):
        raise ValueError(field + ' not a list')
    for x in v:
        if not isinstance(x, str):
            raise ValueError(field + ' item not a string')
    return v


def _secret_ref(v, field):
    d = _dict_req(v, field)
    return {'name': _nonempty(d.get('name'), field + '.name'),
            'key': _str(d.get('key'), field + '.key', allow_none=True)}


def _require_kind(obj, kind):
    if obj.get('kind') != kind:
        raise ValueError(f"kind {obj.get('kind')!r} != {kind}")


def _require_api(obj, api_version):
    if obj.get('apiVersion') != api_version:
        raise ValueError(f"apiVersion {obj.get('apiVersion')!r} != {api_version}")


def _meta(obj, namespaced=True):
    md = _dict(obj.get('metadata'), 'metadata')
    name = _nonempty(md.get('name'), 'metadata.name')
    ns = md.get('namespace')
    if namespaced:
        ns = _nonempty(ns, 'metadata.namespace')
    elif ns is not None:
        ns = _str(ns, 'metadata.namespace')
    return {'name': name, 'namespace': ns}


# --- Discovery projection/validation (SP-01) -------------------------------------

def project_discovery(raw):
    """Validate APIResourceList shape/kind/groupVersion/resources; typed output."""
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError('discovery not an object')
    if data.get('kind') != 'APIResourceList':
        raise ValueError(f"discovery kind {data.get('kind')!r}")
    gv = _str(data.get('groupVersion'), 'groupVersion')
    res = data.get('resources')
    if not isinstance(res, list):
        raise ValueError('resources not a list')
    out = []
    for r in res:
        if not isinstance(r, dict):
            raise ValueError('resource not an object')
        out.append({'name': _str(r.get('name'), 'resource.name'),
                    'namespaced': _bool(r.get('namespaced'), 'resource.namespaced', allow_none=True),
                    'verbs': _str_list(r.get('verbs'), 'resource.verbs')})
    return json.dumps({'kind': 'APIResourceList', 'groupVersion': gv, 'resources': out})


# --- ObjectStore / Cluster / policy / identity projections -----------------------

def project_objectstore(obj):
    _require_kind(obj, 'ObjectStore')
    _require_api(obj, 'barmancloud.cnpg.io/v1')
    spec = _dict_req(obj.get('spec'), 'spec')
    cfg = _dict_req(spec.get('configuration'), 'spec.configuration')
    s3 = _dict(cfg.get('s3Credentials'), 'spec.configuration.s3Credentials')
    ca = _dict(cfg.get('endpointCA'), 'spec.configuration.endpointCA')
    def ref_or_none(v):
        return _secret_ref(v, 's3Credentials') if v is not None else None
    return {'kind': 'ObjectStore', 'metadata': _meta(obj, namespaced=True), 'spec': {'configuration': {
        'endpointURL': origin_only(cfg.get('endpointURL')),
        'destinationPath': origin_only(cfg.get('destinationPath')),
        'endpointCAName': _str(ca.get('name'), 'endpointCA.name', allow_none=True),
        's3AccessKeyIdRef': ref_or_none(s3.get('accessKeyId')),
        's3SecretAccessKeyRef': ref_or_none(s3.get('secretAccessKey')),
        's3RegionRef': ref_or_none(s3.get('region')),
    }}}


def project_cluster(obj):
    _require_kind(obj, 'Cluster')
    _require_api(obj, 'postgresql.cnpg.io/v1')
    spec = _dict_req(obj.get('spec'), 'spec')
    plugins = spec.get('plugins')
    out = []
    if plugins is not None:
        if not isinstance(plugins, list):
            raise ValueError('spec.plugins not a list')
        for pl in plugins:
            if not isinstance(pl, dict):
                raise ValueError('plugin not an object')
            params = _dict(pl.get('parameters'), 'plugin.parameters')
            out.append({'name': _str(pl.get('name'), 'plugin.name'),
                        'isWALArchiver': _bool(pl.get('isWALArchiver'), 'plugin.isWALArchiver', allow_none=True),
                        'barmanObjectName': _str(params.get('barmanObjectName'), 'plugin.parameters.barmanObjectName', allow_none=True)})
    return {'kind': 'Cluster', 'metadata': _meta(obj, namespaced=True), 'spec': {
        'plugins': out, 'imageName': _str(spec.get('imageName'), 'spec.imageName', allow_none=True)}}


def _ports_typed(v, field):
    if v is None:
        return []
    if not isinstance(v, list):
        raise ValueError(field + ' not a list')
    out = []
    for x in v:
        if isinstance(x, bool) or not isinstance(x, (int, str)):
            raise ValueError(field + ' port not int/string')
        out.append(x)
    return out


def _policy_entity(e, field):
    e = _dict_req(e, field)
    return {'selector': _str(e.get('selector'), field + '.selector', allow_none=True),
            'namespaceSelector': _str(e.get('namespaceSelector'), field + '.namespaceSelector', allow_none=True),
            'nets': _str_list(e.get('nets'), field + '.nets'),
            'notNets': _str_list(e.get('notNets'), field + '.notNets'),
            'ports': _ports_typed(e.get('ports'), field + '.ports'),
            'notPorts': _ports_typed(e.get('notPorts'), field + '.notPorts'),
            'serviceAccounts': _dict(e.get('serviceAccounts'), field + '.serviceAccounts')}


def _policy_rule(r, field):
    r = _dict_req(r, field)
    out = {'action': _enum(r.get('action'), field + '.action', ('Allow', 'Deny', 'Log', 'Pass'), allow_none=True),
           'protocol': _str(r.get('protocol'), field + '.protocol', allow_none=True)}
    if 'source' in r:
        out['source'] = _policy_entity(r['source'], field + '.source')
    if 'destination' in r:
        out['destination'] = _policy_entity(r['destination'], field + '.destination')
    return out


def project_calico_policy(obj, kind, namespaced):
    _require_kind(obj, kind)
    _require_api(obj, 'crd.projectcalico.org/v1')
    spec = _dict_req(obj.get('spec'), 'spec')
    ingress = spec.get('ingress')
    egress = spec.get('egress')
    if ingress is not None and not isinstance(ingress, list):
        raise ValueError('ingress not a list')
    if egress is not None and not isinstance(egress, list):
        raise ValueError('egress not a list')
    out = {'kind': kind, 'metadata': _meta(obj, namespaced=namespaced), 'spec': {
        'order': _num(spec.get('order'), 'order', allow_none=True),
        'selector': _str(spec.get('selector'), 'selector', allow_none=True),
        'types': _str_list(spec.get('types'), 'types'),
        'ingress': [_policy_rule(x, 'ingress') for x in (ingress or [])],
        'egress': [_policy_rule(x, 'egress') for x in (egress or [])],
    }}
    # host effects only on GlobalNetworkPolicy (cluster scope)
    if not namespaced:
        for f in ('applyOnForward', 'doNotTrack', 'preDNAT'):
            out['spec'][f] = _bool(spec.get(f), f, allow_none=True)
    return out


def project_felix(obj):
    _require_kind(obj, 'FelixConfiguration')
    _require_api(obj, 'crd.projectcalico.org/v1')
    spec = _dict_req(obj.get('spec'), 'spec')
    return {'kind': 'FelixConfiguration', 'metadata': _meta(obj, namespaced=False),
            'spec': {'bpfEnabled': _bool(spec.get('bpfEnabled'), 'bpfEnabled', allow_none=True),
                     'dataplane': _str(spec.get('dataplane'), 'dataplane', allow_none=True),
                     'chainInsertMode': _str(spec.get('chainInsertMode'), 'chainInsertMode', allow_none=True)}}


def _container(c, field):
    c = _dict_req(c, field)
    ports = []
    for p in (c.get('ports') or []):
        if isinstance(p, dict):
            ports.append({'containerPort': p.get('containerPort'), 'name': p.get('name')})
    return {'name': _str(c.get('name'), field + '.name'),
            'image': _str(c.get('image'), field + '.image', allow_none=True),
            'imageID': _str(c.get('imageID'), field + '.imageID', allow_none=True),
            'ports': ports,
            'restartPolicy': _str(c.get('restartPolicy'), field + '.restartPolicy', allow_none=True)}


def project_pod_identity(obj):
    _require_api(obj, 'v1')
    md = _dict(obj.get('metadata'), 'metadata')
    spec = _dict_req(obj.get('spec'), 'spec')
    def cs(k):
        v = spec.get(k)
        if v is None:
            return []
        if not isinstance(v, list):
            raise ValueError(k + ' not a list')
        return [_container(x, k) for x in v if isinstance(x, dict)]
    return {'metadata': {'name': _str(md.get('name'), 'metadata.name'),
                         'namespace': _str(md.get('namespace'), 'metadata.namespace')},
            'initContainers': cs('initContainers'),
            'containers': cs('containers')}


# --- read contract (with explicit dependencies + reviewed versions) --------------

# (id, phase, argv_tail, resource_key, deps)
READ_CONTRACT = [
    ('D1', 'discover', ['get', '--raw', '/apis/crd.projectcalico.org/v1'], 'calico_discovery', []),
    ('D2', 'discover', ['get', '--raw', '/apis/policy.networking.k8s.io/v1alpha2'], 'policy_discovery', []),
    ('C1', 'config', ['get', 'objectstores.barmancloud.cnpg.io', '-n', 'portal', 'portal-db-backup', '-o', 'json'], 'objectstore', []),
    ('C2', 'config', ['get', 'clusters.postgresql.cnpg.io', '-n', 'portal', 'portal-db', '-o', 'json'], 'cluster', []),
    ('C3', 'config', ['get', 'networkpolicies.crd.projectcalico.org', '-A', '-o', 'json'], 'calico_np', ['D1']),
    ('C4', 'config', ['get', 'globalnetworkpolicies.crd.projectcalico.org', '-o', 'json'], 'calico_gnp', ['D1']),
    ('C5', 'config', ['get', 'felixconfigurations.crd.projectcalico.org', 'default', '-o', 'json'], 'felix', ['D1']),
    ('S1', 'config', ['get', 'pods', '-n', 'portal', '-l', 'cnpg.io/cluster=portal-db', '-o', 'json'], 'sidecar', []),
    ('S2', 'config', ['get', 'pods', '-n', 'cnpg-system', '-l', 'app=barman-cloud', '-o', 'json'], 'plugin', []),
]

DISCOVERY_EXPECT = {
    'calico_discovery': ('crd.projectcalico.org/v1', {'networkpolicies', 'globalnetworkpolicies'}),
    'policy_discovery': ('policy.networking.k8s.io/v1alpha2', set()),
}

PROJECTORS = {
    'objectstore': project_objectstore,
    'cluster': project_cluster,
    'calico_np': lambda o: project_calico_policy(o, 'NetworkPolicy', namespaced=True),
    'calico_gnp': lambda o: project_calico_policy(o, 'GlobalNetworkPolicy', namespaced=False),
    'felix': project_felix,
    'sidecar': project_pod_identity,
    'plugin': project_pod_identity,
}


def _items(raw):
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError('expected object')
    items = data.get('items')
    if items is None:
        # single object (get <name>) — still projectable
        return [data]
    if not isinstance(items, list):
        raise ValueError('items not a list')
    return items


def project_config(resource_key, raw):
    proj = PROJECTORS[resource_key]
    items = _items(raw)
    out = []
    for it in items:
        if not isinstance(it, dict):
            raise ValueError('item not an object')  # reject, never drop
        out.append(proj(it))
    return json.dumps(out)


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
    discovery_ok = set()
    with (directory / 'supplemental.jsonl').open('x') as log:
        for rid, phase, argv_tail, resource_key, deps in READ_CONTRACT:
            unmet = [d for d in deps if d not in discovery_ok]
            if unmet:
                # gated: do NOT call kubectl
                log.write(json.dumps({'id': rid, 'phase': phase, 'start': None, 'argv': None,
                                      'exit': None, 'category': 'BLOCKED_NOT_EXECUTED',
                                      'blocked_by': unmet, 'output': '',
                                      'end': datetime.datetime.now(datetime.timezone.utc).isoformat()}) + '\n')
                failures += 1
                continue
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
            ok = result is not None and result.returncode == 0
            if ok:
                try:
                    if phase == 'discover':
                        output = project_discovery(result.stdout)
                        exp_gv, exp_res = DISCOVERY_EXPECT[resource_key]
                        data = json.loads(output)
                        if data['groupVersion'] != exp_gv:
                            raise ValueError(f"discovery groupVersion {data['groupVersion']} != {exp_gv}")
                        names = {r['name'] for r in data['resources']}
                        missing = exp_res - names
                        if missing:
                            raise ValueError('discovery missing resources: ' + ','.join(sorted(missing)))
                    else:
                        output = project_config(resource_key, result.stdout)
                except (json.JSONDecodeError, ValueError, KeyError, TypeError):
                    parse_error = True
                    output = ''
            category = classify(None if result is None else result.returncode,
                                '' if result is None else result.stderr, timed_out, parse_error)
            if category is not None:
                failures += 1
            else:
                if phase == 'discover':
                    discovery_ok.add(rid)
            log.write(json.dumps({'id': rid, 'phase': phase, 'start': start, 'argv': argv,
                                  'exit': None if result is None else result.returncode,
                                  'category': category, 'output': output,
                                  'end': datetime.datetime.now(datetime.timezone.utc).isoformat()}) + '\n')
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
