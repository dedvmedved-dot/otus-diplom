#!/usr/bin/env python3
"""P8C-R1 RV-02 — bounded follow-up collector (F-D1..F-TIER), corrected.

Offline source design per portal/networkpolicy/followup-read-design.md. Corrections
R1-R4 after review d71af18: preserved per-page journal + honest exit codes, hard
boundary/null semantics, typed CRD version identity, cluster-scope null checks.
No live execution authorized by this module itself.
"""
import argparse
import copy
import datetime
import hashlib
import ipaddress
import json
import math
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
    _dict_req,
    _enum,
    _nonempty,
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

CNP_SPEC_SHA256 = '770130a412fd6fab2f02d953edf35f8cc68bf4379db8307e2185937c1e699568'

PAGE_LIMIT = 200
PAGE_LIMIT_LAST = 100
TOTAL_CAP = 500
MAX_PAGES = 3

CNP_TIER = {'Admin', 'Baseline'}
CNP_ACTION = {'Accept', 'Deny', 'Pass'}
CNP_PROTOCOL = {'tcp', 'udp', 'sctp'}
EXPR_OPERATOR = {'In', 'NotIn', 'Exists', 'DoesNotExist'}

LIST_ENVELOPE = {
    'F-CNP': ('ClusterNetworkPolicyList', 'policy.networking.k8s.io/v1alpha2'),
    'F-NP': ('NetworkPolicyList', 'crd.projectcalico.org/v1'),
    'F-GNP': ('GlobalNetworkPolicyList', 'crd.projectcalico.org/v1'),
    'F-HEP': ('HostEndpointList', 'crd.projectcalico.org/v1'),
    'F-TIER': ('TierList', 'crd.projectcalico.org/v1'),
}


