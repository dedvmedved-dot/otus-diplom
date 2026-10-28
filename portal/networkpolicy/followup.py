#!/usr/bin/env python3
"""P8C-R1 RV-02 — bounded follow-up collector (F-D1..F-TIER).

Offline source design per portal/networkpolicy/followup-read-design.md (Architect
revision after bcda2f7). Reuses accepted pure projectors and the finite S1 identity
gate from supplemental.py; adds CNP/HEP/Tier typed projectors, the F-CS schema
fingerprint and pagination. No live execution authorized by this module itself.
"""
import argparse
import datetime
import hashlib
import ipaddress
import json
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

from supplemental import (
    UnsupportedDiscovery,
    UnsupportedField,
    UnsupportedIdentity,
    _check_keys,
    _dict,
    _dict_req,
    _enum,
    _meta,
    _nonempty,
    _num,
    _require,
    _str,
    _str_list,
    classify,
    project_calico_policy,
    project_discovery,
    project_felix,
    project_pod_identity,
    verify_calico_identity,
)

CTX = 'kubernetes-admin@pak-portal'
REQUEST_TIMEOUT = '15s'
SUBPROCESS_TIMEOUT = 20
OUTPUT_FILE = 'followup.jsonl'

# F-CS canonical spec-schema hash (network-policy-api v1alpha2 ClusterNetworkPolicy).
CNP_SPEC_SHA256 = '770130a412fd6fab2f02d953edf35f8cc68bf4379db8307e2185937c1e699568'

# Pagination budget for the five --raw list reads.
PAGE_LIMIT = 200
PAGE_LIMIT_LAST = 100
TOTAL_CAP = 500
MAX_PAGES = 3

CNP_TIER = {'Admin', 'Baseline'}
CNP_ACTION = {'Accept', 'Deny', 'Pass'}
CNP_PROTOCOL = {'tcp', 'udp', 'sctp'}
EXPR_OPERATOR = {'In', 'NotIn', 'Exists', 'DoesNotExist'}


def _strip_descriptions(obj):
    if isinstance(obj, dict):
        return {k: _strip_descriptions(v) for k, v in obj.items() if k != 'description'}
    if isinstance(obj, list):
        return [_strip_descriptions(x) for x in obj]
    return obj


def _canonicalize(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False,
                      separators=(',', ':'), allow_nan=False)


def _expr(e, field):
    o = _dict_req(e, field)
    _check_keys(o, {'key', 'operator', 'values'}, field)
    key = _nonempty(o.get('key'), field + '.key')
    op = _enum(o.get('operator'), field + '.operator', EXPR_OPERATOR)
    values = o.get('values')
    if op in ('In', 'NotIn'):
        if not isinstance(values, list) or not values or not all(isinstance(x, str) for x in values):
            raise ValueError(field + '.values must be a nonempty string list for ' + op)
        return {'key': key, 'operator': op, 'values': values}
    if values not in (None, []):
        raise ValueError(field + '.values must be absent/empty for ' + op)
    return {'key': key, 'operator': op}


def _selector(v, field, required=False):
    if v is None:
        if required:
            raise ValueError(field + ' required')
        return {}
    if not isinstance(v, dict):
        raise ValueError(field + ' not an object')
    _check_keys(v, {'matchLabels', 'matchExpressions'}, field)
    out = {}
    if 'matchLabels' in v:
        ml = v['matchLabels']
        if not isinstance(ml, dict) or not all(isinstance(k, str) and isinstance(val, str)
                                               for k, val in ml.items()):
            raise ValueError(field + '.matchLabels not a string map')
        out['matchLabels'] = dict(ml)
    if 'matchExpressions' in v:
        me = v['matchExpressions']
        if not isinstance(me, list):
            raise ValueError(field + '.matchExpressions not a list')
        out['matchExpressions'] = [_expr(e, field + '.matchExpressions[%d]' % i) for i, e in enumerate(me)]
    return out


def _valid_cidr(x):
    try:
        net = ipaddress.ip_network(x, strict=False)
    except ValueError:
        return False
    return str(net) == x


def _networks(v, field):
    if not isinstance(v, list) or not (1 <= len(v) <= 25):
        raise ValueError(field + ' must be a list of 1..25 CIDRs')
    out = []
    for x in v:
        if not isinstance(x, str) or len(x) > 43 or not _valid_cidr(x):
            raise ValueError(field + ' invalid CIDR ' + repr(x))
        out.append(x)
    return out


