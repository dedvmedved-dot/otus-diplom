#!/usr/bin/env python3
"""P8C RV-02 Phase-2 — supplemental read-only collector (OFFLINE-ONLY, NOT approved to run).

PHASE2_LIVE_READS_APPROVED=NO; OWNER_PHASE2_HANDOFF_ALLOWED=NO.

Fixes SP-01..05 remainder:
  - discovery validates per-resource kind/scope/verbs; config reads gate on exact
    GVR+kind+scope+get/list; C5 requires felixconfigurations; D2 classifies policy
    kinds (unsupported -> UNSUPPORTED, no completeness claim).
  - typed leaves: serviceAccounts{names,selector}, container ports containerPort/name,
    policy tier/notSelector; protocol int-or-string.
  - pod identity: kind=Pod required, nonempty namespace, spec+status joined for imageID,
    malformed containers reject (no silent drop).
  - named reads bound to requested namespace/name; list-vs-single shape enforced.
  - Calico runtime identity read (I1) precedes version-specific Calico reads.
"""
import argparse
import datetime
import json
import re
from pathlib import Path
import shutil
import subprocess
import sys
from urllib.parse import urlsplit


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


def _port_val(v, field):
    if isinstance(v, bool) or not isinstance(v, (int, str)):
        raise ValueError(field + ' not int/string')
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


def _require(obj, kind, api):
    if obj.get('kind') != kind:
        raise ValueError(f"kind {obj.get('kind')!r} != {kind}")
    if obj.get('apiVersion') != api:
        raise ValueError(f"apiVersion {obj.get('apiVersion')!r} != {api}")


def _meta(obj, namespaced=True):
    md = _dict(obj.get('metadata'), 'metadata')
    name = _nonempty(md.get('name'), 'metadata.name')
    ns = md.get('namespace')
    if namespaced:
        ns = _nonempty(ns, 'metadata.namespace')
    elif ns is not None:
        ns = _str(ns, 'metadata.namespace')
    return {'name': name, 'namespace': ns}


# --- discovery ----------------------------------------------------------------

def project_discovery(raw):
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError('discovery not an object')
    if data.get('kind') != 'APIResourceList':
        raise ValueError('discovery kind != APIResourceList')
    gv = _nonempty(data.get('groupVersion'), 'groupVersion')
    res = data.get('resources')
    if not isinstance(res, list):
        raise ValueError('resources not a list')
    out = []
    for r in res:
        if not isinstance(r, dict):
            raise ValueError('resource not an object')
        out.append({'name': _str(r.get('name'), 'resource.name'),
                    'kind': _str(r.get('kind'), 'resource.kind'),
                    'namespaced': _bool(r.get('namespaced'), 'resource.namespaced'),
                    'verbs': _str_list(r.get('verbs'), 'resource.verbs')})
    return json.dumps({'kind': 'APIResourceList', 'groupVersion': gv, 'resources': out})


# --- projections --------------------------------------------------------------

def project_objectstore(obj, expect_name=None):
    _require(obj, 'ObjectStore', 'barmancloud.cnpg.io/v1')
    md = _meta(obj, namespaced=True)
    if md['namespace'] != 'portal':
        raise ValueError(f"objectstore namespace {md['namespace']!r} != portal")
    if expect_name is not None and md['name'] != expect_name:
        raise ValueError(f"objectstore name {md['name']!r} != {expect_name}")
    spec = _dict_req(obj.get('spec'), 'spec')
    cfg = _dict_req(spec.get('configuration'), 'spec.configuration')
    s3 = _dict(cfg.get('s3Credentials'), 'spec.configuration.s3Credentials')
    ca = _dict(cfg.get('endpointCA'), 'spec.configuration.endpointCA')
    def ref(v):
        if v is None:
            return None
        d = _dict_req(v, 's3Credentials')
        return {'name': _nonempty(d.get('name'), 'ref.name'), 'key': _str(d.get('key'), 'ref.key', allow_none=True)}
    return {'kind': 'ObjectStore', 'metadata': md, 'spec': {'configuration': {
        'endpointURL': origin_only(cfg.get('endpointURL')),
        'destinationPath': origin_only(cfg.get('destinationPath')),
        'endpointCAName': _str(ca.get('name'), 'endpointCA.name', allow_none=True),
        's3AccessKeyIdRef': ref(s3.get('accessKeyId')),
        's3SecretAccessKeyRef': ref(s3.get('secretAccessKey')),
        's3RegionRef': ref(s3.get('region'))}}}


