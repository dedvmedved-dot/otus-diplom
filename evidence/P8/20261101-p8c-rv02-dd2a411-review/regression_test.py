"""Behavioral closure checks. All collector subprocesses mocked by followup_test.run."""
import copy,json,pathlib,subprocess,unittest
import followup_test as t
OBJ={'F-CNP':t.CNP,'F-NP':t.NP,'F-GNP':t.GNP,'F-HEP':t.HEP,'F-TIER':t.TIER}
class RemainingContract(unittest.TestCase):
 def test_projector_failure_stops_continuation(self):
  for rid,obj in OBJ.items():
   with self.subTest(rid=rid):
    bad=copy.deepcopy(obj);bad['spec']='bad'
    rc,calls,rows=t.run({rid:[t.R(0,t.page(rid,[bad],'next')),t.R(0,t.page(rid,[obj]))]})
    r=t.by_id(rows)[rid]
    self.assertEqual(sum(c[0]==rid for c in calls),1)
    self.assertEqual((rc,r['category'],r['complete'],r['exit'],r['output']),(1,'PARSE_ERROR',False,0,''))
    self.assertEqual(len(rows),9)
 def test_projector_journal_is_not_success(self):
  for rid,obj in OBJ.items():
   with self.subTest(rid=rid):
    bad=copy.deepcopy(obj);bad['spec']='bad'
    rc,_,rows=t.run({rid:t.R(0,t.page(rid,[bad]))});r=t.by_id(rows)[rid]
    self.assertTrue(r['journal'][0]['cause'])
    self.assertEqual(r['journal'][0]['validated'],0)
    self.assertEqual(r['journal'][0]['returncode'],0)
 def test_unsupported_stops_continuation(self):
  for rid,obj in OBJ.items():
   with self.subTest(rid=rid):
    bad=copy.deepcopy(obj);bad['spec']['UNKNOWN_SEMANTIC']='SYNTHETIC_CANARY'
    rc,calls,rows=t.run({rid:[t.R(0,t.page(rid,[bad],'next')),t.R(0,t.page(rid,[obj]))]})
    r=t.by_id(rows)[rid]
    self.assertEqual(sum(c[0]==rid for c in calls),1)
    self.assertEqual((r['category'],r['complete'],r['output']),('UNSUPPORTED',False,''))
    self.assertNotIn('SYNTHETIC_CANARY',json.dumps(rows))
 def test_unknown_later_process_returncode_is_null(self):
  for rid,obj in OBJ.items():
   for exc in (subprocess.TimeoutExpired('kubectl',20),OSError('SYNTHETIC_CANARY')):
    with self.subTest(rid=rid,error=type(exc).__name__):
     rc,_,rows=t.run({rid:[t.R(0,t.page(rid,[obj],'next')),exc]});r=t.by_id(rows)[rid]
     self.assertIsNone(r['exit'])
     self.assertIsNone(r['journal'][-1]['returncode'])
     self.assertEqual((rc,r['category'],r['complete']),(1,'PARTIAL',False))
     self.assertEqual(len(json.loads(r['output'])),1)
     self.assertNotIn('SYNTHETIC_CANARY',json.dumps(rows))
 def test_one_journal_record_per_repeated_token_attempt(self):
  for rid,obj in OBJ.items():
   with self.subTest(rid=rid):
    rc,calls,rows=t.run({rid:[t.R(0,t.page(rid,[obj],'same')),t.R(0,t.page(rid,[obj],'same'))]});r=t.by_id(rows)[rid]
    actual=sum(c[0]==rid for c in calls)
    self.assertEqual(len(r['journal']),actual)
    self.assertEqual(actual,2)
    self.assertTrue(r['journal'][-1]['cause'])
 def test_duplicate_nonselected_versions_rejected(self):
  for entries in ([{'name':'v2','served':False},{'name':'v2','served':False}],
                  [{'name':'v2','served':False},{'name':'v2','served':True}]):
   with self.subTest(entries=entries):
    c=copy.deepcopy(t.CRD);c['spec']['versions']+=entries
    rc,calls,rows=t.run({'F-CS':t.R(0,json.dumps(c))});r=t.by_id(rows)['F-CS']
    self.assertEqual((rc,r['category'],r['output']),(1,'PARSE_ERROR',''))
    self.assertFalse(any(c[0]=='F-CNP' for c in calls))
 def test_real_archived_identity_mapping(self):
  fixture=json.loads((pathlib.Path(__file__).parent/'derived-i1-fixture.json').read_text())
  rc,_,rows=t.run({'F-I1':t.R(0,json.dumps(fixture['podlist']))})
  self.assertEqual(rc,0)
  self.assertEqual(json.loads(t.by_id(rows)['F-I1']['output']),fixture['expected_projection'])
if __name__=='__main__':unittest.main(verbosity=2)

