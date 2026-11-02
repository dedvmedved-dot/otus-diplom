#!/usr/bin/env python3
"""Offline tests for followup.py (F-D1..F-TIER), FU-01..08 corrective suite."""
import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from collections import defaultdict
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import followup as fw  # noqa: E402
import yaml  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(HERE))

CANARY = "SYNTHETIC_FOLLOWUP_CANARY_NOT_A_SECRET"
PINNED_HEX = "f4fafd8ba641d96c5a91b01e5a519117d77d55dee789a3562ba3ad4aa125b36a"
AMD64_CONFIG_HEX = "6bc9fa4dc2b10ca1d4b97a1cd570036651898cea8b3c3bcbb1d55cf813e43f65"

CONTRACT = json.load(open(os.path.join(HERE, 'followup-typed-contract.json')))
CNP_SPEC = CONTRACT['cnp']['spec_schema']


def route(tail):
    if len(tail) >= 3 and tail[0] == 'get' and tail[1] == '--raw':
        return tuple(['get', '--raw', tail[2].split('?')[0]])
    return tuple(tail)


CMDS = {route(tuple(r['argv'])): r['id'] for r in fw.READS}


def podlist(pods, continue_token=None, kind='PodList', api='v1'):
    meta = {'resourceVersion': 'rv1'}
    if continue_token is not None:
        meta['continue'] = continue_token
    return json.dumps({'kind': kind, 'apiVersion': api, 'metadata': meta, 'items': pods})


def page(rid, items, continue_token=None, rv='rv1'):
    kind, api = fw.LIST_ENVELOPE[rid]
    meta = {'resourceVersion': rv}
    if continue_token is not None:
        meta['continue'] = continue_token
    return json.dumps({'kind': kind, 'apiVersion': api, 'metadata': meta, 'items': items})


def objects(obj, n, offset=0):
    out = []
    for i in range(n):
        x = copy.deepcopy(obj)
        x['metadata']['name'] = x['metadata']['name'] + '-%d' % (offset + i)
        out.append(x)
    return out


CALICO_DISC = {'kind': 'APIResourceList', 'groupVersion': 'crd.projectcalico.org/v1', 'resources': [
    {'name': 'networkpolicies', 'kind': 'NetworkPolicy', 'namespaced': True, 'verbs': ['get', 'list']},
    {'name': 'globalnetworkpolicies', 'kind': 'GlobalNetworkPolicy', 'namespaced': False, 'verbs': ['get', 'list']},
    {'name': 'felixconfigurations', 'kind': 'FelixConfiguration', 'namespaced': False, 'verbs': ['get']},
    {'name': 'hostendpoints', 'kind': 'HostEndpoint', 'namespaced': False, 'verbs': ['get', 'list']},
    {'name': 'tiers', 'kind': 'Tier', 'namespaced': False, 'verbs': ['get', 'list']},
]}

POD = {'apiVersion': 'v1', 'kind': 'Pod', 'metadata': {'name': 'calico-node-abc', 'namespace': 'kube-system'},
       'spec': {'initContainers': [], 'containers': [{'name': 'calico-node', 'image': 'quay.io/calico/node:v3.32.0', 'ports': []}]},
       'status': {'containerStatuses': [{'name': 'calico-node', 'imageID': 'containerd://sha256:' + PINNED_HEX}]}}

POD_CFG = {'apiVersion': 'v1', 'kind': 'Pod', 'metadata': {'name': 'calico-node-def', 'namespace': 'kube-system'},
           'spec': {'initContainers': [], 'containers': [{'name': 'calico-node', 'image': 'quay.io/calico/node:v3.32.0', 'ports': []}]},
           'status': {'containerStatuses': [{'name': 'calico-node', 'imageID': 'sha256:' + AMD64_CONFIG_HEX}]}}

POD_DIGEST = {'apiVersion': 'v1', 'kind': 'Pod', 'metadata': {'name': 'calico-node-ghi', 'namespace': 'kube-system'},
              'spec': {'initContainers': [], 'containers': [{'name': 'calico-node', 'image': 'quay.io/calico/node@sha256:' + PINNED_HEX, 'ports': []}]},
              'status': {'containerStatuses': [{'name': 'calico-node', 'imageID': 'docker-pullable://sha256:' + PINNED_HEX}]}}

CRD = {'apiVersion': 'apiextensions.k8s.io/v1', 'kind': 'CustomResourceDefinition',
       'metadata': {'name': 'clusternetworkpolicies.policy.networking.k8s.io'},
       'spec': {'group': 'policy.networking.k8s.io',
                'names': {'kind': 'ClusterNetworkPolicy', 'plural': 'clusternetworkpolicies'},
                'scope': 'Cluster',
                'versions': [{'name': 'v1alpha2', 'served': True,
                              'schema': {'openAPIV3Schema': {'type': 'object', 'properties': {'spec': CNP_SPEC}}}}]}}

CNP = {'apiVersion': 'policy.networking.k8s.io/v1alpha2', 'kind': 'ClusterNetworkPolicy',
       'metadata': {'name': 'allow-portal'},
       'spec': {'tier': 'Admin', 'priority': 10,
                'subject': {'namespaces': {'matchLabels': {'name': 'portal'}}},
                'ingress': [{'action': 'Accept',
                             'from': [{'namespaces': {'matchLabels': {'name': 'portal'}}}],
                             'protocols': [{'tcp': {'destinationPort': {'number': 5432}}}]}],
                'egress': [{'action': 'Accept',
                            'to': [{'networks': ['10.244.0.0/24']}],
                            'protocols': [{'udp': {'destinationPort': {'range': {'start': 53, 'end': 54}}}}]}]}}

NP = {'apiVersion': 'crd.projectcalico.org/v1', 'kind': 'NetworkPolicy',
      'metadata': {'name': 'n', 'namespace': 'portal'},
      'spec': {'selector': 'all()', 'ingress': [{'action': 'Allow', 'source': {'selector': 'x'}}], 'types': ['Ingress']}}

GNP = {'apiVersion': 'crd.projectcalico.org/v1', 'kind': 'GlobalNetworkPolicy',
       'metadata': {'name': 'gnp'}, 'spec': {'selector': 'all()', 'order': 10, 'applyOnForward': True}}

FELIX = {'apiVersion': 'crd.projectcalico.org/v1', 'kind': 'FelixConfiguration',
         'metadata': {'name': 'default'}, 'spec': {'bpfEnabled': False, 'nftablesMode': 'Auto'}}

HEP = {'apiVersion': 'crd.projectcalico.org/v1', 'kind': 'HostEndpoint',
       'metadata': {'name': 'node01-eth0', 'labels': {'kubernetes.io/hostname': 'node-01'}},
       'spec': {'node': 'node-01', 'interfaceName': 'eth0', 'expectedIPs': ['172.30.140.101'],
                'profiles': ['default'], 'ports': [{'name': 'k8s', 'port': 6443, 'protocol': 'TCP'}]}}

TIER = {'apiVersion': 'crd.projectcalico.org/v1', 'kind': 'Tier',
        'metadata': {'name': 'security'}, 'spec': {'order': 100, 'defaultAction': 'Pass'}}


class R:
    def __init__(self, returncode=0, stdout='', stderr=''):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class RunMock:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []
        self.pages = defaultdict(int)

    def __call__(self, argv, **kw):
        rid = CMDS[route(tuple(argv[4:]))]
        self.calls.append((rid, list(argv)))
        ans = self.responses.get(rid)
        if isinstance(ans, list):
            idx = min(self.pages[rid], len(ans) - 1)
            self.pages[rid] += 1
            ans = ans[idx]
        else:
            self.pages[rid] += 1
        if isinstance(ans, BaseException):
            raise ans
        return ans


def run(overrides=None, ctx=None):
    overrides = overrides or {}
    defaults = {
        'F-D1': R(0, json.dumps(CALICO_DISC)),
        'F-I1': R(0, podlist([POD])),
        'F-CS': R(0, json.dumps(CRD)),
        'F-CNP': [R(0, page('F-CNP', [CNP]))],
        'F-NP': [R(0, page('F-NP', [NP]))],
        'F-GNP': [R(0, page('F-GNP', [GNP]))],
        'F-FELIX': R(0, json.dumps(FELIX)),
        'F-HEP': [R(0, page('F-HEP', [HEP]))],
        'F-TIER': [R(0, page('F-TIER', [TIER]))],
    }
    responses = dict(defaults)
    responses.update(overrides)
    mrun = RunMock(responses)
    tmp = tempfile.mkdtemp()
    outdir = os.path.join(tmp, 'out')
    with mock.patch.object(shutil, 'which', return_value='/mock/kubectl'), \
         mock.patch.object(subprocess, 'run', side_effect=mrun), \
         mock.patch.object(fw.sys, 'argv', ['followup.py', '--context', ctx or fw.CTX, '--output', outdir]):
        rc = fw.main()
    with open(os.path.join(outdir, 'followup.jsonl')) as _fh:
        rows = [json.loads(l) for l in _fh]
    return rc, mrun.calls, rows