def project_cluster(obj, expect_name=None):
    _require(obj, 'Cluster', 'postgresql.cnpg.io/v1')
    md = _meta(obj, namespaced=True)
    if md['namespace'] != 'portal':
        raise ValueError(f"cluster namespace {md['namespace']!r} != portal")
    if expect_name is not None and md['name'] != expect_name:
        raise ValueError(f"cluster name {md['name']!r} != {expect_name}")
    spec = _dict_req(obj.get('spec'), 'spec')
    plugins = spec.get('plugins')
    out = []
    if plugins is not None:
        if not isinstance(plugins, list):
            raise ValueError('plugins not a list')
        for pl in plugins:
            if not isinstance(pl, dict):
                raise ValueError('plugin not an object')
            params = _dict(pl.get('parameters'), 'plugin.parameters')
            out.append({'name': _str(pl.get('name'), 'plugin.name'),
                        'isWALArchiver': _bool(pl.get('isWALArchiver'), 'plugin.isWALArchiver', allow_none=True),
                        'barmanObjectName': _str(params.get('barmanObjectName'), 'barmanObjectName', allow_none=True)})
    return {'kind': 'Cluster', 'metadata': md, 'spec': {
        'plugins': out, 'imageName': _str(spec.get('imageName'), 'imageName', allow_none=True)}}


def _ports_typed(v, field):
    if v is None:
        return []
    if not isinstance(v, list):
        raise ValueError(field + ' not a list')
    return [_port_val(x, field) for x in v]


def _sa(v, field):
    if v is None:
        return None
    d = _dict_req(v, field)
    _check_keys(d, SA_ALLOWED, field)
    return {'names': _str_list(d.get('names'), field + '.names'),
            'selector': _str(d.get('selector'), field + '.selector', allow_none=True)}


def _services(v, field):
    if v is None:
        return None
    d = _dict_req(v, field)
    _check_keys(d, SERVICES_ALLOWED, field)
    return {'name': _str(d.get('name'), field + '.name', allow_none=True),
            'namespace': _str(d.get('namespace'), field + '.namespace', allow_none=True)}


def _policy_entity(e, field):
    e = _dict_req(e, field)
    _check_keys(e, ENTITY_ALLOWED, field)
    return {'selector': _str(e.get('selector'), field + '.selector', allow_none=True),
            'notSelector': _str(e.get('notSelector'), field + '.notSelector', allow_none=True),
            'namespaceSelector': _str(e.get('namespaceSelector'), field + '.namespaceSelector', allow_none=True),
            'nets': _str_list(e.get('nets'), field + '.nets'),
            'notNets': _str_list(e.get('notNets'), field + '.notNets'),
            'ports': _ports_typed(e.get('ports'), field + '.ports'),
            'notPorts': _ports_typed(e.get('notPorts'), field + '.notPorts'),
            'serviceAccounts': _sa(e.get('serviceAccounts'), field + '.serviceAccounts'),
            'services': _services(e.get('services'), field + '.services')}


def _proto(v, field):
    if v is None:
        return None
    if isinstance(v, bool):
        raise ValueError(field + ' not int/string')
    if isinstance(v, (int, str)):
        return v
    raise ValueError(field + ' not int/string')


def _ip_version(v, field):
    if v is None:
        return None
    if isinstance(v, bool) or not isinstance(v, int) or v not in (4, 6):
        raise ValueError(field + ' invalid (must be 4 or 6)')
    return v


def _int_range(v, field, lo, hi, allow_none=False):
    if v is None:
        if allow_none:
            return None
        raise ValueError(field + ' required')
    if isinstance(v, bool) or not isinstance(v, int) or not (lo <= v <= hi):
        raise ValueError(field + f' not in {lo}..{hi}')
    return v


