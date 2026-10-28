#!/usr/bin/env python3
"""Offline tests for followup.py (F-D1..F-TIER). Mocked kubectl, argv-routed."""
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


def podlist(pods, continue_token=None):
    meta = {'resourceVersion': 'rv1'}
    if continue_token is not None:
        meta['continue'] = continue_token
    return json.dumps({'kind': 'PodList', 'apiVersion': 'v1', 'metadata': meta, 'items': pods})


def listpage(items, continue_token=None, rv='rv1'):
    meta = {'resourceVersion': rv}
    if continue_token is not None:
        meta['continue'] = continue_token
    return json.dumps({'kind': 'List', 'metadata': meta, 'items': items})


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
            return ans[idx]
        self.pages[rid] += 1
        if isinstance(ans, BaseException):
            raise ans
        return ans


def run(overrides=None):
    overrides = overrides or {}
    defaults = {
        'F-D1': R(0, json.dumps(CALICO_DISC)),
        'F-I1': R(0, podlist([POD])),
        'F-CS': R(0, json.dumps(CRD)),
        'F-CNP': [R(0, listpage([CNP]))],
        'F-NP': [R(0, listpage([NP]))],
        'F-GNP': [R(0, listpage([GNP]))],
        'F-FELIX': R(0, json.dumps(FELIX)),
        'F-HEP': [R(0, listpage([HEP]))],
        'F-TIER': [R(0, listpage([TIER]))],
    }
    responses = dict(defaults)
    responses.update(overrides)
    mrun = RunMock(responses)
    tmp = tempfile.mkdtemp()
    outdir = os.path.join(tmp, 'out')
    with mock.patch.object(shutil, 'which', return_value='/mock/kubectl'), \
         mock.patch.object(subprocess, 'run', side_effect=mrun), \
         mock.patch.object(fw.sys, 'argv', ['followup.py', '--context', 'c', '--output', outdir]):
        rc = fw.main()
    rows = [json.loads(l) for l in open(os.path.join(outdir, 'followup.jsonl'))]
    return rc, mrun.calls, rows


def by_id(rows):
    return {r['id']: r for r in rows}


class TestHappyPath(unittest.TestCase):
    def test_all_ok(self):
        rc, calls, rows = run()
        self.assertEqual(rc, 0)
        self.assertEqual(len(rows), 9)
        for r in rows:
            self.assertIsNone(r['category'], r['id'])
        # literal argv assertions
        self.assertEqual(by_id(rows)['F-D1']['argv'][4:], ['get', '--raw', '/apis/crd.projectcalico.org/v1'])
        self.assertEqual(by_id(rows)['F-FELIX']['argv'][4:],
                         ['get', '--raw', '/apis/crd.projectcalico.org/v1/felixconfigurations/default'])
        # paginated reads use limit=200 on first page
        np_argv = [c[1] for c in calls if c[0] == 'F-NP'][0]
        self.assertIn('?limit=200', np_argv[6])

    def test_cnp_projection(self):
        _, _, rows = run()
        cnp = json.loads(by_id(rows)['F-CNP']['output'])[0]
        self.assertEqual(cnp['spec']['tier'], 'Admin')
        self.assertEqual(cnp['spec']['subject']['namespaces']['matchLabels'], {'name': 'portal'})
        self.assertEqual(cnp['spec']['ingress'][0]['protocols'][0]['tcp']['destinationPort'], {'number': 5432})
        self.assertEqual(cnp['spec']['egress'][0]['to'][0]['networks'], ['10.244.0.0/24'])
        self.assertEqual(cnp['spec']['egress'][0]['protocols'][0]['udp']['destinationPort'],
                         {'range': {'start': 53, 'end': 54}})

    def test_cs_output(self):
        _, _, rows = run()
        cs = json.loads(by_id(rows)['F-CS']['output'])
        self.assertTrue(cs['compatible'])
        self.assertEqual(cs['spec_schema_sha256'], fw.CNP_SPEC_SHA256)
        self.assertEqual(cs['scope'], 'Cluster')
        self.assertEqual(cs['names_kind'], 'ClusterNetworkPolicy')