def by_id(rows):
    return {r['id']: r for r in rows}


class TestContext(unittest.TestCase):
    def test_wrong_context_rejected_before_calls(self):
        tmp = tempfile.mkdtemp()
        outdir = os.path.join(tmp, 'out')
        mrun = RunMock({})
        with mock.patch.object(shutil, 'which', return_value='/mock/kubectl'), \
             mock.patch.object(subprocess, 'run', side_effect=mrun), \
             mock.patch.object(fw.sys, 'argv', ['followup.py', '--context', 'another-context', '--output', outdir]):
            with self.assertRaises(SystemExit):
                fw.main()
        self.assertEqual(mrun.calls, [])
        self.assertFalse(os.path.exists(outdir))

    def test_approved_context_positive(self):
        rc, calls, rows = run()
        self.assertEqual(rc, 0)
        self.assertEqual(len(rows), 9)
        contexts = set(c[1][2] for c in calls)
        self.assertEqual(contexts, {fw.CTX})


class TestHappyPath(unittest.TestCase):
    def test_all_ok(self):
        rc, calls, rows = run()
        self.assertEqual(rc, 0)
        for r in rows:
            self.assertIsNone(r['category'], r['id'])
        np_argv = [c[1] for c in calls if c[0] == 'F-NP'][0]
        self.assertIn('?limit=200', np_argv[6])

    def test_three_synthetic_pod_identity_formats(self):
        # SYNTHETIC fixture (POD/POD_CFG/POD_DIGEST) — format coverage only, not the
        # archived observed Pods (see TestRemainingContract.test_real_archived_identity_mapping).
        rc, _, rows = run({'F-I1': R(0, podlist([POD, POD_CFG, POD_DIGEST]))})
        self.assertEqual(rc, 0)
        self.assertIsNone(by_id(rows)['F-I1']['category'])

    def test_cnp_projection(self):
        _, _, rows = run()
        cnp = json.loads(by_id(rows)['F-CNP']['output'])[0]
        self.assertEqual(cnp['spec']['tier'], 'Admin')
        self.assertEqual(cnp['spec']['egress'][0]['to'][0]['networks'], ['10.244.0.0/24'])

    def test_cs_output(self):
        _, _, rows = run()
        cs = json.loads(by_id(rows)['F-CS']['output'])
        self.assertTrue(cs['compatible'])
        self.assertEqual(cs['spec_schema_sha256'], fw.CNP_SPEC_SHA256)


class TestIdentity(unittest.TestCase):
    def test_config_digest_prefix_rejected(self):
        p = copy.deepcopy(POD_CFG)
        p['status']['containerStatuses'][0]['imageID'] = 'containerd://sha256:' + AMD64_CONFIG_HEX
        rc, calls, rows = run({'F-I1': R(0, podlist([p]))})
        self.assertNotEqual(rc, 0)
        self.assertEqual(by_id(rows)['F-I1']['category'], 'UNSUPPORTED')
        for dep in ('F-NP', 'F-GNP', 'F-FELIX', 'F-HEP', 'F-TIER'):
            self.assertEqual(by_id(rows)[dep]['category'], 'BLOCKED_NOT_EXECUTED')

    def test_wrong_registry_rejected(self):
        p = copy.deepcopy(POD)
        p['spec']['containers'][0]['image'] = 'quay.io/calico/node:v3.31.0'
        rc, _, rows = run({'F-I1': R(0, podlist([p]))})
        self.assertNotEqual(rc, 0)
        self.assertEqual(by_id(rows)['F-I1']['category'], 'UNSUPPORTED')

    def test_empty_pods_rejected(self):
        rc, _, rows = run({'F-I1': R(0, podlist([]))})
        self.assertNotEqual(rc, 0)
        self.assertEqual(by_id(rows)['F-I1']['category'], 'UNSUPPORTED')


class TestDiscovery(unittest.TestCase):
    def test_wrong_scope_kind_verb(self):
        for mutate in [
            lambda d: d['resources'][4].update(namespaced=True),
            lambda d: d['resources'][3].update(kind='Wrong'),
            lambda d: d['resources'][0].update(verbs=['get']),
        ]:
            d = copy.deepcopy(CALICO_DISC)
            mutate(d)
            rc, calls, rows = run({'F-D1': R(0, json.dumps(d))})
            self.assertNotEqual(rc, 0)

    def test_missing_tier_blocks_only_tier(self):
        d = copy.deepcopy(CALICO_DISC)
        d['resources'] = [x for x in d['resources'] if x['name'] != 'tiers']
        rc, calls, rows = run({'F-D1': R(0, json.dumps(d))})
        self.assertNotEqual(rc, 0)
        executed = [c[0] for c in calls]
        self.assertIn('F-NP', executed)
        self.assertIn('F-GNP', executed)
        self.assertIn('F-FELIX', executed)
        self.assertIn('F-HEP', executed)
        self.assertNotIn('F-TIER', executed)
        self.assertEqual(by_id(rows)['F-TIER']['category'], 'BLOCKED_NOT_EXECUTED')


class TestCRDSchema(unittest.TestCase):
    def test_served_string_false(self):
        c = copy.deepcopy(CRD)
        c['spec']['versions'][0]['served'] = 'false'
        rc, calls, rows = run({'F-CS': R(0, json.dumps(c))})
        self.assertNotEqual(rc, 0)
        self.assertEqual(by_id(rows)['F-CS']['category'], 'PARSE_ERROR')
        self.assertNotIn('F-CNP', [x[0] for x in calls])

    def test_malformed_version_entry(self):
        c = copy.deepcopy(CRD)
        c['spec']['versions'].append(None)
        rc, _, rows = run({'F-CS': R(0, json.dumps(c))})
        self.assertNotEqual(rc, 0)
        self.assertEqual(by_id(rows)['F-CS']['category'], 'PARSE_ERROR')

    def test_schema_annotation_description_still_compatible(self):
        c = copy.deepcopy(CRD)
        c['spec']['versions'][0]['schema']['openAPIV3Schema']['properties']['spec']['description'] = 'wording'
        rc, _, rows = run({'F-CS': R(0, json.dumps(c))})
        self.assertEqual(rc, 0)
        self.assertTrue(json.loads(by_id(rows)['F-CS']['output'])['compatible'])

    def test_schema_semantic_description_property_mismatch(self):
        c = copy.deepcopy(CRD)
        c['spec']['versions'][0]['schema']['openAPIV3Schema']['properties']['spec']['properties']['description'] = {'type': 'string'}
        rc, calls, rows = run({'F-CS': R(0, json.dumps(c))})
        self.assertNotEqual(rc, 0)
        self.assertEqual(by_id(rows)['F-CS']['category'], 'UNSUPPORTED')
        self.assertFalse(json.loads(by_id(rows)['F-CS']['output'])['compatible'])
        self.assertNotIn('F-CNP', [x[0] for x in calls])

    def test_malformed_parse_error_no_raw(self):
        bad = {'apiVersion': 'apiextensions.k8s.io/v1', 'kind': 'CustomResourceDefinition',
               'metadata': {'name': 'clusternetworkpolicies.policy.networking.k8s.io',
                            'annotations': {'leak': CANARY}},
               'spec': {'group': 'policy.networking.k8s.io',
                        'names': {'kind': 'ClusterNetworkPolicy', 'plural': 'clusternetworkpolicies'},
                        'scope': 'Namespaced',
                        'versions': [{'name': 'v1alpha2', 'served': True}]}}
        rc, _, rows = run({'F-CS': R(0, json.dumps(bad))})
        self.assertNotEqual(rc, 0)
        self.assertEqual(by_id(rows)['F-CS']['category'], 'PARSE_ERROR')
        self.assertEqual(by_id(rows)['F-CS']['output'], '')
        self.assertNotIn(CANARY, json.dumps(rows))


