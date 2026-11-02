"""Offline PodList wire-boundary regression; fixtures are DERIVED, not raw live Pods.
Run beside followup.py, supplemental.py, followup_test.py and its fixture/contract.
Expected on reviewed fdfc776: 4 methods fail (3 positive omission variants + unbound).
No network or kubectl subprocess: followup_test.run mocks subprocess.run.
"""
import copy
import json
import unittest
from pathlib import Path
import followup_test as t

DEPS = {'F-NP', 'F-GNP', 'F-FELIX', 'F-HEP', 'F-TIER'}

def fixture():
    with (Path(__file__).parent / 'derived-i1-fixture.json').open() as f:
        return json.load(f)

def payload(omit=()):
    data = copy.deepcopy(fixture()['podlist'])
    for pod in data['items']:
        for key in omit:
            pod.pop(key, None)
    return data

def execute(data):
    rc, calls, rows = t.run({'F-I1': t.R(0, json.dumps(data))})
    return rc, calls, t.by_id(rows)

class TestTypedPodListBoundary(unittest.TestCase):
    def accepted(self, omit):
        rc, calls, rows = execute(payload(omit))
        r = rows['F-I1']
        self.assertEqual((rc, r['category'], r['complete']), (0, None, True))
        self.assertEqual(json.loads(r['output']), fixture()['expected_projection'])
        self.assertEqual({x[0] for x in calls} & DEPS, DEPS)

    def test_explicit_typemeta_control(self): self.accepted(())
    def test_both_typemeta_absent(self): self.accepted(('kind', 'apiVersion'))
    def test_kind_absent(self): self.accepted(('kind',))
    def test_version_absent(self): self.accepted(('apiVersion',))

    def test_present_invalid_typemeta_stays_rejected(self):
        for key, value in [('kind', None), ('kind', ''), ('kind', 'Service'),
                           ('kind', False), ('kind', {}), ('apiVersion', None),
                           ('apiVersion', ''), ('apiVersion', 'v2'),
                           ('apiVersion', 1), ('apiVersion', [])]:
            with self.subTest(key=key, value=value):
                d = payload(); d['items'][0][key] = value
                rc, calls, rows = execute(d)
                r = rows['F-I1']
                self.assertEqual((rc, r['category'], r['complete'], r['output']),
                                 (1, 'PARSE_ERROR', False, ''))
                self.assertFalse({x[0] for x in calls} & DEPS)
                self.assertIsNone(rows['F-CS']['category'])
                self.assertIsNone(rows['F-CNP']['category'])

    def test_omission_does_not_bypass_identity_gate(self):
        d = payload(('kind', 'apiVersion'))
        for p in d['items']:
            for s in p['status'].get('containerStatuses', []):
                if s['name'] == 'calico-node': s['imageID'] = 'sha256:' + '0' * 64
        rc, calls, rows = execute(d)
        r = rows['F-I1']
        self.assertEqual((rc, r['category'], r['complete']), (1, 'UNSUPPORTED', False))
        self.assertTrue(r['output'])
        self.assertFalse({x[0] for x in calls} & DEPS)

if __name__ == '__main__': unittest.main(verbosity=2)