def _icmp(v, field):
    if v is None:
        return None
    d = _dict_req(v, field)
    _check_keys(d, ICMP_ALLOWED, field)
    return {'type': _int_range(d.get('type'), field + '.type', 0, 254, allow_none=True),
            'code': _int_range(d.get('code'), field + '.code', 0, 255, allow_none=True)}


def _http(v, field):
    if v is None:
        return None
    d = _dict_req(v, field)
    _check_keys(d, HTTP_ALLOWED, field)
    paths = d.get('paths')
    if paths is None:
        paths = []
    if not isinstance(paths, list):
        raise ValueError(field + '.paths not a list')
    out_paths = []
    for p in paths:
        if not isinstance(p, dict):
            raise ValueError(field + '.paths item not object')
        _check_keys(p, HTTP_PATH_ALLOWED, field + '.paths')
        out_paths.append({'exact': _str(p.get('exact'), field + '.exact', allow_none=True),
                          'prefix': _str(p.get('prefix'), field + '.prefix', allow_none=True)})
    return {'methods': _str_list(d.get('methods'), field + '.methods'),
            'paths': out_paths}


def _policy_rule(r, field):
    r = _dict_req(r, field)
    _check_keys(r, RULE_ALLOWED, field)
    out = {'action': _enum(r.get('action'), field + '.action', ('Allow', 'Deny', 'Log', 'Pass'), allow_none=True),
           'protocol': _proto(r.get('protocol'), field + '.protocol'),
           'notProtocol': _proto(r.get('notProtocol'), field + '.notProtocol'),
           'ipVersion': _ip_version(r.get('ipVersion'), field + '.ipVersion'),
           'icmp': _icmp(r.get('icmp'), field + '.icmp'),
           'notICMP': _icmp(r.get('notICMP'), field + '.notICMP'),
           'http': _http(r.get('http'), field + '.http')}
    if 'source' in r:
        out['source'] = _policy_entity(r['source'], field + '.source')
    if 'destination' in r:
        out['destination'] = _policy_entity(r['destination'], field + '.destination')
    return out


def project_calico_policy(obj, kind, namespaced):
    _require(obj, kind, 'crd.projectcalico.org/v1')
    spec = _dict_req(obj.get('spec'), 'spec')
    _check_keys(spec, CALICO_SPEC_ALLOWED, 'spec')
    ingress = spec.get('ingress')
    egress = spec.get('egress')
    if ingress is not None and not isinstance(ingress, list):
        raise ValueError('ingress not a list')
    if egress is not None and not isinstance(egress, list):
        raise ValueError('egress not a list')
    out = {'kind': kind, 'metadata': _meta(obj, namespaced=namespaced), 'spec': {
        'order': _num(spec.get('order'), 'order', allow_none=True),
        'tier': _str(spec.get('tier'), 'tier', allow_none=True),
        'selector': _str(spec.get('selector'), 'selector', allow_none=True),
        'serviceAccountSelector': _str(spec.get('serviceAccountSelector'), 'serviceAccountSelector', allow_none=True),
        'types': _str_list(spec.get('types'), 'types'),
        'ingress': [_policy_rule(x, 'ingress') for x in (ingress or [])],
        'egress': [_policy_rule(x, 'egress') for x in (egress or [])],
    }}
    if not namespaced:
        for f in ('applyOnForward', 'doNotTrack', 'preDNAT'):
            out['spec'][f] = _bool(spec.get(f), f, allow_none=True)
        out['spec']['namespaceSelector'] = _str(spec.get('namespaceSelector'), 'namespaceSelector', allow_none=True)
    return out


def project_felix(obj):
    _require(obj, 'FelixConfiguration', 'crd.projectcalico.org/v1')
    md = _meta(obj, namespaced=False)
    if md['name'] != 'default':
        raise ValueError(f"felix name {md['name']!r} != default")
    spec = _dict_req(obj.get('spec'), 'spec')
    return {'kind': 'FelixConfiguration', 'metadata': _meta(obj, namespaced=False), 'spec': {
        'bpfEnabled': _bool(spec.get('bpfEnabled'), 'bpfEnabled', allow_none=True),
        'nftablesMode': _enum(spec.get('nftablesMode'), 'nftablesMode', ('Disabled', 'Enabled', 'Auto'), allow_none=True),
        'iptablesBackend': _str(spec.get('iptablesBackend'), 'iptablesBackend', allow_none=True),
        'nodeSelector': _str(spec.get('nodeSelector'), 'nodeSelector', allow_none=True)}}