def _namespaced_pod(v, field):
    o = _dict_req(v, field)
    _check_keys(o, {'namespaceSelector', 'podSelector'}, field)
    pod_sel = _selector(o.get('podSelector'), field + '.podSelector', required=True)
    out = {'podSelector': pod_sel}
    if 'namespaceSelector' in o:
        out['namespaceSelector'] = _selector(o['namespaceSelector'], field + '.namespaceSelector')
    return out


def _subject(v, field):
    o = _dict_req(v, field)
    _check_keys(o, {'namespaces', 'pods'}, field)
    keys = [k for k in ('namespaces', 'pods') if k in o]
    if len(keys) != 1:
        raise ValueError(field + ' must set exactly one of namespaces/pods')
    if 'namespaces' in o:
        return {'namespaces': _selector(o['namespaces'], field + '.namespaces')}
    return {'pods': _namespaced_pod(o['pods'], field + '.pods')}


def _peer(v, field, egress=False):
    o = _dict_req(v, field)
    allowed = {'namespaces', 'pods', 'networks'} if egress else {'namespaces', 'pods'}
    _check_keys(o, allowed, field)
    keys = [k for k in allowed if k in o]
    if len(keys) != 1:
        raise ValueError(field + ' must set exactly one peer field')
    k = keys[0]
    if k == 'namespaces':
        return {'namespaces': _selector(o['namespaces'], field + '.namespaces')}
    if k == 'pods':
        return {'pods': _namespaced_pod(o['pods'], field + '.pods')}
    return {'networks': _networks(o['networks'], field + '.networks')}


def _destination_port(v, field):
    o = _dict_req(v, field)
    _check_keys(o, {'number', 'range'}, field)
    keys = [k for k in ('number', 'range') if k in o]
    if len(keys) != 1:
        raise ValueError(field + ' must set exactly one of number/range')
    if 'number' in o:
        n = o['number']
        if isinstance(n, bool) or not isinstance(n, int) or not (1 <= n <= 65535):
            raise ValueError(field + '.number out of range')
        return {'number': n}
    r = _dict_req(o['range'], field + '.range')
    _check_keys(r, {'start', 'end'}, field + '.range')
    start, end = r.get('start'), r.get('end')
    if isinstance(start, bool) or not isinstance(start, int) or not (1 <= start <= 65535):
        raise ValueError(field + '.range.start out of range')
    if isinstance(end, bool) or not isinstance(end, int) or not (1 <= end <= 65535):
        raise ValueError(field + '.range.end out of range')
    if not (start < end):
        raise ValueError(field + '.range must have start < end')
    return {'range': {'start': start, 'end': end}}


def _protocol(p, field):
    o = _dict_req(p, field)
    _check_keys(o, CNP_PROTOCOL, field)
    keys = [k for k in CNP_PROTOCOL if k in o]
    if len(keys) != 1:
        raise ValueError(field + ' must set exactly one of tcp/udp/sctp')
    k = keys[0]
    po = _dict_req(o[k], field + '.' + k)
    _check_keys(po, {'destinationPort'}, field + '.' + k)
    dp = _destination_port(po.get('destinationPort'), field + '.' + k + '.destinationPort')
    return {k: {'destinationPort': dp}}


def _protocols(v, field):
    if v is None:
        return None
    if not isinstance(v, list) or not (1 <= len(v) <= 25):
        raise ValueError(field + ' must be a list of 1..25 protocols')
    return [_protocol(p, field + '[%d]' % i) for i, p in enumerate(v)]


def _rule(r, field, egress=False):
    o = _dict_req(r, field)
    _check_keys(o, {'name', 'action', 'from', 'to', 'protocols'}, field)
    action = _enum(o.get('action'), field + '.action', CNP_ACTION)
    out = {'action': action}
    if 'name' in o:
        name = o['name']
        if not isinstance(name, str) or len(name) > 100:
            raise ValueError(field + '.name must be string <=100')
        out['name'] = name
    peers_key = 'to' if egress else 'from'
    peers = o.get(peers_key)
    if not isinstance(peers, list) or not (1 <= len(peers) <= 25):
        raise ValueError(field + '.' + peers_key + ' must be 1..25 peers')
    out[peers_key] = [_peer(x, field + '.%s[%d]' % (peers_key, i), egress=egress)
                      for i, x in enumerate(peers)]
    if 'protocols' in o:
        out['protocols'] = _protocols(o['protocols'], field + '.protocols')
    return out