def normalize_schema(s):
    if isinstance(s, bool):
        return s
    if not isinstance(s, dict):
        raise ValueError('schema must be object/boolean')
    maps = {'properties', 'patternProperties', 'definitions', '$defs', 'dependentSchemas'}
    arrays = {'allOf', 'anyOf', 'oneOf', 'prefixItems'}
    singles = {'items', 'additionalItems', 'additionalProperties', 'unevaluatedItems',
               'unevaluatedProperties', 'not', 'contains', 'propertyNames', 'if', 'then', 'else'}
    out = {}
    for k, v in s.items():
        if k == 'description':
            continue
        if k in maps:
            if not isinstance(v, dict):
                raise ValueError('schema map')
            out[k] = {name: normalize_schema(sub) for name, sub in v.items()}
        elif k in arrays:
            if not isinstance(v, list):
                raise ValueError('schema array')
            out[k] = [normalize_schema(sub) for sub in v]
        elif k in singles:
            if k == 'items' and isinstance(v, list):
                out[k] = [normalize_schema(sub) for sub in v]
            else:
                out[k] = normalize_schema(v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def _canonicalize(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False,
                      separators=(',', ':'), allow_nan=False)


def _expr(e, field):
    o = _dict_req(e, field)
    _check_keys(o, {'key', 'operator', 'values'}, field)
    key = _nonempty(o.get('key'), field + '.key')
    op = _enum(o.get('operator'), field + '.operator', EXPR_OPERATOR)
    if 'values' in o:
        values = o['values']
        if values is None:
            raise ValueError(field + '.values cannot be null')
        if op in ('In', 'NotIn'):
            if not isinstance(values, list) or not values or not all(isinstance(x, str) for x in values):
                raise ValueError(field + '.values must be a nonempty string list for ' + op)
            return {'key': key, 'operator': op, 'values': values}
        if values != []:
            raise ValueError(field + '.values must be empty for ' + op)
        return {'key': key, 'operator': op}
    if op in ('In', 'NotIn'):
        raise ValueError(field + '.values required for ' + op)
    return {'key': key, 'operator': op}


def _selector(v, field):
    if v is None:
        raise ValueError(field + ' cannot be null')
    if not isinstance(v, dict):
        raise ValueError(field + ' not an object')
    _check_keys(v, {'matchLabels', 'matchExpressions'}, field)
    out = {}
    if 'matchLabels' in v:
        if v['matchLabels'] is None:
            raise ValueError(field + '.matchLabels cannot be null')
        ml = v['matchLabels']
        if not isinstance(ml, dict) or not all(isinstance(k, str) and isinstance(val, str)
                                               for k, val in ml.items()):
            raise ValueError(field + '.matchLabels not a string map')
        out['matchLabels'] = dict(ml)
    if 'matchExpressions' in v:
        if v['matchExpressions'] is None:
            raise ValueError(field + '.matchExpressions cannot be null')
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
    if v is None:
        raise ValueError(field + ' cannot be null')
    if not isinstance(v, list) or not (1 <= len(v) <= 25):
        raise ValueError(field + ' must be a list of 1..25 CIDRs')
    out = []
    seen = set()
    for x in v:
        if not isinstance(x, str) or len(x) > 43 or not _valid_cidr(x):
            raise ValueError(field + ' invalid CIDR ' + repr(x))
        if x in seen:
            raise ValueError(field + ' duplicate CIDR ' + x)
        seen.add(x)
        out.append(x)
    return out


def _namespaced_pod(v, field):
    o = _dict_req(v, field)
    _check_keys(o, {'namespaceSelector', 'podSelector'}, field)
    if 'podSelector' not in o or o['podSelector'] is None:
        raise ValueError(field + '.podSelector required')
    out = {'podSelector': _selector(o['podSelector'], field + '.podSelector')}
    if 'namespaceSelector' in o:
        if o['namespaceSelector'] is None:
            raise ValueError(field + '.namespaceSelector cannot be null')
        out['namespaceSelector'] = _selector(o['namespaceSelector'], field + '.namespaceSelector')
    return out


def _subject(v, field):
    o = _dict_req(v, field)
    _check_keys(o, {'namespaces', 'pods'}, field)
    keys = [k for k in ('namespaces', 'pods') if k in o]
    if len(keys) != 1:
        raise ValueError(field + ' must set exactly one of namespaces/pods')
    k = keys[0]
    if o[k] is None:
        raise ValueError(field + '.' + k + ' cannot be null')
    if k == 'namespaces':
        return {'namespaces': _selector(o[k], field + '.namespaces')}
    return {'pods': _namespaced_pod(o[k], field + '.pods')}


def _peer(v, field, egress=False):
    o = _dict_req(v, field)
    allowed = {'namespaces', 'pods', 'networks'} if egress else {'namespaces', 'pods'}
    _check_keys(o, allowed, field)
    keys = [k for k in allowed if k in o]
    if len(keys) != 1:
        raise ValueError(field + ' must set exactly one peer field')
    k = keys[0]
    if o[k] is None:
        raise ValueError(field + '.' + k + ' cannot be null')
    if k == 'namespaces':
        return {'namespaces': _selector(o[k], field + '.namespaces')}
    if k == 'pods':
        return {'pods': _namespaced_pod(o[k], field + '.pods')}
    return {'networks': _networks(o[k], field + '.networks')}


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
    if o[k] is None:
        raise ValueError(field + '.' + k + ' cannot be null')
    po = _dict_req(o[k], field + '.' + k)
    _check_keys(po, {'destinationPort'}, field + '.' + k)
    if 'destinationPort' not in po or po['destinationPort'] is None:
        raise ValueError(field + '.' + k + '.destinationPort required')
    dp = _destination_port(po['destinationPort'], field + '.' + k + '.destinationPort')
    return {k: {'destinationPort': dp}}


def _protocols(v, field):
    if v is None:
        raise ValueError(field + ' cannot be null')
    if not isinstance(v, list) or not (1 <= len(v) <= 25):
        raise ValueError(field + ' must be a list of 1..25 protocols')
    return [_protocol(p, field + '[%d]' % i) for i, p in enumerate(v)]


def _rule(r, field, egress=False):
    o = _dict_req(r, field)
    allowed = {'name', 'action', 'to', 'protocols'} if egress else {'name', 'action', 'from', 'protocols'}
    _check_keys(o, allowed, field)
    action = _enum(o.get('action'), field + '.action', CNP_ACTION)
    out = {'action': action}
    if 'name' in o:
        if o['name'] is None:
            raise ValueError(field + '.name cannot be null')
        name = o['name']
        if not isinstance(name, str) or len(name) > 100:
            raise ValueError(field + '.name must be string <=100')
        out['name'] = name
    peers_key = 'to' if egress else 'from'
    if peers_key not in o or o[peers_key] is None:
        raise ValueError(field + '.' + peers_key + ' required')
    peers = o[peers_key]
    if not isinstance(peers, list) or not (1 <= len(peers) <= 25):
        raise ValueError(field + '.' + peers_key + ' must be 1..25 peers')
    out[peers_key] = [_peer(x, field + '.%s[%d]' % (peers_key, i), egress=egress)
                      for i, x in enumerate(peers)]
    if 'protocols' in o:
        out['protocols'] = _protocols(o['protocols'], field + '.protocols')
    return out


def _labels(md):
    if 'labels' not in md:
        return None
    if md['labels'] is None:
        raise ValueError('metadata.labels cannot be null')
    labels = md['labels']
    if not isinstance(labels, dict) or not all(isinstance(k, str) and isinstance(v, str)
                                              for k, v in labels.items()):
        raise ValueError('metadata.labels not a string map')
    return dict(labels)


def _cluster_meta(obj, kind, api):
    _require(obj, kind, api)
    md = _dict_req(obj.get('metadata'), 'metadata')
    name = _nonempty(md.get('name'), 'metadata.name')
    if 'namespace' in md:
        ns = md['namespace']
        if ns is None:
            raise ValueError('cluster-scoped ' + kind + ' namespace cannot be null')
        if not isinstance(ns, str):
            raise ValueError('cluster-scoped ' + kind + ' namespace must be string')
        if ns != '':
            raise ValueError('cluster-scoped ' + kind + ' must not set metadata.namespace')
    return {'name': name, 'namespace': None}


def _cluster_check(obj, kind):
    md = _dict_req(obj.get('metadata'), 'metadata')
    if 'namespace' in md:
        ns = md['namespace']
        if ns is None:
            raise ValueError('cluster-scoped ' + kind + ' namespace cannot be null')
        if not isinstance(ns, str):
            raise ValueError('cluster-scoped ' + kind + ' namespace must be string')
        if ns != '':
            raise ValueError('cluster-scoped ' + kind + ' must not set metadata.namespace')
    return True


def _finite_num(v, field):
    if v is None or isinstance(v, bool) or not isinstance(v, (int, float)):
        raise ValueError(field + ' not a number')
    if isinstance(v, float) and not math.isfinite(v):
        raise ValueError(field + ' not finite')
    return v


def project_cnp(obj):
    _require(obj, 'ClusterNetworkPolicy', 'policy.networking.k8s.io/v1alpha2')
    md = _cluster_meta(obj, 'ClusterNetworkPolicy', 'policy.networking.k8s.io/v1alpha2')
    spec = _dict_req(obj.get('spec'), 'spec')
    _check_keys(spec, {'tier', 'priority', 'subject', 'ingress', 'egress'}, 'spec')
    tier = _enum(spec.get('tier'), 'spec.tier', CNP_TIER)
    priority = spec.get('priority')
    if isinstance(priority, bool) or not isinstance(priority, int) or not (0 <= priority <= 1000):
        raise ValueError('spec.priority must be integer 0..1000')
    subject = _subject(spec.get('subject'), 'spec.subject')
    out = {'apiVersion': 'policy.networking.k8s.io/v1alpha2', 'kind': 'ClusterNetworkPolicy',
           'metadata': md, 'spec': {'tier': tier, 'priority': priority, 'subject': subject}}
    if 'labels' in obj.get('metadata', {}):
        out['metadata']['labels'] = _labels(obj['metadata'])
    if 'ingress' in spec:
        ing = spec['ingress']
        if ing is None:
            raise ValueError('spec.ingress cannot be null')
        if not isinstance(ing, list) or len(ing) > 25:
            raise ValueError('spec.ingress must be array <=25')
        out['spec']['ingress'] = [_rule(x, 'spec.ingress[%d]' % i, egress=False) for i, x in enumerate(ing)]
    if 'egress' in spec:
        egr = spec['egress']
        if egr is None:
            raise ValueError('spec.egress cannot be null')
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
    md = _cluster_meta(obj, 'HostEndpoint', 'crd.projectcalico.org/v1')
    out = {'apiVersion': 'crd.projectcalico.org/v1', 'kind': 'HostEndpoint', 'metadata': md}
    if 'labels' in obj.get('metadata', {}):
        out['metadata']['labels'] = _labels(obj['metadata'])
    spec = _dict_req(obj.get('spec'), 'spec')
    _check_keys(spec, {'node', 'interfaceName', 'expectedIPs', 'profiles', 'ports'}, 'spec')
    node = spec.get('node')
    if node is None or not isinstance(node, str) or node == '' or len(node) > 253:
        raise ValueError('spec.node must be nonempty string <=253')
    sp = {'node': node}
    if 'interfaceName' in spec:
        if spec['interfaceName'] is None:
            raise ValueError('spec.interfaceName cannot be null')
        ifn = spec['interfaceName']
        if not isinstance(ifn, str) or len(ifn) > 15:
            raise ValueError('spec.interfaceName must be string <=15')
        sp['interfaceName'] = ifn
    if 'expectedIPs' in spec:
        if spec['expectedIPs'] is None:
            raise ValueError('spec.expectedIPs cannot be null')
        eips = _str_list(spec['expectedIPs'], 'spec.expectedIPs')
        if len(set(eips)) != len(eips):
            raise ValueError('spec.expectedIPs duplicate')
        sp['expectedIPs'] = eips
    if 'profiles' in spec:
        if spec['profiles'] is None:
            raise ValueError('spec.profiles cannot be null')
        profs = _str_list(spec['profiles'], 'spec.profiles')
        if len(set(profs)) != len(profs):
            raise ValueError('spec.profiles duplicate')
        sp['profiles'] = profs
    if 'ports' in spec:
        if spec['ports'] is None:
            raise ValueError('spec.ports cannot be null')
        ports = spec['ports']
        if not isinstance(ports, list):
            raise ValueError('spec.ports not a list')
        sp['ports'] = []
        for i, p in enumerate(ports):
            po = _dict_req(p, 'spec.ports[%d]' % i)
            _check_keys(po, {'name', 'port', 'protocol'}, 'spec.ports[%d]' % i)
            if 'name' not in po or po['name'] is None:
                raise ValueError('spec.ports[%d].name required' % i)
            name = po['name']
            if not isinstance(name, str):
                raise ValueError('spec.ports[%d].name not a string' % i)
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
    md = _cluster_meta(obj, 'Tier', 'crd.projectcalico.org/v1')
    out = {'apiVersion': 'crd.projectcalico.org/v1', 'kind': 'Tier', 'metadata': md}
    if 'labels' in obj.get('metadata', {}):
        out['metadata']['labels'] = _labels(obj['metadata'])
    spec = _dict_req(obj.get('spec'), 'spec')
    _check_keys(spec, {'order', 'defaultAction'}, 'spec')
    sp = {}
    if 'order' in spec:
        if spec['order'] is None:
            raise ValueError('spec.order cannot be null')
        sp['order'] = _finite_num(spec['order'], 'spec.order')
    if 'defaultAction' in spec:
        da = spec['defaultAction']
        if da is None:
            raise ValueError('spec.defaultAction cannot be null')
        if not isinstance(da, str) or da not in ('Pass', 'Deny'):
            raise ValueError('spec.defaultAction invalid enum')
        sp['defaultAction'] = da
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
    md = _cluster_meta(data, 'CustomResourceDefinition', 'apiextensions.k8s.io/v1')
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
    v1a2 = []
    for i, v in enumerate(versions):
        if not isinstance(v, dict):
            raise ValueError('crd versions[%d] not an object' % i)
        name = v.get('name')
        if name is None or not isinstance(name, str) or name == '':
            raise ValueError('crd versions[%d].name must be nonempty string' % i)
        if 'served' in v and not isinstance(v['served'], bool):
            raise ValueError('crd versions[%d].served must be bool' % i)
        if name == 'v1alpha2':
            v1a2.append(v)
    if len(v1a2) != 1:
        raise ValueError('crd must have exactly one v1alpha2 version')
    v = v1a2[0]
    if v.get('served') is not True:
        raise ValueError('crd v1alpha2 served must be boolean true')
    schema = _dict_req(v.get('schema'), 'versions[0].schema')
    oas = _dict_req(schema.get('openAPIV3Schema'), 'openAPIV3Schema')
    props = _dict_req(oas.get('properties'), 'openAPIV3Schema.properties')
    spec_subtree = _dict_req(props.get('spec'), 'properties.spec')
    canon = _canonicalize(normalize_schema(spec_subtree))
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
        'served': True,
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
    verdicts = {}
    for rname, (kind, namespaced, verbs) in D1_EXPECT.items():
        rr = res_by_name.get(rname)
        verdicts[rname] = (rr is not None and rr['kind'] == kind and rr['namespaced'] == namespaced
                           and all(v in rr['verbs'] for v in verbs))
    return output, verdicts


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
     'kind': 'list', 'deps': ['D1:networkpolicies', 'F-I1'], 'proj': 'np', 'paginated': True},
    {'id': 'F-GNP', 'argv': ['get', '--raw', '/apis/crd.projectcalico.org/v1/globalnetworkpolicies'],
     'kind': 'list', 'deps': ['D1:globalnetworkpolicies', 'F-I1'], 'proj': 'gnp', 'paginated': True},
    {'id': 'F-FELIX', 'argv': ['get', '--raw', '/apis/crd.projectcalico.org/v1/felixconfigurations/default'],
     'kind': 'single', 'deps': ['D1:felixconfigurations', 'F-I1'], 'proj': 'felix', 'paginated': False},
    {'id': 'F-HEP', 'argv': ['get', '--raw', '/apis/crd.projectcalico.org/v1/hostendpoints'],
     'kind': 'list', 'deps': ['D1:hostendpoints', 'F-I1'], 'proj': 'hep', 'paginated': True},
    {'id': 'F-TIER', 'argv': ['get', '--raw', '/apis/crd.projectcalico.org/v1/tiers'],
     'kind': 'list', 'deps': ['D1:tiers', 'F-I1'], 'proj': 'tier', 'paginated': True},
]