def _container_ports(v, field):
    if v is None:
        return []
    if not isinstance(v, list):
        raise ValueError(field + ' not a list')
    out = []
    for p in v:
        if not isinstance(p, dict):
            raise ValueError(field + ' port not an object')
        cp = p.get('containerPort')
        if isinstance(cp, bool) or not isinstance(cp, int) or not (1 <= cp <= 65535):
            raise ValueError(field + '.containerPort not in 1..65535')
        out.append({'containerPort': cp,
                    'name': _str(p.get('name'), field + '.name', allow_none=True)})
    return out


def project_pod_identity(obj, expect_ns=None):
    _require(obj, 'Pod', 'v1')
    md = _meta(obj, namespaced=True)
    if expect_ns is not None and md['namespace'] != expect_ns:
        raise ValueError(f"pod namespace {md['namespace']!r} != {expect_ns}")
    spec = _dict_req(obj.get('spec'), 'spec')
    status = _dict(obj.get('status'), 'status')
    status_by = {}
    for cat in ('containerStatuses', 'initContainerStatuses'):
        v = status.get(cat)
        if v is None:
            continue
        if not isinstance(v, list):
            raise ValueError(cat + ' not a list')
        for s in v:
            if not isinstance(s, dict):
                raise ValueError(cat + ' item not an object')
            if isinstance(s.get('name'), str):
                status_by[(cat, s['name'])] = s.get('imageID')
    def cs(k, cat):
        v = spec.get(k)
        if v is None:
            return []
        if not isinstance(v, list):
            raise ValueError(k + ' not a list')
        out = []
        for c in v:
            if not isinstance(c, dict):
                raise ValueError(k + ' item not an object')
            name = _nonempty(c.get('name'), k + '.name')
            out.append({'name': name,
                        'image': _str(c.get('image'), k + '.image', allow_none=True),
                        'imageID': _str(status_by.get((cat, name)), k + '.imageID', allow_none=True),
                        'ports': _container_ports(c.get('ports'), k + '.ports'),
                        'restartPolicy': _str(c.get('restartPolicy'), k + '.restartPolicy', allow_none=True)})
        return out
    return {'metadata': md,
            'initContainers': cs('initContainers', 'initContainerStatuses'),
            'containers': cs('containers', 'containerStatuses')}


# --- read contract ------------------------------------------------------------

# (id, phase, argv_tail, resource_key, deps, shape, expect_name)
# shape: 'list' or 'single'
READ_CONTRACT = [
    ('D1', 'discover', ['get', '--raw', '/apis/crd.projectcalico.org/v1'], 'calico', [], 'single', None),
    ('D2', 'discover', ['get', '--raw', '/apis/policy.networking.k8s.io/v1alpha2'], 'policy', [], 'single', None),
    ('I1', 'config', ['get', 'pods', '-n', 'kube-system', '-l', 'k8s-app=calico-node', '-o', 'json'], 'identity', [], 'list', None),
    ('C1', 'config', ['get', 'objectstores.barmancloud.cnpg.io', '-n', 'portal', 'portal-db-backup', '-o', 'json'], 'objectstore', [], 'single', 'portal-db-backup'),
    ('C2', 'config', ['get', 'clusters.postgresql.cnpg.io', '-n', 'portal', 'portal-db', '-o', 'json'], 'cluster', [], 'single', 'portal-db'),
    ('C3', 'config', ['get', 'networkpolicies.crd.projectcalico.org', '-A', '-o', 'json'], 'calico_np', ['D1', 'I1'], 'list', None),
    ('C4', 'config', ['get', 'globalnetworkpolicies.crd.projectcalico.org', '-o', 'json'], 'calico_gnp', ['D1', 'I1'], 'list', None),
    ('C5', 'config', ['get', 'felixconfigurations.crd.projectcalico.org', 'default', '-o', 'json'], 'felix', ['D1', 'I1'], 'single', 'default'),
    ('S1', 'config', ['get', 'pods', '-n', 'portal', '-l', 'cnpg.io/cluster=portal-db', '-o', 'json'], 'sidecar', [], 'list', None),
    ('S2', 'config', ['get', 'pods', '-n', 'cnpg-system', '-l', 'app=barman-cloud', '-o', 'json'], 'plugin', [], 'list', None),
]