class TestIdentity(unittest.TestCase):
    def test_new_config_digest_positive(self):
        p = copy.deepcopy(POD)
        p['status']['containerStatuses'][0]['imageID'] = 'sha256:' + AMD64_CONFIG_HEX
        rc, calls, rows = run({'F-I1': R(0, podlist([p]))})
        self.assertEqual(rc, 0)
        self.assertIn('F-NP', [c[0] for c in calls])

    def test_config_digest_prefix_rejected(self):
        p = copy.deepcopy(POD)
        p['status']['containerStatuses'][0]['imageID'] = 'containerd://sha256:' + AMD64_CONFIG_HEX
        rc, calls, rows = run({'F-I1': R(0, podlist([p]))})
        self.assertNotEqual(rc, 0)
        i1 = by_id(rows)['F-I1']
        self.assertEqual(i1['category'], 'UNSUPPORTED')
        for dep in ('F-NP', 'F-GNP', 'F-FELIX', 'F-HEP', 'F-TIER'):
            self.assertEqual(by_id(rows)[dep]['category'], 'BLOCKED_NOT_EXECUTED')
        self.assertNotIn('F-NP', [c[0] for c in calls])

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
    def _bad_disc(self, mutate):
        d = copy.deepcopy(CALICO_DISC)
        mutate(d)
        return R(0, json.dumps(d))

    def test_wrong_scope_kind_verb(self):
        for mutate in [
            lambda d: d['resources'][4].update(namespaced=True),   # tiers -> namespaced
            lambda d: d['resources'][3].update(kind='Wrong'),      # hostendpoints wrong kind
            lambda d: d['resources'][0].update(verbs=['get']),     # np missing list verb
            lambda d: d.update(resources=d['resources'][:4]),      # missing tiers
        ]:
            rc, calls, rows = run({'F-D1': self._bad_disc(mutate)})
            self.assertNotEqual(rc, 0)
            self.assertNotIn('F-NP', [c[0] for c in calls])
            for dep in ('F-NP', 'F-GNP', 'F-FELIX', 'F-HEP', 'F-TIER'):
                self.assertEqual(by_id(rows)[dep]['category'], 'BLOCKED_NOT_EXECUTED')


class TestCRDSchema(unittest.TestCase):
    def test_mismatch_unsupported(self):
        bad_spec = copy.deepcopy(CNP_SPEC)
        bad_spec['properties']['priority']['maximum'] = 9999
        bad_crd = copy.deepcopy(CRD)
        bad_crd['spec']['versions'][0]['schema']['openAPIV3Schema']['properties']['spec'] = bad_spec
        rc, calls, rows = run({'F-CS': R(0, json.dumps(bad_crd))})
        self.assertNotEqual(rc, 0)
        cs = by_id(rows)['F-CS']
        self.assertEqual(cs['category'], 'UNSUPPORTED')
        self.assertFalse(json.loads(cs['output'])['compatible'])
        self.assertEqual(by_id(rows)['F-CNP']['category'], 'BLOCKED_NOT_EXECUTED')
        self.assertNotIn('F-CNP', [c[0] for c in calls])

    def test_malformed_parse_error_no_raw(self):
        bad = {'apiVersion': 'apiextensions.k8s.io/v1', 'kind': 'CustomResourceDefinition',
               'metadata': {'name': 'clusternetworkpolicies.policy.networking.k8s.io',
                            'annotations': {'leak': CANARY}},
               'spec': {'group': 'policy.networking.k8s.io', 'names': {'kind': 'ClusterNetworkPolicy',
                                                                        'plural': 'clusternetworkpolicies'},
                        'scope': 'Namespaced',  # wrong scope
                        'versions': [{'name': 'v1alpha2', 'served': True}]}}
        rc, _, rows = run({'F-CS': R(0, json.dumps(bad))})
        self.assertNotEqual(rc, 0)
        self.assertEqual(by_id(rows)['F-CS']['category'], 'PARSE_ERROR')
        self.assertEqual(by_id(rows)['F-CS']['output'], '')
        # no raw leak
        allout = json.dumps([r for r in rows])
        self.assertNotIn(CANARY, allout)