class TestCNP(unittest.TestCase):
    def _cnp(self, mutate):
        c = copy.deepcopy(CNP)
        mutate(c)
        return R(0, page('F-CNP', [c]))

    def test_unknown_semantic_field(self):
        c = copy.deepcopy(CNP)
        c['spec']['ingress'][0]['bogusField'] = 'x'
        rc, _, rows = run({'F-CNP': [R(0, page('F-CNP', [c]))]})
        self.assertNotEqual(rc, 0)
        self.assertEqual(by_id(rows)['F-CNP']['category'], 'UNSUPPORTED')

    def test_priority_bounds(self):
        rc, _, rows = run({'F-CNP': self._cnp(lambda c: c['spec'].update(priority=1001))})
        self.assertEqual(by_id(rows)['F-CNP']['category'], 'PARSE_ERROR')

    def test_port_range_start_ge_end(self):
        rc, _, rows = run({'F-CNP': self._cnp(
            lambda c: c['spec']['egress'][0]['protocols'][0]['udp']['destinationPort'].update(range={'start': 60, 'end': 60}))})
        self.assertEqual(by_id(rows)['F-CNP']['category'], 'PARSE_ERROR')

    def test_bad_action_enum(self):
        rc, _, rows = run({'F-CNP': self._cnp(lambda c: c['spec']['ingress'][0].update(action='Allow'))})
        self.assertEqual(by_id(rows)['F-CNP']['category'], 'PARSE_ERROR')

    def test_host_bits_cidr_ipv4_accepted(self):
        rc, _, rows = run({'F-CNP': self._cnp(
            lambda c: c['spec']['egress'][0].update(to=[{'networks': ['10.244.0.5/24']}]))})
        self.assertIsNone(by_id(rows)['F-CNP']['category'])
        self.assertIn('10.244.0.5/24', by_id(rows)['F-CNP']['output'])

    def test_host_bits_cidr_ipv6_accepted(self):
        rc, _, rows = run({'F-CNP': self._cnp(
            lambda c: c['spec']['egress'][0].update(to=[{'networks': ['2001:db8::5/64']}]))})
        self.assertIsNone(by_id(rows)['F-CNP']['category'])
        self.assertIn('2001:db8::5/64', by_id(rows)['F-CNP']['output'])

    def test_malformed_cidr_rejected(self):
        for bad in ['not-a-cidr', '999.1.1.1/24', '10.244.0.0/33']:
            with self.subTest(bad=bad):
                rc, _, rows = run({'F-CNP': self._cnp(
                    lambda c: c['spec']['egress'][0].update(to=[{'networks': [bad]}]))})
                self.assertEqual(by_id(rows)['F-CNP']['category'], 'PARSE_ERROR')

    def test_bare_ip_not_cidr_rejected(self):
        rc, _, rows = run({'F-CNP': self._cnp(
            lambda c: c['spec']['egress'][0].update(to=[{'networks': ['10.244.0.5']}]))})
        self.assertEqual(by_id(rows)['F-CNP']['category'], 'PARSE_ERROR')

    def test_named_port_ingress(self):
        rc, _, rows = run({'F-CNP': self._cnp(
            lambda c: c['spec']['ingress'][0].update(protocols=[{'destinationNamedPort': 'postgres'}]))})
        self.assertIsNone(by_id(rows)['F-CNP']['category'])
        self.assertIn('destinationNamedPort', by_id(rows)['F-CNP']['output'])

    def test_named_port_egress(self):
        rc, _, rows = run({'F-CNP': self._cnp(
            lambda c: c['spec']['egress'][0].update(protocols=[{'destinationNamedPort': 'postgres'}]))})
        self.assertIsNone(by_id(rows)['F-CNP']['category'])
        self.assertIn('destinationNamedPort', by_id(rows)['F-CNP']['output'])

    def test_named_port_wrong_type(self):
        rc, _, rows = run({'F-CNP': self._cnp(
            lambda c: c['spec']['ingress'][0].update(protocols=[{'destinationNamedPort': 123}]))})
        self.assertEqual(by_id(rows)['F-CNP']['category'], 'PARSE_ERROR')

    def test_named_port_null(self):
        rc, _, rows = run({'F-CNP': self._cnp(
            lambda c: c['spec']['ingress'][0].update(protocols=[{'destinationNamedPort': None}]))})
        self.assertEqual(by_id(rows)['F-CNP']['category'], 'PARSE_ERROR')

    def test_named_port_union_conflict(self):
        rc, _, rows = run({'F-CNP': self._cnp(
            lambda c: c['spec']['ingress'][0].update(protocols=[{'destinationNamedPort': 'p', 'tcp': {'destinationPort': {'number': 1}}}]))})
        self.assertEqual(by_id(rows)['F-CNP']['category'], 'PARSE_ERROR')

    def test_subject_two_fields(self):
        c = copy.deepcopy(CNP)
        c['spec']['subject'] = {'namespaces': {'matchLabels': {}}, 'pods': {'podSelector': {}}}
        rc, _, rows = run({'F-CNP': [R(0, page('F-CNP', [c]))]})
        self.assertEqual(by_id(rows)['F-CNP']['category'], 'PARSE_ERROR')

    def test_subject_null(self):
        rc, _, rows = run({'F-CNP': self._cnp(lambda c: c['spec'].update(subject={'namespaces': None}))})
        self.assertEqual(by_id(rows)['F-CNP']['category'], 'PARSE_ERROR')

    def test_peer_null(self):
        rc, _, rows = run({'F-CNP': self._cnp(
            lambda c: c['spec']['ingress'][0].update(**{'from': [{'namespaces': None}]}))})
        self.assertEqual(by_id(rows)['F-CNP']['category'], 'PARSE_ERROR')

    def test_protocols_null(self):
        rc, _, rows = run({'F-CNP': self._cnp(lambda c: c['spec']['ingress'][0].update(protocols=None))})
        self.assertEqual(by_id(rows)['F-CNP']['category'], 'PARSE_ERROR')

    def test_namespace_selector_null(self):
        rc, _, rows = run({'F-CNP': self._cnp(
            lambda c: c['spec'].update(subject={'pods': {'podSelector': {}, 'namespaceSelector': None}}))})
        self.assertEqual(by_id(rows)['F-CNP']['category'], 'PARSE_ERROR')

    def test_ingress_wrong_direction_unsupported(self):
        rc, _, rows = run({'F-CNP': self._cnp(
            lambda c: c['spec']['ingress'][0].update(to=[{'networks': ['0.0.0.0/0']}]))})
        self.assertEqual(by_id(rows)['F-CNP']['category'], 'UNSUPPORTED')

    def test_duplicate_networks(self):
        rc, _, rows = run({'F-CNP': self._cnp(
            lambda c: c['spec']['egress'][0].update(to=[{'networks': ['10.0.0.0/8', '10.0.0.0/8']}]))})
        self.assertEqual(by_id(rows)['F-CNP']['category'], 'PARSE_ERROR')

    def test_selector_explicit_null_values(self):
        rc, _, rows = run({'F-CNP': self._cnp(
            lambda c: c['spec'].update(subject={'namespaces': {
                'matchExpressions': [{'key': 'x', 'operator': 'Exists', 'values': None}]}}))})
        self.assertEqual(by_id(rows)['F-CNP']['category'], 'PARSE_ERROR')


class TestHEP(unittest.TestCase):
    def test_valid_preserved(self):
        _, _, rows = run()
        hep = json.loads(by_id(rows)['F-HEP']['output'])[0]
        self.assertEqual(hep['metadata']['labels'], {'kubernetes.io/hostname': 'node-01'})
        self.assertEqual(hep['spec']['ports'], [{'name': 'k8s', 'port': 6443, 'protocol': 'TCP'}])

    def test_missing_node(self):
        h = copy.deepcopy(HEP)
        h['spec'].pop('node')
        rc, _, rows = run({'F-HEP': [R(0, page('F-HEP', [h]))]})
        self.assertEqual(by_id(rows)['F-HEP']['category'], 'PARSE_ERROR')

    def test_empty_interface_and_ips(self):
        h = copy.deepcopy(HEP)
        h['spec']['interfaceName'] = ''
        h['spec']['expectedIPs'] = []
        rc, _, rows = run({'F-HEP': [R(0, page('F-HEP', [h]))]})
        self.assertEqual(by_id(rows)['F-HEP']['category'], 'PARSE_ERROR')

    def test_null_profiles(self):
        h = copy.deepcopy(HEP)
        h['spec']['profiles'] = None
        rc, _, rows = run({'F-HEP': [R(0, page('F-HEP', [h]))]})
        self.assertEqual(by_id(rows)['F-HEP']['category'], 'PARSE_ERROR')

    def test_duplicate_profiles(self):
        h = copy.deepcopy(HEP)
        h['spec']['profiles'] = ['a', 'a']
        rc, _, rows = run({'F-HEP': [R(0, page('F-HEP', [h]))]})
        self.assertEqual(by_id(rows)['F-HEP']['category'], 'PARSE_ERROR')

    def test_empty_port_name_accepted(self):
        h = copy.deepcopy(HEP)
        h['spec']['ports'][0]['name'] = ''
        rc, _, rows = run({'F-HEP': [R(0, page('F-HEP', [h]))]})
        self.assertEqual(rc, 0)
        hep = json.loads(by_id(rows)['F-HEP']['output'])[0]
        self.assertEqual(hep['spec']['ports'][0]['name'], '')

    def test_unknown_spec_key(self):
        h = copy.deepcopy(HEP)
        h['spec']['bogus'] = 1
        rc, _, rows = run({'F-HEP': [R(0, page('F-HEP', [h]))]})
        self.assertEqual(by_id(rows)['F-HEP']['category'], 'UNSUPPORTED')