def _project_gnp(obj):
    _cluster_check(obj, 'GlobalNetworkPolicy')
    return project_calico_policy(obj, 'GlobalNetworkPolicy', namespaced=False)


def _project_felix(obj):
    _cluster_check(obj, 'FelixConfiguration')
    return project_felix(obj)


PROJECTOR = {
    'cnp': project_cnp,
    'hep': project_hep,
    'tier': project_tier,
    'np': lambda o: project_calico_policy(o, 'NetworkPolicy', namespaced=True),
    'gnp': _project_gnp,
    'felix': _project_felix,
}


def _run(argv):
    return subprocess.run(argv, capture_output=True, text=True, timeout=SUBPROCESS_TIMEOUT)


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _j(page, limit, path, token_present, start, end, rc, cause, received, validated):
    return {'page': page, 'limit': limit, 'path': path, 'continue': token_present,
            'start': start, 'end': end, 'returncode': rc, 'cause': cause,
            'received': received, 'validated': validated}


def _list_pages(rid, path, ctx, run_fn):
    kind, api = LIST_ENVELOPE[rid]
    journal = []
    items = []
    token = None
    rv = None
    seen = set()
    last_rc = None
    for page in range(MAX_PAGES):
        limit = PAGE_LIMIT if page < MAX_PAGES - 1 else PAGE_LIMIT_LAST
        p = path + '?limit=%d' % limit
        if token is not None:
            p += '&continue=' + quote(token, safe='')
        argv = ['kubectl', '--context', ctx, '--request-timeout=' + REQUEST_TIMEOUT, 'get', '--raw', p]
        start = _now()
        result = None
        try:
            result = run_fn(argv)
        except subprocess.TimeoutExpired:
            journal.append(_j(page, limit, path, token is not None, start, _now(), None, 'TIMEOUT', None, None))
            if page == 0:
                return {'items': [], 'complete': False, 'category': 'TIMEOUT', 'reason': 'timeout',
                        'returncode': None, 'journal': journal}
            return {'items': items, 'complete': False, 'category': 'PARTIAL', 'reason': 'timeout after page',
                    'returncode': last_rc, 'journal': journal}
        except OSError:
            journal.append(_j(page, limit, path, token is not None, start, _now(), None, 'GET_FAILED', None, None))
            if page == 0:
                return {'items': [], 'complete': False, 'category': 'GET_FAILED', 'reason': 'os error',
                        'returncode': None, 'journal': journal}
            return {'items': items, 'complete': False, 'category': 'PARTIAL', 'reason': 'os error after page',
                    'returncode': last_rc, 'journal': journal}
        rc = result.returncode if result is not None else None
        last_rc = rc
        if rc != 0:
            cause = classify(rc, result.stderr if result is not None else '', False)
            journal.append(_j(page, limit, path, token is not None, start, _now(), rc, cause, None, None))
            if page == 0:
                return {'items': [], 'complete': False, 'category': cause, 'reason': cause,
                        'returncode': rc, 'journal': journal}
            return {'items': items, 'complete': False, 'category': 'PARTIAL',
                    'reason': 'next-page ' + (cause or 'GET_FAILED'), 'returncode': rc, 'journal': journal}
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            journal.append(_j(page, limit, path, token is not None, start, _now(), rc, 'invalid JSON', None, None))
            return {'items': [], 'complete': False, 'category': 'PARSE_ERROR', 'reason': 'invalid JSON',
                    'returncode': rc, 'journal': journal}
        if not isinstance(data, dict) or data.get('kind') != kind or data.get('apiVersion') != api:
            journal.append(_j(page, limit, path, token is not None, start, _now(), rc, 'envelope mismatch', None, None))
            return {'items': [], 'complete': False, 'category': 'PARSE_ERROR', 'reason': 'envelope mismatch',
                    'returncode': rc, 'journal': journal}
        meta = data.get('metadata')
        if not isinstance(meta, dict):
            journal.append(_j(page, limit, path, token is not None, start, _now(), rc, 'metadata not object', None, None))
            return {'items': [], 'complete': False, 'category': 'PARSE_ERROR', 'reason': 'metadata not object',
                    'returncode': rc, 'journal': journal}
        new_rv = meta.get('resourceVersion')
        if not isinstance(new_rv, str) or new_rv == '':
            journal.append(_j(page, limit, path, token is not None, start, _now(), rc, 'invalid resourceVersion', None, None))
            return {'items': [], 'complete': False, 'category': 'PARSE_ERROR', 'reason': 'invalid resourceVersion',
                    'returncode': rc, 'journal': journal}
        if rv is not None and new_rv != rv:
            journal.append(_j(page, limit, path, token is not None, start, _now(), rc, 'resourceVersion changed', None, None))
            return {'items': items, 'complete': False, 'category': 'PARTIAL', 'reason': 'resourceVersion changed',
                    'returncode': rc, 'journal': journal}
        rv = new_rv
        if 'continue' in meta:
            cont = meta['continue']
            if cont is None:
                journal.append(_j(page, limit, path, token is not None, start, _now(), rc, 'continue null', None, None))
                return {'items': [], 'complete': False, 'category': 'PARSE_ERROR', 'reason': 'continue null',
                        'returncode': rc, 'journal': journal}
            if not isinstance(cont, str):
                journal.append(_j(page, limit, path, token is not None, start, _now(), rc, 'continue not string', None, None))
                return {'items': [], 'complete': False, 'category': 'PARSE_ERROR', 'reason': 'continue not string',
                        'returncode': rc, 'journal': journal}
            if cont == '':
                cont = None
        else:
            cont = None
        page_items = data.get('items')
        if not isinstance(page_items, list):
            journal.append(_j(page, limit, path, token is not None, start, _now(), rc, 'items not list', None, None))
            return {'items': [], 'complete': False, 'category': 'PARSE_ERROR', 'reason': 'items not list',
                    'returncode': rc, 'journal': journal}
        received = len(page_items)
        for it in page_items:
            if not isinstance(it, dict):
                journal.append(_j(page, limit, path, token is not None, start, _now(), rc, 'item not object', received, None))
                return {'items': [], 'complete': False, 'category': 'PARSE_ERROR', 'reason': 'item not object',
                        'returncode': rc, 'journal': journal}
        items.extend(page_items)
        validated = len(items)
        if validated > TOTAL_CAP:
            journal.append(_j(page, limit, path, token is not None, start, _now(), rc, 'over cap', received, validated))
            return {'items': items[:TOTAL_CAP], 'complete': False, 'category': 'PARTIAL', 'reason': 'over cap',
                    'returncode': rc, 'journal': journal}
        if received > limit:
            journal.append(_j(page, limit, path, token is not None, start, _now(), rc, 'page overlong', received, validated))
            return {'items': items, 'complete': False, 'category': 'PARTIAL', 'reason': 'page overlong',
                    'returncode': rc, 'journal': journal}
        journal.append(_j(page, limit, path, token is not None, start, _now(), rc, None, received, validated))
        if cont is None:
            return {'items': items, 'complete': True, 'category': None, 'reason': None,
                    'returncode': rc, 'journal': journal}
        if cont in seen:
            journal.append(_j(page, limit, path, token is not None, start, _now(), rc, 'repeated token', received, validated))
            return {'items': items, 'complete': False, 'category': 'PARTIAL', 'reason': 'repeated continue token',
                    'returncode': rc, 'journal': journal}
        seen.add(cont)
        token = cont
    return {'items': items, 'complete': False, 'category': 'PARTIAL', 'reason': 'cap reached',
            'returncode': last_rc, 'journal': journal}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--context', required=True)
    p.add_argument('--output', required=True)
    args = p.parse_args()
    if args.context != CTX:
        raise SystemExit('BLOCKED: unexpected context (approved: %s)' % CTX)
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
                                      'output': '', 'complete': None, 'end': _now()},
                                     allow_nan=False) + '\n')
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
                res = _list_pages(rid, path, args.context, _run)
                journal = res['journal']
                category = res['category']
                complete = res['complete']
                reason = res['reason']
                exit_code = res.get('returncode')
                output = ''
                if res['items']:
                    try:
                        output = json.dumps([PROJECTOR[entry['proj']](it) for it in res['items']],
                                            allow_nan=False)
                    except UnsupportedField:
                        category, output = 'UNSUPPORTED', ''
                    except (json.JSONDecodeError, ValueError, KeyError, TypeError):
                        category, output = 'PARSE_ERROR', ''
                if category is not None:
                    complete = False
                log.write(json.dumps({'id': rid, 'start': start, 'argv': argv,
                                      'exit': exit_code, 'category': category, 'output': output,
                                      'complete': complete, 'reason': reason, 'journal': journal,
                                      'continuation_redacted': len(journal) > 1,
                                      'end': _now()}, allow_nan=False) + '\n')
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
            verdicts = None
            if ok:
                try:
                    kind = entry['kind']
                    if kind == 'discovery':
                        output, verdicts = _project_d1(result.stdout)
                    elif kind == 'podlist':
                        data = json.loads(result.stdout)
                        if not isinstance(data, dict) or data.get('kind') != 'PodList' or data.get('apiVersion') != 'v1':
                            raise ValueError('pod list envelope mismatch')
                        meta = data.get('metadata')
                        if not isinstance(meta, dict):
                            raise ValueError('pod list metadata not an object')
                        rv = meta.get('resourceVersion')
                        if not isinstance(rv, str) or rv == '':
                            raise ValueError('pod list resourceVersion must be nonempty string')
                        if 'continue' in meta:
                            cont = meta['continue']
                            if cont is None:
                                raise ValueError('pod list continue cannot be null')
                            if not isinstance(cont, str):
                                raise ValueError('pod list continue must be string')
                            if cont:
                                raise ValueError('pod list incomplete (continue present)')
                        items = data.get('items')
                        if not isinstance(items, list):
                            raise ValueError('items not a list')
                        proj = []
                        for it in items:
                            if not isinstance(it, dict):
                                raise ValueError('item not an object')
                            proj.append(project_pod_identity(it, 'kube-system'))
                        output = json.dumps(proj, allow_nan=False)
                        verify_calico_identity(proj)
                        complete = True
                    elif kind == 'crd':
                        proj = project_crd_schema(result.stdout)
                        if not proj['compatible']:
                            unsupported = True
                        output = json.dumps(proj, allow_nan=False)
                    elif kind == 'single':
                        data = json.loads(result.stdout)
                        if not isinstance(data, dict):
                            raise ValueError('expected single object')
                        output = json.dumps(PROJECTOR[entry['proj']](data), allow_nan=False)
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
                                          'complete': False, 'end': _now()}, allow_nan=False) + '\n')
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
            if verdicts is not None:
                for rname, vok in verdicts.items():
                    if vok:
                        ok_ids.add('D1:' + rname)
            log.write(json.dumps({'id': rid, 'start': start, 'argv': argv,
                                  'exit': None if result is None else result.returncode,
                                  'category': category, 'output': output, 'complete': complete,
                                  'end': _now()}, allow_nan=False) + '\n')
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
