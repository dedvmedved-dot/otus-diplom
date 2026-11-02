"""Independent offline boundary tests; subprocesses are mocked by author harness."""
import copy
import json
import unittest
from unittest import mock
import followup as f
import followup_test as t

DEPS = {'F-NP', 'F-GNP', 'F-FELIX', 'F-HEP', 'F-TIER'}

class TestCompatibilityRemaining(unittest.TestCase):
    def test_explicit_null_continue_blocks_all_consumers(self):
        raw = json.loads(t.podlist([t.POD_CFG]))
        raw['metadata']['continue'] = None
        rc, calls, rows = t.run({'F-I1': t.R(0, json.dumps(raw))})
        r = t.by_id(rows)['F-I1']
        actual = (rc, r['category'], r['complete'], r['output'], sum(i in DEPS for i,_ in calls))
        self.assertEqual(actual, (1, 'PARSE_ERROR', False, '', 0))

    def test_cidr_cel_and_schema_negatives(self):
        # Expected rejection is independently grounded in Kubernetes CEL parseCIDR,
        # Go netip.ParsePrefix and manifest maxLength=43, not Python ip_network.
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
                obj = copy.deepcopy(t.CNP)
                obj['spec']['egress'][0]['to'] = [{'networks': [value]}]
                rc, calls, rows = t.run({'F-CNP': t.R(0, t.page('F-CNP', [obj]))})
                r = t.by_id(rows)['F-CNP']
                self.assertEqual((rc,r['category'],r['complete'],r['output']), (1,'PARSE_ERROR',False,''))

    def test_identity_valid_and_overlong_controls(self):
        for pod in (t.POD, t.POD_CFG, t.POD_DIGEST):
            with self.subTest(image=pod['status']['containerStatuses'][0]['imageID']):
                rc,calls,rows=t.run({'F-I1':t.R(0,t.podlist([pod]))})
                self.assertEqual((rc,t.by_id(rows)['F-I1']['complete'],sum(i in DEPS for i,_ in calls)),(0,True,5))
        with mock.patch.object(f, 'project_pod_identity', wraps=f.project_pod_identity) as spy:
            rc,calls,rows=t.run({'F-I1':t.R(0,t.podlist(t.objects(t.POD_CFG,201)))})
            r=t.by_id(rows)['F-I1']
            self.assertEqual((r['category'],r['complete'],spy.call_count,sum(i in DEPS for i,_ in calls)),('PARTIAL',False,0,0))

    def test_host_bits_and_named_ports_preserved(self):
        for cidr in ('10.0.0.5/24','2001:db8::5/64','0.0.0.0/0','::/0'):
            obj=copy.deepcopy(t.CNP)
            obj['spec']['egress'][0]['to']=[{'networks':[cidr]}]
            out=f.project_cnp(obj)
            self.assertEqual(out['spec']['egress'][0]['to'][0]['networks'],[cidr])
        for direction in ('ingress','egress'):
            for name in ('http','', 'Mixed.Case'):
                obj=copy.deepcopy(t.CNP)
                obj['spec'][direction][0]['protocols']=[{'destinationNamedPort':name}]
                out=f.project_cnp(obj)
                self.assertEqual(out['spec'][direction][0]['protocols'],[{'destinationNamedPort':name}])

if __name__ == '__main__':
    unittest.main(verbosity=2)