class TestTier(unittest.TestCase):
    def test_default_action_preserved(self):
        _, _, rows = run()
        tier = json.loads(by_id(rows)['F-TIER']['output'])[0]
        self.assertEqual(tier['spec']['defaultAction'], 'Pass')

    def test_absent_vs_observed(self):
        t = copy.deepcopy(TIER)
        t['spec'].pop('defaultAction')
        rc, _, rows = run({'F-TIER': [R(0, page('F-TIER', [t]))]})
        self.assertEqual(rc, 0)
        self.assertNotIn('defaultAction', json.loads(by_id(rows)['F-TIER']['output'])[0]['spec'])

    def test_invalid_enum(self):
        t = copy.deepcopy(TIER)
        t['spec']['defaultAction'] = 'Allow'
        rc, _, rows = run({'F-TIER': [R(0, page('F-TIER', [t]))]})
        self.assertEqual(by_id(rows)['F-TIER']['category'], 'PARSE_ERROR')

    def test_labels_preserved(self):
        t = copy.deepcopy(TIER)
        t['metadata']['labels'] = {'purpose': 'preserve'}
        rc, _, rows = run({'F-TIER': [R(0, page('F-TIER', [t]))]})
        self.assertEqual(rc, 0)
        tier = json.loads(by_id(rows)['F-TIER']['output'])[0]
        self.assertEqual(tier['metadata']['labels'], {'purpose': 'preserve'})

    def test_nonfinite_order(self):
        for v in (float('nan'), float('inf')):
            t = copy.deepcopy(TIER)
            t['spec']['order'] = v
            rc, _, rows = run({'F-TIER': [R(0, page('F-TIER', [t]))]})
            self.assertEqual(by_id(rows)['F-TIER']['category'], 'PARSE_ERROR', str(v))


class TestClusterScope(unittest.TestCase):
    def test_cluster_namespace_rejected(self):
        for rid, obj in [('F-CNP', CNP), ('F-GNP', GNP), ('F-HEP', HEP), ('F-TIER', TIER)]:
            o = copy.deepcopy(obj)
            o['metadata']['namespace'] = 'wrong'
            rc, _, rows = run({rid: R(0, page(rid, [o]))})
            self.assertNotEqual(rc, 0, rid)
            self.assertEqual(by_id(rows)[rid]['category'], 'PARSE_ERROR', rid)


class TestPagination(unittest.TestCase):
    def test_empty(self):
        rc, _, rows = run({'F-NP': [R(0, page('F-NP', []))]})
        self.assertEqual(rc, 0)
        self.assertTrue(by_id(rows)['F-NP']['complete'])

    def test_two_pages_complete(self):
        rc, calls, rows = run({'F-NP': [R(0, page('F-NP', [NP], continue_token='tok1')),
                                         R(0, page('F-NP', [NP], continue_token=None))]})
        self.assertEqual(rc, 0)
        self.assertTrue(by_id(rows)['F-NP']['complete'])
        self.assertEqual(len([c for c in calls if c[0] == 'F-NP']), 2)
        journal = by_id(rows)['F-NP']['journal']
        self.assertEqual(len(journal), 2)

    def test_cap_reached_partial(self):
        rc, calls, rows = run({'F-NP': [R(0, page('F-NP', [NP], continue_token='t1')),
                                         R(0, page('F-NP', [NP], continue_token='t2')),
                                         R(0, page('F-NP', [NP], continue_token='t3'))]})
        self.assertNotEqual(rc, 0)
        self.assertEqual(by_id(rows)['F-NP']['category'], 'PARTIAL')
        self.assertFalse(by_id(rows)['F-NP']['complete'])
        self.assertEqual(len([c for c in calls if c[0] == 'F-NP']), 3)

    def test_oversized_501_partial(self):
        rc, _, rows = run({'F-NP': R(0, page('F-NP', objects(NP, 501)))})
        self.assertNotEqual(rc, 0)
        r = by_id(rows)['F-NP']
        self.assertEqual(r['category'], 'PARTIAL')
        self.assertFalse(r['complete'])
        self.assertEqual(r['reason'], 'over cap')

    def test_three_pages_600_partial(self):
        rc, _, rows = run({'F-NP': [R(0, page('F-NP', objects(NP, 200), 'a')),
                                     R(0, page('F-NP', objects(NP, 200), 'b')),
                                     R(0, page('F-NP', objects(NP, 200), None))]})
        self.assertNotEqual(rc, 0)
        self.assertEqual(by_id(rows)['F-NP']['category'], 'PARTIAL')
        self.assertEqual(by_id(rows)['F-NP']['reason'], 'over cap')

    def test_wrong_list_kind(self):
        rc, _, rows = run({'F-NP': R(0, json.dumps({'apiVersion': 'v1', 'kind': 'SecretList',
                                                     'metadata': {'resourceVersion': 'r'}, 'items': []}))})
        self.assertEqual(by_id(rows)['F-NP']['category'], 'PARSE_ERROR')

    def test_missing_metadata(self):
        rc, _, rows = run({'F-NP': R(0, json.dumps({'apiVersion': 'crd.projectcalico.org/v1',
                                                     'kind': 'NetworkPolicyList', 'items': []}))})
        self.assertEqual(by_id(rows)['F-NP']['category'], 'PARSE_ERROR')

    def test_null_rv(self):
        rc, _, rows = run({'F-NP': R(0, json.dumps({'apiVersion': 'crd.projectcalico.org/v1',
                                                     'kind': 'NetworkPolicyList',
                                                     'metadata': {'resourceVersion': None}, 'items': []}))})
        self.assertEqual(by_id(rows)['F-NP']['category'], 'PARSE_ERROR')

    def test_false_continue(self):
        rc, _, rows = run({'F-NP': R(0, json.dumps({'apiVersion': 'crd.projectcalico.org/v1',
                                                     'kind': 'NetworkPolicyList',
                                                     'metadata': {'resourceVersion': 'r', 'continue': False},
                                                     'items': []}))})
        self.assertEqual(by_id(rows)['F-NP']['category'], 'PARSE_ERROR')

    def test_scalar_item(self):
        rc, _, rows = run({'F-NP': R(0, json.dumps({'apiVersion': 'crd.projectcalico.org/v1',
                                                     'kind': 'NetworkPolicyList',
                                                     'metadata': {'resourceVersion': 'r'}, 'items': [None]}))})
        self.assertEqual(by_id(rows)['F-NP']['category'], 'PARSE_ERROR')

    def test_rv_swap_partial(self):
        rc, _, rows = run({'F-NP': [R(0, page('F-NP', [NP], continue_token='t1', rv='rv1')),
                                     R(0, page('F-NP', [NP], continue_token=None, rv='rv2'))]})
        self.assertNotEqual(rc, 0)
        self.assertEqual(by_id(rows)['F-NP']['category'], 'PARTIAL')

    def test_repeated_token_partial(self):
        rc, _, rows = run({'F-NP': [R(0, page('F-NP', [NP], continue_token='t1')),
                                     R(0, page('F-NP', [NP], continue_token='t1')),
                                     R(0, page('F-NP', [NP], continue_token='t1'))]})
        self.assertNotEqual(rc, 0)
        self.assertEqual(by_id(rows)['F-NP']['category'], 'PARTIAL')
        self.assertEqual(by_id(rows)['F-NP']['reason'], 'repeated continue token')