def project_cnp(obj):
    _require(obj, 'ClusterNetworkPolicy', 'policy.networking.k8s.io/v1alpha2')
    md = _meta(obj, namespaced=False)
    spec = _dict_req(obj.get('spec'), 'spec')
    _check_keys(spec, {'tier', 'priority', 'subject', 'ingress', 'egress'}, 'spec')
    tier = _enum(spec.get('tier'), 'spec.tier', CNP_TIER)
    priority = spec.get('priority')
    if isinstance(priority, bool) or not isinstance(priority, int) or not (0 <= priority <= 1000):
        raise ValueError('spec.priority must be integer 0..1000')
    subject = _subject(spec.get('subject'), 'spec.subject')
    out = {'apiVersion': 'policy.networking.k8s.io/v1alpha2', 'kind': 'ClusterNetworkPolicy',
           'metadata': md, 'spec': {'tier': tier, 'priority': priority, 'subject': subject}}
    if 'ingress' in spec:
        ing = spec['ingress']
        if not isinstance(ing, list) or len(ing) > 25:
            raise ValueError('spec.ingress must be array <=25')
        out['spec']['ingress'] = [_rule(x, 'spec.ingress[%d]' % i, egress=False) for i, x in enumerate(ing)]
    if 'egress' in spec:
        egr = spec['egress']
        if not isinstance(egr, list) or len(egr) > 25:
            raise ValueError('spec.egress must be array <=25')
        out['spec']['egress'] = [_rule(x, 'spec.egress[%d]' % i, egress=True) for i, x in enumerate(egr)]
    return out


def _int_or_string_port(v, field):
    if isinstance(v, int) and not isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v
    raise ValueError(field + ' not int-or-string')


def project_hep(obj):
    _require(obj, 'HostEndpoint', 'crd.projectcalico.org/v1')
    md = _meta(obj, namespaced=False)
    out = {'apiVersion': 'crd.projectcalico.org/v1', 'kind': 'HostEndpoint', 'metadata': md}
    if 'labels' in obj.get('metadata', {}):
        labels = obj['metadata']['labels']
        if not isinstance(labels, dict) or not all(isinstance(k, str) and isinstance(val, str)
                                                  for k, val in labels.items()):
            raise ValueError('metadata.labels not a string map')
        out['metadata']['labels'] = dict(labels)
    spec = _dict_req(obj.get('spec'), 'spec')
    _check_keys(spec, {'node', 'interfaceName', 'expectedIPs', 'profiles', 'ports'}, 'spec')
    node = spec.get('node')
    if not isinstance(node, str) or node == '' or len(node) > 253:
        raise ValueError('spec.node must be nonempty string <=253')
    sp = {'node': node}
    if 'interfaceName' in spec:
        ifn = spec['interfaceName']
        if not isinstance(ifn, str) or len(ifn) > 15:
            raise ValueError('spec.interfaceName must be string <=15')
        sp['interfaceName'] = ifn
    if 'expectedIPs' in spec:
        sp['expectedIPs'] = _str_list(spec['expectedIPs'], 'spec.expectedIPs')
    if 'profiles' in spec:
        sp['profiles'] = _str_list(spec['profiles'], 'spec.profiles')
    if 'ports' in spec:
        ports = spec['ports']
        if not isinstance(ports, list):
            raise ValueError('spec.ports not a list')
        sp['ports'] = []
        for i, p in enumerate(ports):
            po = _dict_req(p, 'spec.ports[%d]' % i)
            _check_keys(po, {'name', 'port', 'protocol'}, 'spec.ports[%d]' % i)
            name = _nonempty(po.get('name'), 'spec.ports[%d].name' % i)
            port = po.get('port')
            if isinstance(port, bool) or not isinstance(port, int) or not (1 <= port <= 65535):
                raise ValueError('spec.ports[%d].port out of range' % i)
            proto = _int_or_string_port(po.get('protocol'), 'spec.ports[%d].protocol' % i)
            sp['ports'].append({'name': name, 'port': port, 'protocol': proto})
    ifn_ok = bool(sp.get('interfaceName'))
    eip_ok = bool(sp.get('expectedIPs'))
    if not ifn_ok and not eip_ok:
        raise ValueError('spec must set nonempty interfaceName or expectedIPs')
    out['spec'] = sp
    return out