class TestCNP(unittest.TestCase):
    def _cnp(self, mutate):
        c = copy.deepcopy(CNP)
        mutate(c)
        return R(0, listpage([c]))

    def test_unknown_semantic_field_unsupported(self):
        c = copy.deepcopy(CNP)
        c['spec']['ingress'][0]['bogusField'] = 'x'
        rc, _, rows = run({'F-CNP': self._cnp(lambda _: None) if False else [R(0, listpage([c]))]})
        self.assertNotEqual(rc, 0)
        self.assertEqual(by_id(rows)['F-CNP']['category'], 'UNSUPPORTED')

    def test_priority_bounds(self):
        rc, _, rows = run({'F-CNP': self._cnp(lambda c: c['spec'].update(priority=1001))})
        self.assertNotEqual(rc, 0)
        self.assertEqual(by_id(rows)['F-CNP']['category'], 'PARSE_ERROR')

    def test_port_range_start_ge_end(self):
        rc, _, rows = run({'F-CNP': self._cnp(
            lambda c: c['spec']['egress'][0]['protocols'][0]['udp']['destinationPort'].update(
                range={'start': 60, 'end': 60}))})
        self.assertNotEqual(rc, 0)
        self.assertEqual(by_id(rows)['F-CNP']['category'], 'PARSE_ERROR')

    def test_bad_action_enum(self):
        rc, _, rows = run({'F-CNP': self._cnp(lambda c: c['spec']['ingress'][0].update(action='Allow'))})
        self.assertNotEqual(rc, 0)
        self.assertEqual(by_id(rows)['F-CNP']['category'], 'PARSE_ERROR')

    def test_noncanonical_cidr(self):
        rc, _, rows = run({'F-CNP': self._cnp(
            lambda c: c['spec']['egress'][0].update(to=[{'networks': ['10.244.0.5/24']}]))})
        self.assertNotEqual(rc, 0)
        self.assertEqual(by_id(rows)['F-CNP']['category'], 'PARSE_ERROR')

    def test_subject_two_fields(self):
        c = copy.deepcopy(CNP)
        c['spec']['subject'] = {'namespaces': {'matchLabels': {}}, 'pods': {'podSelector': {}}}
        rc, _, rows = run({'F-CNP': [R(0, listpage([c]))]})
        self.assertNotEqual(rc, 0)
        self.assertEqual(by_id(rows)['F-CNP']['category'], 'PARSE_ERROR')


class TestHEP(unittest.TestCase):
    def test_valid_preserved(self):
        _, _, rows = run()
        hep = json.loads(by_id(rows)['F-HEP']['output'])[0]
        self.assertEqual(hep['metadata']['name'], 'node01-eth0')
        self.assertEqual(hep['metadata']['labels'], {'kubernetes.io/hostname': 'node-01'})
        self.assertEqual(hep['spec']['node'], 'node-01')
        self.assertEqual(hep['spec']['ports'], [{'name': 'k8s', 'port': 6443, 'protocol': 'TCP'}])
        self.assertEqual(hep['spec']['profiles'], ['default'])

    def test_missing_node(self):
        h = copy.deepcopy(HEP)
        h['spec'].pop('node')
        rc, _, rows = run({'F-HEP': [R(0, listpage([h]))]})
        self.assertNotEqual(rc, 0)
        self.assertEqual(by_id(rows)['F-HEP']['category'], 'PARSE_ERROR')

    def test_empty_interface_and_ips(self):
        h = copy.deepcopy(HEP)
        h['spec']['interfaceName'] = ''
        h['spec']['expectedIPs'] = []
        rc, _, rows = run({'F-HEP': [R(0, listpage([h]))]})
        self.assertNotEqual(rc, 0)
        self.assertEqual(by_id(rows)['F-HEP']['category'], 'PARSE_ERROR')

    def test_unknown_spec_key(self):
        h = copy.deepcopy(HEP)
        h['spec']['bogus'] = 1
        rc, _, rows = run({'F-HEP': [R(0, listpage([h]))]})
        self.assertNotEqual(rc, 0)
        self.assertEqual(by_id(rows)['F-HEP']['category'], 'UNSUPPORTED')


class TestTier(unittest.TestCase):
    def test_default_action_preserved(self):
        _, _, rows = run()
        tier = json.loads(by_id(rows)['F-TIER']['output'])[0]
        self.assertEqual(tier['spec']['defaultAction'], 'Pass')
        self.assertEqual(tier['spec']['order'], 100)

    def test_absent_vs_observed(self):
        t = copy.deepcopy(TIER)
        t['spec'].pop('defaultAction')
        rc, _, rows = run({'F-TIER': [R(0, listpage([t]))]})
        self.assertEqual(rc, 0)
        tier = json.loads(by_id(rows)['F-TIER']['output'])[0]
        self.assertNotIn('defaultAction', tier['spec'])

    def test_invalid_enum(self):
        t = copy.deepcopy(TIER)
        t['spec']['defaultAction'] = 'Allow'
        rc, _, rows = run({'F-TIER': [R(0, listpage([t]))]})
        self.assertNotEqual(rc, 0)
        self.assertEqual(by_id(rows)['F-TIER']['category'], 'PARSE_ERROR')