DISCOVERY_EXPECT = {
    'calico': ('crd.projectcalico.org/v1', {
        'networkpolicies': ('NetworkPolicy', True, ['get', 'list']),
        'globalnetworkpolicies': ('GlobalNetworkPolicy', False, ['get', 'list']),
        'felixconfigurations': ('FelixConfiguration', False, ['get']),
    }),
    'policy': ('policy.networking.k8s.io/v1alpha2', {}),
}

SUPPORTED_POLICY_KINDS = set()  # no policy.networking.k8s.io kinds are reviewed yet

NS_EXPECT = {'identity': 'kube-system', 'sidecar': 'portal', 'plugin': 'cnpg-system'}

# Finite Calico semantic-field contract: any key outside these allowlists at a
# semantic nesting level raises UnsupportedField (UNSUPPORTED), never silent loss.
CALICO_SPEC_ALLOWED = {'order', 'tier', 'selector', 'serviceAccountSelector', 'types', 'ingress', 'egress',
                       'applyOnForward', 'doNotTrack', 'preDNAT', 'namespaceSelector', 'performanceHints'}
RULE_ALLOWED = {'action', 'protocol', 'notProtocol', 'ipVersion', 'icmp', 'notICMP', 'http',
                'source', 'destination', 'metadata'}
ENTITY_ALLOWED = {'selector', 'notSelector', 'namespaceSelector', 'nets', 'notNets', 'ports',
                  'notPorts', 'serviceAccounts', 'services'}
HTTP_ALLOWED = {'methods', 'paths'}
HTTP_PATH_ALLOWED = {'exact', 'prefix'}
ICMP_ALLOWED = {'type', 'code'}
SA_ALLOWED = {'names', 'selector'}
SERVICES_ALLOWED = {'name', 'namespace'}

# Calico runtime identity: exact finite contract grounded in the repository pin
# ansible/playbooks/files/calico-v3.32.0.yaml — the daemonset image is
# quay.io/calico/node@sha256:f4fafd8... (digest ref) or the same-image tag v3.32.0.
# A runtime imageID must be a valid containerd/docker digest AND resolve to the
# pinned manifest digest (textual equality). Platform-child digests of a
# multi-platform manifest are NOT accepted without an explicit reviewed
# relationship — a syntactically valid but unbound digest is not identity proof.
PINNED_DIGEST = 'sha256:f4fafd8ba641d96c5a91b01e5a519117d77d55dee789a3562ba3ad4aa125b36a'
CALICO_IMAGE_REFS = {
    'quay.io/calico/node@' + PINNED_DIGEST,
    'quay.io/calico/node:v3.32.0',
}
IMAGE_ID_RE = re.compile(r'^(containerd|docker-pullable|docker)://sha256:[0-9a-f]{64}$')


class UnsupportedDiscovery(Exception):
    def __init__(self, kinds):
        self.kinds = kinds


class UnsupportedField(Exception):
    def __init__(self, level, keys):
        self.level = level
        self.keys = keys


def _check_keys(d, allowed, level):
    unknown = [k for k in d if k not in allowed]
    if unknown:
        raise UnsupportedField(level, sorted(unknown))


def verify_calico_identity(pods):
    if not pods:
        raise ValueError('no calico-node pods')
    for pod in pods:
        containers = pod.get('containers', [])
        calico = [c for c in containers
                  if 'calico-node' in (c.get('name') or '') or 'calico/node' in (c.get('image') or '')]
        if not calico:
            raise ValueError('pod without calico-node identity')
        for c in calico:
            image = c.get('image')
            if image not in CALICO_IMAGE_REFS:
                raise ValueError(f'unsupported calico image {image!r}')
            iid = c.get('imageID')
            if not iid or not IMAGE_ID_RE.match(iid):
                raise ValueError(f'invalid imageID {iid!r}')
            if not iid.endswith(PINNED_DIGEST):
                raise ValueError('imageID digest not linked to pinned image')
    return len(pods)

