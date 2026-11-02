"""MI-02 residual: optional status is not an error; never mask a proven leaf failure.
Offline main-path harness; no live subprocess. Expected fdf/4913 behavior is recorded,
not treated as live raw evidence. Run beside followup_test.py and its dependencies.
"""
import copy
import io
import json
import unittest
from contextlib import redirect_stdout, redirect_stderr
import followup_test as t

DEPS={'F-NP','F-GNP','F-FELIX','F-HEP','F-TIER'}
CANARY='MI02_DIAGNOSTIC_CANARY'

class TestOptionalStatusDiagnostic(unittest.TestCase):
    def check(self, status_mode, field, value, code):
        p=copy.deepcopy(t.POD_CFG)
        if status_mode=='absent': p.pop('status',None)
        elif status_mode=='null': p['status']=None
        elif status_mode=='empty': p['status']={}
        p['metadata']['name']=CANARY
        p['spec']['containers'][0][field]=value
        stdout=io.StringIO();stderr=io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            rc,calls,rows=t.run({'F-I1':t.R(0,t.podlist([p]))})
        r=t.by_id(rows)['F-I1']
        self.assertEqual((rc,r['category'],r['diag'],r['complete'],r['output']),
                         (1,'PARSE_ERROR','ITEM',False,''))
        self.assertFalse({c[0] for c in calls}&DEPS)
        self.assertIsNone(t.by_id(rows)['F-CS']['category'])
        self.assertIsNone(t.by_id(rows)['F-CNP']['category'])
        self.assertNotIn(CANARY,json.dumps(rows)+stdout.getvalue()+stderr.getvalue())
        # OTHER permitted by Architect when not confidently distinguishable.
        self.assertIn(r['itemDiag'],(code,'OTHER'))

    def test_optional_status_does_not_mask_image(self):
        for mode in ('absent','null','empty'):
            with self.subTest(mode=mode): self.check(mode,'image',123,'IMAGE')

    def test_optional_status_does_not_mask_ports(self):
        for mode in ('absent','null','empty'):
            with self.subTest(mode=mode): self.check(mode,'ports',[{'containerPort':0}],'PORTS')

    def test_optional_status_does_not_mask_restart(self):
        for mode in ('absent','null','empty'):
            with self.subTest(mode=mode): self.check(mode,'restartPolicy',False,'RESTART_POLICY')

    def test_true_malformed_status_stays_status(self):
        for bad in (False,0,'',[],[{}]):
            with self.subTest(bad=bad):
                p=copy.deepcopy(t.POD_CFG);p['status']=bad
                rc,calls,rows=t.run({'F-I1':t.R(0,t.podlist([p]))})
                r=t.by_id(rows)['F-I1']
                self.assertEqual((rc,r['category'],r['itemDiag'],r['output']),
                                 (1,'PARSE_ERROR','STATUS',''))
                self.assertFalse({c[0] for c in calls}&DEPS)

if __name__=='__main__':unittest.main(verbosity=2)