class TestPagination(unittest.TestCase):
    def test_empty(self):
        rc, _, rows = run({'F-NP': [R(0, listpage([]))]})
        self.assertEqual(rc, 0)
        self.assertTrue(by_id(rows)['F-NP']['complete'])

    def test_two_pages_complete(self):
        rc, calls, rows = run({'F-NP': [R(0, listpage([NP], continue_token='tok1')),
                                         R(0, listpage([NP], continue_token=None))]})
        self.assertEqual(rc, 0)
        self.assertTrue(by_id(rows)['F-NP']['complete'])
        self.assertEqual(len([c for c in calls if c[0] == 'F-NP']), 2)

    def test_cap_reached_partial(self):
        rc, calls, rows = run({'F-NP': [R(0, listpage([NP], continue_token='t1')),
                                         R(0, listpage([NP], continue_token='t2')),
                                         R(0, listpage([NP], continue_token='t3'))]})
        self.assertNotEqual(rc, 0)
        self.assertEqual(by_id(rows)['F-NP']['category'], 'PARTIAL')
        self.assertFalse(by_id(rows)['F-NP']['complete'])
        self.assertEqual(len([c for c in calls if c[0] == 'F-NP']), 3)

    def test_rv_swap_partial(self):
        rc, _, rows = run({'F-NP': [R(0, listpage([NP], continue_token='t1', rv='rv1')),
                                     R(0, listpage([NP], continue_token=None, rv='rv2'))]})
        self.assertNotEqual(rc, 0)
        self.assertEqual(by_id(rows)['F-NP']['category'], 'PARTIAL')

    def test_repeated_token_partial(self):
        rc, _, rows = run({'F-NP': [R(0, listpage([NP], continue_token='t1')),
                                     R(0, listpage([NP], continue_token='t1')),
                                     R(0, listpage([NP], continue_token='t1'))]})
        self.assertNotEqual(rc, 0)
        self.assertEqual(by_id(rows)['F-NP']['category'], 'PARTIAL')

    def test_next_page_error_partial(self):
        rc, _, rows = run({'F-NP': [R(0, listpage([NP], continue_token='t1')),
                                     R(501, '', 'server error')]})
        self.assertNotEqual(rc, 0)
        self.assertEqual(by_id(rows)['F-NP']['category'], 'PARTIAL')

    def test_malformed_list_parse_error(self):
        rc, _, rows = run({'F-NP': [R(0, json.dumps({'kind': 'List', 'metadata': {}, 'items': 'notalist'}))]})
        self.assertNotEqual(rc, 0)
        self.assertEqual(by_id(rows)['F-NP']['category'], 'PARSE_ERROR')


class TestSubprocessErrors(unittest.TestCase):
    def test_timeout(self):
        rc, _, rows = run({'F-D1': subprocess.TimeoutExpired('kubectl', 20)})
        self.assertNotEqual(rc, 0)
        self.assertEqual(by_id(rows)['F-D1']['category'], 'TIMEOUT')

    def test_forbidden(self):
        rc, _, rows = run({'F-D1': R(1, '', 'Error: forbidden')})
        self.assertNotEqual(rc, 0)
        self.assertEqual(by_id(rows)['F-D1']['category'], 'FORBIDDEN')

    def test_not_served(self):
        rc, _, rows = run({'F-D1': R(1, '', "error: the server doesn't have a resource type")})
        self.assertNotEqual(rc, 0)
        self.assertEqual(by_id(rows)['F-D1']['category'], 'API_NOT_SERVED')

    def test_connection(self):
        rc, _, rows = run({'F-D1': R(1, '', 'Error: connection refused')})
        self.assertNotEqual(rc, 0)
        self.assertEqual(by_id(rows)['F-D1']['category'], 'CONNECTION')


class TestEnv(unittest.TestCase):
    def test_no_kubectl(self):
        tmp = tempfile.mkdtemp()
        outdir = os.path.join(tmp, 'out')
        with mock.patch.object(shutil, 'which', return_value=None), \
             mock.patch.object(fw.sys, 'argv', ['followup.py', '--context', 'c', '--output', outdir]):
            with self.assertRaises(SystemExit):
                fw.main()

    def test_no_overwrite(self):
        tmp = tempfile.mkdtemp()
        outdir = os.path.join(tmp, 'out')
        os.mkdir(outdir)
        with mock.patch.object(shutil, 'which', return_value='/mock/kubectl'), \
             mock.patch.object(subprocess, 'run', side_effect=RunMock({})), \
             mock.patch.object(fw.sys, 'argv', ['followup.py', '--context', 'c', '--output', outdir]):
            with self.assertRaises(FileExistsError):
                fw.main()

    def test_no_raw_annotation_env_credential_leak(self):
        p = copy.deepcopy(POD)
        p['metadata']['annotations'] = {'leak': CANARY}
        p['spec']['containers'][0]['env'] = [{'name': 'SECRET', 'value': CANARY}]
        rc, _, rows = run({'F-I1': R(0, podlist([p]))})
        allout = json.dumps(rows)
        self.assertNotIn(CANARY, allout)


if __name__ == '__main__':
    unittest.main(verbosity=2)