class TestListErrors(unittest.TestCase):
    def test_first_page_forbidden(self):
        rc, _, rows = run({'F-NP': R(1, '', 'forbidden')})
        self.assertNotEqual(rc, 0)
        r = by_id(rows)['F-NP']
        self.assertEqual(r['category'], 'FORBIDDEN')
        self.assertEqual(r['exit'], 1)

    def test_first_page_not_served(self):
        rc, _, rows = run({'F-NP': R(1, '', "the server doesn't have a resource type")})
        self.assertEqual(by_id(rows)['F-NP']['category'], 'API_NOT_SERVED')

    def test_first_page_connection(self):
        rc, _, rows = run({'F-NP': R(1, '', 'connection refused')})
        self.assertEqual(by_id(rows)['F-NP']['category'], 'CONNECTION')

    def test_first_page_timeout(self):
        rc, _, rows = run({'F-NP': subprocess.TimeoutExpired('kubectl', 20)})
        self.assertNotEqual(rc, 0)
        r = by_id(rows)['F-NP']
        self.assertEqual(r['category'], 'TIMEOUT')
        self.assertIsNone(r['exit'])

    def test_later_page_timeout_retains_prefix(self):
        rc, _, rows = run({'F-NP': [R(0, page('F-NP', [NP], 'a')),
                                     subprocess.TimeoutExpired('kubectl', 20)]})
        self.assertNotEqual(rc, 0)
        r = by_id(rows)['F-NP']
        self.assertEqual(r['category'], 'PARTIAL')
        self.assertEqual(r['reason'], 'timeout after page')
        # validated prefix retained
        self.assertEqual(len(json.loads(r['output'])), 1)

    def test_later_page_forbidden(self):
        rc, _, rows = run({'F-NP': [R(0, page('F-NP', [NP], 'a')),
                                     R(1, '', 'forbidden')]})
        self.assertNotEqual(rc, 0)
        r = by_id(rows)['F-NP']
        self.assertEqual(r['category'], 'PARTIAL')
        self.assertIn('FORBIDDEN', r['reason'])


class TestStructuralIsolation(unittest.TestCase):
    def test_scalar_item_does_not_crash(self):
        rc, calls, rows = run({'F-NP': R(0, json.dumps({'apiVersion': 'crd.projectcalico.org/v1',
                                                         'kind': 'NetworkPolicyList',
                                                         'metadata': {'resourceVersion': 'r'},
                                                         'items': [None]}))})
        self.assertNotEqual(rc, 0)
        self.assertEqual(by_id(rows)['F-NP']['category'], 'PARSE_ERROR')
        # independent reads continue
        self.assertIn('F-GNP', [c[0] for c in calls])

    def test_podlist_scalar(self):
        rc, _, rows = run({'F-I1': R(0, 'null')})
        self.assertNotEqual(rc, 0)
        self.assertEqual(by_id(rows)['F-I1']['category'], 'PARSE_ERROR')

    def test_pod_metadata_scalar(self):
        rc, _, rows = run({'F-I1': R(0, json.dumps({'metadata': 'bad', 'items': [POD]}))})
        self.assertNotEqual(rc, 0)
        self.assertEqual(by_id(rows)['F-I1']['category'], 'PARSE_ERROR')

    def test_pod_wrong_list_kind(self):
        rc, _, rows = run({'F-I1': R(0, json.dumps({'kind': 'SecretList', 'apiVersion': 'wrong/v2',
                                                     'metadata': {}, 'items': [POD]}))})
        self.assertNotEqual(rc, 0)
        self.assertEqual(by_id(rows)['F-I1']['category'], 'PARSE_ERROR')


class TestEnv(unittest.TestCase):
    def test_no_kubectl(self):
        tmp = tempfile.mkdtemp()
        outdir = os.path.join(tmp, 'out')
        with mock.patch.object(shutil, 'which', return_value=None), \
             mock.patch.object(fw.sys, 'argv', ['followup.py', '--context', fw.CTX, '--output', outdir]):
            with self.assertRaises(SystemExit):
                fw.main()

    def test_no_overwrite(self):
        tmp = tempfile.mkdtemp()
        outdir = os.path.join(tmp, 'out')
        os.mkdir(outdir)
        with mock.patch.object(shutil, 'which', return_value='/mock/kubectl'), \
             mock.patch.object(subprocess, 'run', side_effect=RunMock({})), \
             mock.patch.object(fw.sys, 'argv', ['followup.py', '--context', fw.CTX, '--output', outdir]):
            with self.assertRaises(FileExistsError):
                fw.main()

    def test_no_raw_annotation_env_credential_leak(self):
        p = copy.deepcopy(POD)
        p['metadata']['annotations'] = {'leak': CANARY}
        p['spec']['containers'][0]['env'] = [{'name': 'SECRET', 'value': CANARY}]
        rc, _, rows = run({'F-I1': R(0, podlist([p]))})
        self.assertNotIn(CANARY, json.dumps(rows))

    def test_no_continue_token_in_output(self):
        rc, _, rows = run({'F-NP': [R(0, page('F-NP', [NP], continue_token='SECRET/TOKEN')),
                                     R(0, page('F-NP', [NP], continue_token=None))]})
        self.assertEqual(rc, 0)
        self.assertNotIn('SECRET/TOKEN', json.dumps(rows))


class TestR1JournalAndExit(unittest.TestCase):
    def test_projector_error_complete_false(self):
        c = copy.deepcopy(CNP)
        c['spec'] = 'bad'
        rc, _, rows = run({'F-CNP': [R(0, page('F-CNP', [c]))]})
        r = by_id(rows)['F-CNP']
        self.assertEqual(r['category'], 'PARSE_ERROR')
        self.assertFalse(r['complete'])
        self.assertEqual(r['exit'], 0)
        self.assertGreaterEqual(len(r['journal']), 1)

    def test_unsupported_projector_complete_false(self):
        c = copy.deepcopy(CNP)
        c['spec']['ingress'][0]['bogusField'] = 'x'
        rc, _, rows = run({'F-CNP': [R(0, page('F-CNP', [c]))]})
        r = by_id(rows)['F-CNP']
        self.assertEqual(r['category'], 'UNSUPPORTED')
        self.assertFalse(r['complete'])
        self.assertEqual(r['output'], '')

    def test_invalid_page_preserves_journal_and_exit(self):
        rc, _, rows = run({'F-NP': [R(0, page('F-NP', [NP], 'tok1')),
                                     R(0, 'not json')]})
        r = by_id(rows)['F-NP']
        self.assertEqual(r['category'], 'PARSE_ERROR')
        self.assertFalse(r['complete'])
        self.assertEqual(r['exit'], 0)
        self.assertEqual(len(r['journal']), 2)
        self.assertEqual(r['journal'][1]['cause'], 'invalid JSON')

    def test_nonfinite_gnp_complete_false(self):
        g = copy.deepcopy(GNP)
        g['spec']['order'] = float('nan')
        rc, _, rows = run({'F-GNP': [R(0, page('F-GNP', [g]))]})
        r = by_id(rows)['F-GNP']
        self.assertEqual(r['category'], 'PARSE_ERROR')
        self.assertFalse(r['complete'])


class TestR2Boundaries(unittest.TestCase):
    def test_continue_null_parse_error(self):
        body = {'kind': 'NetworkPolicyList', 'apiVersion': 'crd.projectcalico.org/v1',
                'metadata': {'resourceVersion': 'r', 'continue': None}, 'items': []}
        rc, _, rows = run({'F-NP': R(0, json.dumps(body))})
        self.assertEqual(by_id(rows)['F-NP']['category'], 'PARSE_ERROR')

    def test_cluster_namespace_null_rejected(self):
        for rid, obj in [('F-CNP', CNP), ('F-GNP', GNP), ('F-HEP', HEP), ('F-TIER', TIER)]:
            o = copy.deepcopy(obj)
            o['metadata']['namespace'] = None
            rc, _, rows = run({rid: R(0, page(rid, [o]))})
            self.assertNotEqual(rc, 0, rid)
            self.assertEqual(by_id(rows)[rid]['category'], 'PARSE_ERROR', rid)

    def test_unbound_identity_retained(self):
        p = copy.deepcopy(POD)
        p['spec']['containers'][0]['image'] = 'quay.io/calico/node:v3.31.0'
        rc, _, rows = run({'F-I1': R(0, podlist([p]))})
        i1 = by_id(rows)['F-I1']
        self.assertEqual(i1['category'], 'UNSUPPORTED')
        self.assertNotEqual(i1['output'], '')
        self.assertIn('calico-node', i1['output'])

    def test_single_page_201_overlong(self):
        rc, _, rows = run({'F-NP': R(0, page('F-NP', objects(NP, 201)))})
        r = by_id(rows)['F-NP']
        self.assertEqual(r['category'], 'PARTIAL')
        self.assertEqual(r['reason'], 'page overlong')
        self.assertFalse(r['complete'])

    def test_two_pages_201_complete(self):
        rc, _, rows = run({'F-NP': [R(0, page('F-NP', objects(NP, 200, 0), 'a')),
                                     R(0, page('F-NP', objects(NP, 1, 200), None))]})
        self.assertEqual(rc, 0)
        self.assertTrue(by_id(rows)['F-NP']['complete'])
        self.assertEqual(len(json.loads(by_id(rows)['F-NP']['output'])), 201)


