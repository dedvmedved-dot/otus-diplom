#!/usr/bin/env python3
"""Offline tests for followup.py (F-D1..F-TIER), FU-01..08 corrective suite."""
import copy
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


def objects(obj, n):
    out = []
    for i in range(n):
        x = copy.deepcopy(obj)
        x['metadata']['name'] = x['metadata']['name'] + '-%d' % i
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
    rows = [json.loads(l) for l in open(os.path.join(outdir, 'followup.jsonl'))]
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

    def test_three_saved_pod_identities(self):
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

    def test_noncanonical_cidr(self):
        rc, _, rows = run({'F-CNP': self._cnp(
            lambda c: c['spec']['egress'][0].update(to=[{'networks': ['10.244.0.5/24']}]))})
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


if __name__ == '__main__':
    unittest.main(verbosity=2)