def project_tier(obj):
    _require(obj, 'Tier', 'crd.projectcalico.org/v1')
    md = _meta(obj, namespaced=False)
    out = {'apiVersion': 'crd.projectcalico.org/v1', 'kind': 'Tier', 'metadata': md}
    spec = _dict_req(obj.get('spec'), 'spec')
    _check_keys(spec, {'order', 'defaultAction'}, 'spec')
    sp = {}
    if 'order' in spec:
        sp['order'] = _num(spec['order'], 'spec.order')
    if 'defaultAction' in spec:
        da = spec['defaultAction']
        if not isinstance(da, str) or da not in ('Pass', 'Deny'):
            raise ValueError('spec.defaultAction invalid enum')
        sp['defaultAction'] = da
    # schema-derived default is Deny; absence is preserved (not fabricated)
    out['spec'] = sp
    return out


def project_crd_schema(raw):
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError('crd not an object')
    if data.get('apiVersion') != 'apiextensions.k8s.io/v1':
        raise ValueError('crd apiVersion mismatch')
    if data.get('kind') != 'CustomResourceDefinition':
        raise ValueError('crd kind mismatch')
    md = _meta(data, namespaced=False)
    if md['name'] != 'clusternetworkpolicies.policy.networking.k8s.io':
        raise ValueError('crd name mismatch')
    spec = _dict_req(data.get('spec'), 'spec')
    if spec.get('group') != 'policy.networking.k8s.io':
        raise ValueError('crd group mismatch')
    names = _dict_req(spec.get('names'), 'spec.names')
    if names.get('kind') != 'ClusterNetworkPolicy':
        raise ValueError('crd names.kind mismatch')
    if names.get('plural') != 'clusternetworkpolicies':
        raise ValueError('crd names.plural mismatch')
    if spec.get('scope') != 'Cluster':
        raise ValueError('crd scope mismatch')
    versions = spec.get('versions')
    if not isinstance(versions, list):
        raise ValueError('crd versions not a list')
    v1a2 = [v for v in versions if isinstance(v, dict) and v.get('name') == 'v1alpha2']
    if len(v1a2) != 1:
        raise ValueError('crd must have exactly one v1alpha2 version')
    v = v1a2[0]
    if not v.get('served'):
        raise ValueError('crd v1alpha2 not served')
    schema = _dict_req(v.get('schema'), 'versions[0].schema')
    oas = _dict_req(schema.get('openAPIV3Schema'), 'openAPIV3Schema')
    props = _dict_req(oas.get('properties'), 'openAPIV3Schema.properties')
    spec_subtree = _dict_req(props.get('spec'), 'properties.spec')
    canon = _canonicalize(_strip_descriptions(spec_subtree))
    h = hashlib.sha256(canon.encode('utf-8')).hexdigest()
    return {
        'apiVersion': 'apiextensions.k8s.io/v1',
        'kind': 'CustomResourceDefinition',
        'name': md['name'],
        'group': spec['group'],
        'names_kind': names['kind'],
        'plural': names['plural'],
        'scope': spec['scope'],
        'version': 'v1alpha2',
        'served': bool(v['served']),
        'spec_schema_sha256': h,
        'compatible': h == CNP_SPEC_SHA256,
    }


D1_EXPECT = {
    'networkpolicies': ('NetworkPolicy', True, ['get', 'list']),
    'globalnetworkpolicies': ('GlobalNetworkPolicy', False, ['get', 'list']),
    'felixconfigurations': ('FelixConfiguration', False, ['get']),
    'hostendpoints': ('HostEndpoint', False, ['get', 'list']),
    'tiers': ('Tier', False, ['get', 'list']),
}


def _project_d1(raw):
    output = project_discovery(raw)
    data = json.loads(output)
    if data['groupVersion'] != 'crd.projectcalico.org/v1':
        raise ValueError('discovery groupVersion mismatch')
    res_by_name = {r['name']: r for r in data['resources']}
    for rname, (kind, namespaced, verbs) in D1_EXPECT.items():
        if rname not in res_by_name:
            raise ValueError('discovery missing resource ' + rname)
        rr = res_by_name[rname]
        if rr['kind'] != kind:
            raise ValueError('resource %s kind %s != %s' % (rname, rr['kind'], kind))
        if rr['namespaced'] != namespaced:
            raise ValueError('resource %s scope mismatch' % rname)
        for verb in verbs:
            if verb not in rr['verbs']:
                raise ValueError('resource %s missing verb %s' % (rname, verb))
    return output