class TestR3CRDVersions(unittest.TestCase):
    def _crd_versions(self, extra):
        c = copy.deepcopy(CRD)
        c['spec']['versions'].append(extra)
        return R(0, json.dumps(c))

    def test_empty_entry(self):
        rc, _, rows = run({'F-CS': self._crd_versions({})})
        self.assertEqual(by_id(rows)['F-CS']['category'], 'PARSE_ERROR')

    def test_name_null(self):
        rc, _, rows = run({'F-CS': self._crd_versions({'name': None})})
        self.assertEqual(by_id(rows)['F-CS']['category'], 'PARSE_ERROR')

    def test_name_int(self):
        rc, _, rows = run({'F-CS': self._crd_versions({'name': 42})})
        self.assertEqual(by_id(rows)['F-CS']['category'], 'PARSE_ERROR')

    def test_served_bad_string(self):
        rc, _, rows = run({'F-CS': self._crd_versions({'name': 'v1beta1', 'served': 'bad'})})
        self.assertEqual(by_id(rows)['F-CS']['category'], 'PARSE_ERROR')


OBJ = {'F-CNP': CNP, 'F-NP': NP, 'F-GNP': GNP, 'F-HEP': HEP, 'F-TIER': TIER}


class TestFiveListMatrix(unittest.TestCase):
    """Parameterized five-list coverage of the pagination/error matrix."""

    def test_empty_complete(self):
        for rid in OBJ:
            with self.subTest(rid=rid):
                rc, _, rows = run({rid: [R(0, page(rid, []))]})
                self.assertEqual(rc, 0)
                self.assertTrue(by_id(rows)[rid]['complete'])

    def test_one_page_complete(self):
        for rid, obj in OBJ.items():
            with self.subTest(rid=rid):
                rc, _, rows = run({rid: [R(0, page(rid, [obj]))]})
                self.assertEqual(rc, 0)
                self.assertTrue(by_id(rows)[rid]['complete'])

    def test_overlong_201_partial(self):
        for rid, obj in OBJ.items():
            with self.subTest(rid=rid):
                rc, _, rows = run({rid: R(0, page(rid, objects(obj, 201)))})
                r = by_id(rows)[rid]
                self.assertEqual((r['category'], r['complete'], r['reason']),
                                 ('PARTIAL', False, 'page overlong'))

    def test_501_over_cap_partial(self):
        for rid, obj in OBJ.items():
            with self.subTest(rid=rid):
                rc, _, rows = run({rid: R(0, page(rid, objects(obj, 501)))})
                r = by_id(rows)[rid]
                self.assertEqual((r['category'], r['complete'], r['reason']),
                                 ('PARTIAL', False, 'over cap'))

    def test_wrong_list_kind_parse_error(self):
        for rid in OBJ:
            with self.subTest(rid=rid):
                body = {'apiVersion': 'v1', 'kind': 'SecretList',
                        'metadata': {'resourceVersion': 'r'}, 'items': []}
                rc, _, rows = run({rid: R(0, json.dumps(body))})
                self.assertEqual(by_id(rows)[rid]['category'], 'PARSE_ERROR')

    def test_rv_swap_partial(self):
        for rid, obj in OBJ.items():
            with self.subTest(rid=rid):
                rc, _, rows = run({rid: [R(0, page(rid, [obj], 't1', rv='rv1')),
                                         R(0, page(rid, [obj], None, rv='rv2'))]})
                self.assertEqual(by_id(rows)[rid]['category'], 'PARTIAL')

    def test_first_page_transport(self):
        for rid in OBJ:
            for stderr, cat in [('forbidden', 'FORBIDDEN'),
                                ("the server doesn't have a resource type", 'API_NOT_SERVED'),
                                ('connection refused', 'CONNECTION')]:
                with self.subTest(rid=rid, cat=cat):
                    rc, _, rows = run({rid: R(1, '', stderr)})
                    self.assertEqual(by_id(rows)[rid]['category'], cat)


class TestRemainingContract(unittest.TestCase):
    def test_projector_failure_stops_continuation(self):
        for rid, obj in OBJ.items():
            with self.subTest(rid=rid):
                bad = copy.deepcopy(obj)
                bad['spec'] = 'bad'
                rc, calls, rows = run({rid: [R(0, page(rid, [bad], 'next')), R(0, page(rid, [obj]))]})
                r = by_id(rows)[rid]
                self.assertEqual(sum(c[0] == rid for c in calls), 1)
                self.assertEqual((rc, r['category'], r['complete'], r['exit'], r['output']),
                                 (1, 'PARSE_ERROR', False, 0, ''))
                self.assertEqual(len(rows), 9)

    def test_projector_journal_is_not_success(self):
        for rid, obj in OBJ.items():
            with self.subTest(rid=rid):
                bad = copy.deepcopy(obj)
                bad['spec'] = 'bad'
                rc, _, rows = run({rid: R(0, page(rid, [bad]))})
                r = by_id(rows)[rid]
                self.assertTrue(r['journal'][0]['cause'])
                self.assertEqual(r['journal'][0]['validated'], 0)
                self.assertEqual(r['journal'][0]['returncode'], 0)

    def test_unsupported_stops_continuation(self):
        for rid, obj in OBJ.items():
            with self.subTest(rid=rid):
                bad = copy.deepcopy(obj)
                bad['spec']['UNKNOWN_SEMANTIC'] = 'SYNTHETIC_CANARY'
                rc, calls, rows = run({rid: [R(0, page(rid, [bad], 'next')), R(0, page(rid, [obj]))]})
                r = by_id(rows)[rid]
                self.assertEqual(sum(c[0] == rid for c in calls), 1)
                self.assertEqual((r['category'], r['complete'], r['output']), ('UNSUPPORTED', False, ''))
                self.assertNotIn('SYNTHETIC_CANARY', json.dumps(rows))

    def test_unknown_later_process_returncode_is_null(self):
        for rid, obj in OBJ.items():
            for exc in (subprocess.TimeoutExpired('kubectl', 20), OSError('SYNTHETIC_CANARY')):
                with self.subTest(rid=rid, error=type(exc).__name__):
                    rc, _, rows = run({rid: [R(0, page(rid, [obj], 'next')), exc]})
                    r = by_id(rows)[rid]
                    self.assertIsNone(r['exit'])
                    self.assertIsNone(r['journal'][-1]['returncode'])
                    self.assertEqual((rc, r['category'], r['complete']), (1, 'PARTIAL', False))
                    self.assertEqual(len(json.loads(r['output'])), 1)
                    self.assertNotIn('SYNTHETIC_CANARY', json.dumps(rows))

    def test_one_journal_record_per_repeated_token_attempt(self):
        for rid, obj in OBJ.items():
            with self.subTest(rid=rid):
                rc, calls, rows = run({rid: [R(0, page(rid, [obj], 'same')), R(0, page(rid, [obj], 'same'))]})
                r = by_id(rows)[rid]
                actual = sum(c[0] == rid for c in calls)
                self.assertEqual(len(r['journal']), actual)
                self.assertEqual(actual, 2)
                self.assertTrue(r['journal'][-1]['cause'])

    def test_duplicate_nonselected_versions_rejected(self):
        for entries in ([{'name': 'v2', 'served': False}, {'name': 'v2', 'served': False}],
                        [{'name': 'v2', 'served': False}, {'name': 'v2', 'served': True}]):
            with self.subTest(entries=entries):
                c = copy.deepcopy(CRD)
                c['spec']['versions'] += entries
                rc, calls, rows = run({'F-CS': R(0, json.dumps(c))})
                r = by_id(rows)['F-CS']
                self.assertEqual((rc, r['category'], r['output']), (1, 'PARSE_ERROR', ''))
                self.assertFalse(any(c[0] == 'F-CNP' for c in calls))

    def test_real_archived_identity_mapping(self):
        fixture = json.load(open(os.path.join(HERE, 'derived-i1-fixture.json')))
        rc, _, rows = run({'F-I1': R(0, json.dumps(fixture['podlist']))})
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(by_id(rows)['F-I1']['output']), fixture['expected_projection'])


KEY = {r['id']: r['proj'] for r in fw.READS if r['paginated']}