PROJECTORS = {
    'identity': project_pod_identity,
    'objectstore': project_objectstore,
    'cluster': project_cluster,
    'calico_np': lambda o: project_calico_policy(o, 'NetworkPolicy', namespaced=True),
    'calico_gnp': lambda o: project_calico_policy(o, 'GlobalNetworkPolicy', namespaced=False),
    'felix': project_felix,
    'sidecar': project_pod_identity,
    'plugin': project_pod_identity,
}


def _single(raw):
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError('expected single object')
    return data


def _list(raw):
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError('expected object')
    items = data.get('items')
    if not isinstance(items, list):
        raise ValueError('items not a list')
    return items


def project_config(resource_key, raw, shape, expect_name):
    if shape == 'single':
        items = [_single(raw)]
    else:
        items = _list(raw)
    proj = PROJECTORS[resource_key]
    expect_ns = NS_EXPECT.get(resource_key)
    out = []
    for it in items:
        if not isinstance(it, dict):
            raise ValueError('item not an object')
        if resource_key == 'objectstore':
            out.append(project_objectstore(it, expect_name))
        elif resource_key == 'cluster':
            out.append(project_cluster(it, expect_name))
        elif resource_key in ('identity', 'sidecar', 'plugin'):
            out.append(project_pod_identity(it, expect_ns))
        else:
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
    ok_ids = set()
    discovery = {}  # resource_key -> parsed discovery dict
    with (directory / 'supplemental.jsonl').open('x') as log:
        for rid, phase, argv_tail, resource_key, deps, shape, expect_name in READ_CONTRACT:
            unmet = [d for d in deps if d not in ok_ids]
            if unmet:
                log.write(json.dumps({'id': rid, 'phase': phase, 'start': None, 'argv': None, 'exit': None,
                                      'category': 'BLOCKED_NOT_EXECUTED', 'blocked_by': unmet, 'output': '',
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
            unsupported = False
            if ok:
                try:
                    if phase == 'discover':
                        output = project_discovery(result.stdout)
                        data = json.loads(output)
                        exp_gv, exp_res = DISCOVERY_EXPECT[resource_key]
                        if data['groupVersion'] != exp_gv:
                            raise ValueError(f"groupVersion {data['groupVersion']} != {exp_gv}")
                        res_by_name = {r['name']: r for r in data['resources']}
                        for rname, (kind, namespaced, verbs) in exp_res.items():
                            if rname not in res_by_name:
                                raise ValueError(f'discovery missing resource {rname}')
                            rr = res_by_name[rname]
                            if rr['kind'] != kind:
                                raise ValueError(f"resource {rname} kind {rr['kind']} != {kind}")
                            if rr['namespaced'] != namespaced:
                                raise ValueError(f"resource {rname} scope mismatch")
                            for v in verbs:
                                if v not in rr['verbs']:
                                    raise ValueError(f"resource {rname} missing verb {v}")
                        if resource_key == 'policy':
                            kinds = {r['kind'] for r in data['resources'] if r.get('kind')}
                            unsup = kinds - SUPPORTED_POLICY_KINDS
                            if unsup:
                                raise UnsupportedDiscovery(sorted(unsup))
                        discovery[resource_key] = data
                    else:
                        output = project_config(resource_key, result.stdout, shape, expect_name)
                        if resource_key == 'identity':
                            verify_calico_identity(json.loads(output))
                except UnsupportedDiscovery:
                    unsupported = True
                except UnsupportedField:
                    unsupported = True
                except (json.JSONDecodeError, ValueError, KeyError, TypeError):
                    parse_error = True
                    output = ''
            if unsupported:
                category = 'UNSUPPORTED'
            else:
                category = classify(None if result is None else result.returncode,
                                    '' if result is None else result.stderr, timed_out, parse_error)
            if category is not None:
                failures += 1
            else:
                ok_ids.add(rid)
            log.write(json.dumps({'id': rid, 'phase': phase, 'start': start, 'argv': argv,
                                  'exit': None if result is None else result.returncode,
                                  'category': category, 'output': output,
                                  'end': datetime.datetime.now(datetime.timezone.utc).isoformat()}) + '\n')
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