READS = [
    {'id': 'F-D1', 'argv': ['get', '--raw', '/apis/crd.projectcalico.org/v1'], 'kind': 'discovery',
     'deps': [], 'proj': 'd1', 'paginated': False},
    {'id': 'F-I1', 'argv': ['get', 'pods', '-n', 'kube-system', '-l', 'k8s-app=calico-node', '-o', 'json'],
     'kind': 'podlist', 'deps': [], 'proj': 'i1', 'paginated': False},
    {'id': 'F-CS', 'argv': ['get', '--raw',
                            '/apis/apiextensions.k8s.io/v1/customresourcedefinitions/clusternetworkpolicies.policy.networking.k8s.io'],
     'kind': 'crd', 'deps': [], 'proj': 'cs', 'paginated': False},
    {'id': 'F-CNP', 'argv': ['get', '--raw', '/apis/policy.networking.k8s.io/v1alpha2/clusternetworkpolicies'],
     'kind': 'list', 'deps': ['F-CS'], 'proj': 'cnp', 'paginated': True},
    {'id': 'F-NP', 'argv': ['get', '--raw', '/apis/crd.projectcalico.org/v1/networkpolicies'],
     'kind': 'list', 'deps': ['F-D1', 'F-I1'], 'proj': 'np', 'paginated': True},
    {'id': 'F-GNP', 'argv': ['get', '--raw', '/apis/crd.projectcalico.org/v1/globalnetworkpolicies'],
     'kind': 'list', 'deps': ['F-D1', 'F-I1'], 'proj': 'gnp', 'paginated': True},
    {'id': 'F-FELIX', 'argv': ['get', '--raw', '/apis/crd.projectcalico.org/v1/felixconfigurations/default'],
     'kind': 'single', 'deps': ['F-D1', 'F-I1'], 'proj': 'felix', 'paginated': False},
    {'id': 'F-HEP', 'argv': ['get', '--raw', '/apis/crd.projectcalico.org/v1/hostendpoints'],
     'kind': 'list', 'deps': ['F-D1', 'F-I1'], 'proj': 'hep', 'paginated': True},
    {'id': 'F-TIER', 'argv': ['get', '--raw', '/apis/crd.projectcalico.org/v1/tiers'],
     'kind': 'list', 'deps': ['F-D1', 'F-I1'], 'proj': 'tier', 'paginated': True},
]

PROJECTOR = {
    'cnp': project_cnp,
    'hep': project_hep,
    'tier': project_tier,
    'np': lambda o: project_calico_policy(o, 'NetworkPolicy', namespaced=True),
    'gnp': lambda o: project_calico_policy(o, 'GlobalNetworkPolicy', namespaced=False),
    'felix': project_felix,
}


def _run(argv):
    return subprocess.run(argv, capture_output=True, text=True, timeout=SUBPROCESS_TIMEOUT)