class TestBoundedProjection(unittest.TestCase):
    def execute(self, rid, pages):
        original = fw.PROJECTOR[KEY[rid]]
        with mock.patch.dict(fw.PROJECTOR, {KEY[rid]: mock.Mock(wraps=original)}):
            spy = fw.PROJECTOR[KEY[rid]]
            rc, calls, rows = run({rid: pages})
            return rc, calls, by_id(rows)[rid], spy.call_count

    def test_single_501_projects_only_500(self):
        for rid, obj in OBJ.items():
            with self.subTest(rid=rid):
                rc, calls, r, n = self.execute(rid, R(0, page(rid, objects(obj, 501))))
                self.assertEqual(n, 500)
                self.assertEqual((rc, r['category'], r['complete']), (1, 'PARTIAL', False))
                self.assertEqual(r['journal'][0]['received'], 501)
                self.assertEqual(r['journal'][0]['validated'], 500)
                self.assertEqual(len(json.loads(r['output'])), 500)

    def test_third_page_remaining_budget(self):
        for rid, obj in OBJ.items():
            with self.subTest(rid=rid):
                objs = objects(obj, 501)
                rc, calls, r, n = self.execute(rid, [R(0, page(rid, objs[:200], 'a')),
                                                      R(0, page(rid, objs[200:400], 'b')),
                                                      R(0, page(rid, objs[400:]))])
                self.assertEqual(n, 500)
                self.assertEqual([j['validated'] for j in r['journal']], [200, 200, 100])
                self.assertEqual([j['received'] for j in r['journal']], [200, 200, 101])
                self.assertEqual(sum(c[0] == rid for c in calls), 3)
                self.assertEqual((r['category'], r['complete']), ('PARTIAL', False))

    def test_invalid_discarded_suffix_not_projected(self):
        for rid, obj in OBJ.items():
            for malformed in (True, False):
                with self.subTest(rid=rid, malformed=malformed):
                    objs = objects(obj, 501)
                    if malformed:
                        objs[500]['spec'] = 'bad'
                    else:
                        objs[500]['spec']['UNKNOWN'] = 'SYNTHETIC_SUFFIX_CANARY'
                    rc, calls, r, n = self.execute(rid, R(0, page(rid, objs)))
                    self.assertEqual(n, 500)
                    self.assertEqual((r['category'], r['complete']), ('PARTIAL', False))
                    self.assertEqual(len(json.loads(r['output'])), 500)
                    self.assertNotIn('SYNTHETIC_SUFFIX_CANARY', json.dumps(r))

    def test_validated_count_on_midpage_error(self):
        for rid, obj in OBJ.items():
            with self.subTest(rid=rid):
                bad = copy.deepcopy(obj)
                bad['spec'] = 'bad'
                rc, calls, r, n = self.execute(rid, [R(0, page(rid, [obj, bad], 'next')),
                                                     R(0, page(rid, [obj]))])
                self.assertEqual((rc, r['category'], r['complete'], r['output']),
                                 (1, 'PARSE_ERROR', False, ''))
                self.assertEqual(sum(c[0] == rid for c in calls), 1)
                self.assertEqual(r['journal'][0]['received'], 2)
                self.assertEqual(r['journal'][0]['validated'], 1)


class TestI1Transport(unittest.TestCase):
    """F-I1 request-boundary correction (raw GET PodList) + finite diagnostic stages."""

    def _dependents(self, calls):
        return sum(rid in ('F-NP', 'F-GNP', 'F-FELIX', 'F-HEP', 'F-TIER') for rid, _ in calls)

    def test_literal_raw_argv(self):
        rc, calls, rows = run({'F-I1': R(0, podlist([POD]))})
        argv = [c[1] for c in calls if c[0] == 'F-I1'][0]
        # full argv tail must be the literal raw GET (labelSelector URL-encoded, limit=200)
        self.assertEqual(argv[4:], ['get', '--raw',
                                    '/api/v1/namespaces/kube-system/pods?labelSelector=k8s-app%3Dcalico-node&limit=200'])

    def test_valid_identity_permits_five(self):
        rc, calls, rows = run({'F-I1': R(0, podlist([POD]))})
        self.assertIsNone(by_id(rows)['F-I1']['category'])
        self.assertEqual(self._dependents(calls), 5)

    def test_overlong_partial_no_identity(self):
        rc, calls, rows = run({'F-I1': R(0, podlist([POD] * 201))})
        r = by_id(rows)['F-I1']
        self.assertEqual((r['category'], r['complete'], r['diag'], r['output']),
                         ('PARTIAL', False, 'OVERLONG', ''))
        self.assertEqual(self._dependents(calls), 0)

    def test_nonempty_continue_incomplete(self):
        rc, calls, rows = run({'F-I1': R(0, podlist([POD], continue_token='abc'))})
        r = by_id(rows)['F-I1']
        self.assertEqual((r['category'], r['diag']), ('PARSE_ERROR', 'COMPLETENESS'))
        self.assertEqual(self._dependents(calls), 0)

    def test_empty_continue_is_complete(self):
        rc, calls, rows = run({'F-I1': R(0, podlist([POD], continue_token=''))})
        self.assertIsNone(by_id(rows)['F-I1']['category'])

    def test_old_kubectl_list_regression(self):
        # The OLD transport `kubectl get pods -o json` returns a generic List, not PodList.
        # This is a regression documenting why that transport was invalid (must never pass).
        raw = json.loads(podlist([POD]))
        raw['kind'] = 'List'
        rc, calls, rows = run({'F-I1': R(0, json.dumps(raw))})
        r = by_id(rows)['F-I1']
        self.assertEqual((r['category'], r['diag']), ('PARSE_ERROR', 'ENVELOPE'))
        self.assertEqual(self._dependents(calls), 0)

    def test_missing_rv_metadata_diag(self):
        raw = json.loads(podlist([POD]))
        raw['metadata']['resourceVersion'] = ''
        rc, calls, rows = run({'F-I1': R(0, json.dumps(raw))})
        r = by_id(rows)['F-I1']
        self.assertEqual((r['category'], r['diag']), ('PARSE_ERROR', 'METADATA'))
        self.assertEqual(self._dependents(calls), 0)

    def test_item_not_object_diag(self):
        raw = json.loads(podlist([POD]))
        raw['items'] = [None]
        rc, _, rows = run({'F-I1': R(0, json.dumps(raw))})
        r = by_id(rows)['F-I1']
        self.assertEqual((r['category'], r['diag']), ('PARSE_ERROR', 'ITEM'))

    def test_unbound_identity_diag(self):
        p = copy.deepcopy(POD)
        p['spec']['containers'][0]['image'] = 'quay.io/calico/node:v3.31.0'
        rc, _, rows = run({'F-I1': R(0, podlist([p]))})
        r = by_id(rows)['F-I1']
        self.assertEqual((r['category'], r['diag']), ('UNSUPPORTED', 'IDENTITY'))
        self.assertNotEqual(r['output'], '')  # safe projected identity retained


DEPS5 = ('F-NP', 'F-GNP', 'F-FELIX', 'F-HEP', 'F-TIER')


class TestCompatibilityRemaining(unittest.TestCase):
    """LC-01/LC-02 residual cases (explicit null continue + Kubernetes isCIDR semantics)."""

    def _deps(self, calls):
        return sum(rid in DEPS5 for rid, _ in calls)

    def test_explicit_null_continue_blocks_all_consumers(self):
        raw = json.loads(podlist([POD]))
        raw['metadata']['continue'] = None
        rc, calls, rows = run({'F-I1': R(0, json.dumps(raw))})
        r = by_id(rows)['F-I1']
        self.assertEqual((rc, r['category'], r['complete'], r['output'], r['diag']),
                         (1, 'PARSE_ERROR', False, '', 'COMPLETENESS'))
        self.assertEqual(self._deps(calls), 0)

    def test_continue_present_nonstring(self):
        for bad in (True, 5, ['x'], {'k': 'v'}):
            with self.subTest(bad=bad):
                raw = json.loads(podlist([POD]))
                raw['metadata']['continue'] = bad
                rc, calls, rows = run({'F-I1': R(0, json.dumps(raw))})
                r = by_id(rows)['F-I1']
                self.assertEqual((r['category'], r['diag']), ('PARSE_ERROR', 'COMPLETENESS'))
                self.assertEqual(self._deps(calls), 0)

    def test_cidr_cel_and_schema_negatives(self):
        cases = {
            'dotted_netmask': '10.0.0.5/255.255.255.0',
            'dotted_hostmask': '10.0.0.5/0.0.0.255',
            'zone': 'fe80::1%eth0/64',
            'mapped_v6': '::ffff:192.0.2.1/128',
            'leading_zero_prefix': '10.0.0.5/024',
            'schema_length_49': '2001:0db8:0000:0000:0000:0000:192.168.100.100/128',
        }
        for name, value in cases.items():
            with self.subTest(name=name):
                obj = copy.deepcopy(CNP)
                obj['spec']['egress'][0]['to'] = [{'networks': [value]}]
                rc, _, rows = run({'F-CNP': R(0, page('F-CNP', [obj]))})
                r = by_id(rows)['F-CNP']
                self.assertEqual((rc, r['category'], r['complete'], r['output']),
                                 (1, 'PARSE_ERROR', False, ''))

    def test_host_bits_and_named_ports_preserved(self):
        for cidr in ('10.0.0.5/24', '2001:db8::5/64', '0.0.0.0/0', '::/0'):
            obj = copy.deepcopy(CNP)
            obj['spec']['egress'][0]['to'] = [{'networks': [cidr]}]
            out = fw.project_cnp(obj)
            self.assertEqual(out['spec']['egress'][0]['to'][0]['networks'], [cidr])
        for direction in ('ingress', 'egress'):
            for name in ('http', '', 'Mixed.Case'):
                obj = copy.deepcopy(CNP)
                obj['spec'][direction][0]['protocols'] = [{'destinationNamedPort': name}]
                out = fw.project_cnp(obj)
                self.assertEqual(out['spec'][direction][0]['protocols'], [{'destinationNamedPort': name}])


class TestManifestProvenance(unittest.TestCase):
    """CNP pin provenance: the manifest-derived hash, not the old upstream candidate."""

    def test_manifest_schema_matches_pin(self):
        yaml_path = os.path.join(REPO_ROOT, 'ansible/playbooks/files/calico-v3.32.0.yaml')
        docs = list(yaml.safe_load_all(open(yaml_path)))
        crd = next(d for d in docs if d and d.get('metadata', {}).get('name') == 'clusternetworkpolicies.policy.networking.k8s.io')
        v = next(x for x in crd['spec']['versions'] if x['name'] == 'v1alpha2')
        subtree = v['schema']['openAPIV3Schema']['properties']['spec']
        canon = json.dumps(fw.normalize_schema(subtree), sort_keys=True, ensure_ascii=False, separators=(',', ':'))
        self.assertEqual(hashlib.sha256(canon.encode()).hexdigest(), fw.CNP_SPEC_SHA256)

    def test_old_candidate_mismatch(self):
        # The prior network-policy-api candidate hash differs from the current Calico manifest pin.
        old = '770130a412fd6fab2f02d953edf35f8cc68bf4379db8307e2185937c1e699568'
        self.assertNotEqual(old, fw.CNP_SPEC_SHA256)
        self.assertEqual(fw.CNP_SPEC_SHA256, 'ff433d3463dfa2264a7a3ff6201baabf1ec789e98664aff3401a7ef79ae7ce5e')


class TestTypedPodListBoundary(unittest.TestCase):
    """Integrated supplied regression: typed core/v1 PodList items may omit TypeMeta."""

    def _fixture(self):
        with open(os.path.join(HERE, 'derived-i1-fixture.json')) as f:
            return json.load(f)

    def _payload(self, omit=()):
        data = copy.deepcopy(self._fixture()['podlist'])
        for pod in data['items']:
            for key in omit:
                pod.pop(key, None)
        return data

    def _execute(self, data):
        rc, calls, rows = run({'F-I1': R(0, json.dumps(data))})
        return rc, calls, by_id(rows)

    def _accepted(self, omit):
        rc, calls, rows = self._execute(self._payload(omit))
        r = rows['F-I1']
        self.assertEqual((rc, r['category'], r['complete']), (0, None, True))
        self.assertEqual(json.loads(r['output']), self._fixture()['expected_projection'])
        self.assertEqual({x[0] for x in calls} & set(DEPS5), set(DEPS5))

    def test_explicit_typemeta_control(self):
        self._accepted(())

    def test_both_typemeta_absent(self):
        self._accepted(('kind', 'apiVersion'))

    def test_kind_absent(self):
        self._accepted(('kind',))

    def test_version_absent(self):
        self._accepted(('apiVersion',))

    def test_present_invalid_typemeta_stays_rejected(self):
        for key, value in [('kind', None), ('kind', ''), ('kind', 'Service'),
                           ('kind', False), ('kind', {}), ('apiVersion', None),
                           ('apiVersion', ''), ('apiVersion', 'v2'),
                           ('apiVersion', 1), ('apiVersion', [])]:
            with self.subTest(key=key, value=value):
                d = self._payload()
                d['items'][0][key] = value
                rc, calls, rows = self._execute(d)
                r = rows['F-I1']
                self.assertEqual((rc, r['category'], r['complete'], r['output']),
                                 (1, 'PARSE_ERROR', False, ''))
                self.assertFalse({x[0] for x in calls} & set(DEPS5))
                self.assertIsNone(rows['F-CS']['category'])
                self.assertIsNone(rows['F-CNP']['category'])

    def test_omission_does_not_bypass_identity_gate(self):
        d = self._payload(('kind', 'apiVersion'))
        for p in d['items']:
            for s in p['status'].get('containerStatuses', []):
                if s['name'] == 'calico-node':
                    s['imageID'] = 'sha256:' + '0' * 64
        rc, calls, rows = self._execute(d)
        r = rows['F-I1']
        self.assertEqual((rc, r['category'], r['complete']), (1, 'UNSUPPORTED', False))
        self.assertTrue(r['output'])
        self.assertFalse({x[0] for x in calls} & set(DEPS5))


class TestI1ItemDiag(unittest.TestCase):
    """MI-02: itemDiag finite codes for each projection failure class."""

    def _case(self, mutate, code):
        p = copy.deepcopy(POD)
        mutate(p)
        rc, calls, rows = run({'F-I1': R(0, podlist([p]))})
        rid = by_id(rows)
        r = rid['F-I1']
        self.assertEqual((r['category'], r['complete'], r['output'], r['itemDiag']),
                         ('PARSE_ERROR', False, '', code))
        self.assertFalse({x[0] for x in calls} & set(DEPS5))
        self.assertIsNone(rid['F-CS']['category'])
        self.assertIsNone(rid['F-CNP']['category'])

    def test_typemeta_kind(self):
        self._case(lambda p: p.update(kind='Service'), 'TYPEMETA_KIND')

    def test_typemeta_api_version(self):
        self._case(lambda p: p.update(apiVersion='v2'), 'TYPEMETA_API_VERSION')

    def test_metadata_namespace(self):
        self._case(lambda p: p['metadata'].update(namespace='default'), 'METADATA')

    def test_metadata_missing(self):
        self._case(lambda p: p.pop('metadata'), 'METADATA')

    def test_spec_not_object(self):
        self._case(lambda p: p.update(spec='x'), 'SPEC')

    def test_status_not_object(self):
        self._case(lambda p: p.update(status='x'), 'STATUS')

    def test_containers_not_list(self):
        self._case(lambda p: p['spec'].update(containers='x'), 'CONTAINERS')

    def test_container_name_empty(self):
        self._case(lambda p: p['spec']['containers'][0].update(name=''), 'CONTAINER_NAME')

    def test_image_wrong_type(self):
        self._case(lambda p: p['spec']['containers'][0].update(image=123), 'IMAGE')

    def test_image_id_wrong_type(self):
        self._case(lambda p: p['status']['containerStatuses'][0].update(imageID=123), 'IMAGE_ID')

    def test_ports_invalid(self):
        self._case(lambda p: p['spec']['containers'][0].update(ports=[{'containerPort': 0}]), 'PORTS')

    def test_restart_policy_wrong_type(self):
        self._case(lambda p: p['spec']['containers'][0].update(restartPolicy=123), 'RESTART_POLICY')

    def test_non_dict_item(self):
        rc, calls, rows = run({'F-I1': R(0, podlist([None]))})
        r = by_id(rows)['F-I1']
        self.assertEqual((r['category'], r['itemDiag']), ('PARSE_ERROR', 'OTHER'))

    def test_canary_not_leaked_in_item_diag(self):
        p = copy.deepcopy(POD)
        p['metadata']['name'] = CANARY  # would be projected if the item were valid
        p['spec']['containers'][0]['image'] = 123  # triggers PARSE_ERROR (IMAGE)
        rc, calls, rows = run({'F-I1': R(0, podlist([p]))})
        r = by_id(rows)['F-I1']
        self.assertEqual((r['category'], r['itemDiag'], r['output']),
                         ('PARSE_ERROR', 'IMAGE', ''))
        self.assertNotIn(CANARY, json.dumps(rows))

    def test_adapter_contract(self):
        # MI-01: absent keys are filled on the copy; present-invalid keys are rejected, never overwritten.
        item = {'metadata': {}, 'spec': {}, 'status': {}}
        self.assertIsNone(fw._i1_adapt_type_meta(item))
        self.assertEqual((item.get('kind'), item.get('apiVersion')), ('Pod', 'v1'))
        bad = {'kind': 'Service', 'apiVersion': 'v1'}
        self.assertEqual(fw._i1_adapt_type_meta(bad), 'TYPEMETA_KIND')
        self.assertEqual(bad['kind'], 'Service')  # not overwritten


if __name__ == '__main__':
    unittest.main(verbosity=2)