def _list_pages(path, run_fn):
    items = []
    token = None
    rv = None
    seen = set()
    for page in range(MAX_PAGES):
        limit = PAGE_LIMIT if page < MAX_PAGES - 1 else PAGE_LIMIT_LAST
        p = path + '?limit=%d' % limit
        if token is not None:
            p += '&continue=' + quote(token, safe='')
        argv = ['kubectl', '--context', CTX, '--request-timeout=' + REQUEST_TIMEOUT,
                'get', '--raw', p]
        result = run_fn(argv)
        if result is None or result.returncode != 0:
            return items, False, 'next-page GET_FAILED'
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            raise ValueError('list not valid JSON')
        if not isinstance(data, dict):
            raise ValueError('list not an object')
        meta = data.get('metadata')
        meta = meta if isinstance(meta, dict) else {}
        new_rv = meta.get('resourceVersion')
        if rv is not None and new_rv != rv:
            return items, False, 'resourceVersion changed'
        rv = new_rv
        page_items = data.get('items')
        if not isinstance(page_items, list):
            raise ValueError('items not a list')
        items.extend(page_items)
        cont = meta.get('continue')
        if not cont:
            return items, True, None
        if cont in seen:
            return items, False, 'repeated continue token'
        seen.add(cont)
        token = cont
    return items, False, 'cap reached'


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


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
    with (directory / OUTPUT_FILE).open('x') as log:
        for entry in READS:
            rid = entry['id']
            unmet = [d for d in entry['deps'] if d not in ok_ids]
            if unmet:
                log.write(json.dumps({'id': rid, 'start': None, 'argv': None, 'exit': None,
                                      'category': 'BLOCKED_NOT_EXECUTED', 'blocked_by': unmet,
                                      'output': '', 'complete': None, 'end': _now()}) + '\n')
                failures += 1
                continue
            if entry['paginated']:
                path = entry['argv'][-1]
                argv = ['kubectl', '--context', args.context,
                        '--request-timeout=' + REQUEST_TIMEOUT, 'get', '--raw',
                        path + '?limit=%d' % PAGE_LIMIT]
            else:
                argv = ['kubectl', '--context', args.context,
                        '--request-timeout=' + REQUEST_TIMEOUT] + entry['argv']
            start = _now()
            timed_out = False
            result = None
            if entry['paginated']:
                try:
                    items, complete, reason = _list_pages(path, _run)
                    category = None
                    output = ''
                    try:
                        output = json.dumps([PROJECTOR[entry['proj']](it) for it in items])
                    except UnsupportedField:
                        category = 'UNSUPPORTED'
                    except (json.JSONDecodeError, ValueError, KeyError, TypeError):
                        category = 'PARSE_ERROR'
                    if category is None and not complete:
                        category = 'PARTIAL'
                except subprocess.TimeoutExpired:
                    category, complete, reason, output = 'TIMEOUT', False, 'timeout', ''
                except OSError:
                    category, complete, reason, output = 'GET_FAILED', False, 'os error', ''
                except (json.JSONDecodeError, ValueError, KeyError, TypeError):
                    category, complete, reason, output = 'PARSE_ERROR', False, 'malformed list', ''
                log.write(json.dumps({'id': rid, 'start': start, 'argv': argv,
                                      'exit': 0, 'category': category, 'output': output,
                                      'complete': complete, 'reason': reason,
                                      'end': _now()}) + '\n')
                if category is None:
                    ok_ids.add(rid)
                else:
                    failures += 1
                continue
            try:
                result = _run(argv)
            except subprocess.TimeoutExpired:
                timed_out = True
            except OSError:
                pass

            output = ''
            ok = result is not None and result.returncode == 0
            unsupported = False
            complete = None
            if ok:
                try:
                    kind = entry['kind']
                    if kind == 'discovery':
                        output = _project_d1(result.stdout)
                    elif kind == 'podlist':
                        data = json.loads(result.stdout)
                        meta = data.get('metadata') or {}
                        if meta.get('continue'):
                            output = ''
                            complete = False
                            raise ValueError('pod list incomplete (continue present)')
                        items = data.get('items')
                        if not isinstance(items, list):
                            raise ValueError('items not a list')
                        proj = [project_pod_identity(it, 'kube-system') for it in items]
                        verify_calico_identity(proj)
                        output = json.dumps(proj)
                        complete = True
                    elif kind == 'crd':
                        proj = project_crd_schema(result.stdout)
                        if not proj['compatible']:
                            unsupported = True
                        output = json.dumps(proj)
                    elif kind == 'single':
                        data = json.loads(result.stdout)
                        if not isinstance(data, dict):
                            raise ValueError('expected single object')
                        output = json.dumps(PROJECTOR[entry['proj']](data))
                    else:
                        raise ValueError('unknown kind ' + kind)
                except UnsupportedField:
                    unsupported = True
                except UnsupportedDiscovery:
                    unsupported = True
                except UnsupportedIdentity:
                    unsupported = True
                except (json.JSONDecodeError, ValueError, KeyError, TypeError):
                    failures += 1
                    log.write(json.dumps({'id': rid, 'start': start, 'argv': argv,
                                          'exit': 0, 'category': 'PARSE_ERROR', 'output': '',
                                          'complete': complete, 'end': _now()}) + '\n')
                    continue
            if unsupported:
                category = 'UNSUPPORTED'
            else:
                category = classify(None if result is None else result.returncode,
                                    '' if result is None else result.stderr, timed_out)
            if category is not None:
                failures += 1
            else:
                ok_ids.add(rid)
            log.write(json.dumps({'id': rid, 'start': start, 'argv': argv,
                                  'exit': None if result is None else result.returncode,
                                  'category': category, 'output': output, 'complete': complete,
                                  'end': _now()}) + '\n')
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
