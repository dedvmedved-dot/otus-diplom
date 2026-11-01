"""Final bounded-projection contract: offline mocked tests, no live calls."""
import copy,json,unittest
from unittest import mock
import followup_test as t
KEY={'F-CNP':'cnp','F-NP':'np','F-GNP':'gnp','F-HEP':'hep','F-TIER':'tier'}
class BoundedProjection(unittest.TestCase):
 def execute(self,rid,pages):
  original=t.fw.PROJECTOR[KEY[rid]]
  with mock.patch.dict(t.fw.PROJECTOR,{KEY[rid]:mock.Mock(wraps=original)}):
   spy=t.fw.PROJECTOR[KEY[rid]]
   rc,calls,rows=t.run({rid:pages})
   return rc,calls,t.by_id(rows)[rid],spy.call_count
 def test_single_501_projects_only_500(self):
  for rid,obj in t.OBJ.items():
   with self.subTest(rid=rid):
    rc,calls,r,n=self.execute(rid,t.R(0,t.page(rid,t.objects(obj,501))))
    self.assertEqual(n,500)
    self.assertEqual((rc,r['category'],r['complete']),(1,'PARTIAL',False))
    self.assertEqual(r['journal'][0]['received'],501)
    self.assertEqual(r['journal'][0]['validated'],500)
    self.assertEqual(len(json.loads(r['output'])),500)
 def test_third_page_remaining_budget(self):
  for rid,obj in t.OBJ.items():
   with self.subTest(rid=rid):
    objs=t.objects(obj,501)
    rc,calls,r,n=self.execute(rid,[t.R(0,t.page(rid,objs[:200],'a')),t.R(0,t.page(rid,objs[200:400],'b')),t.R(0,t.page(rid,objs[400:]))])
    self.assertEqual(n,500)
    self.assertEqual([j['validated'] for j in r['journal']],[200,200,100])
    self.assertEqual([j['received'] for j in r['journal']],[200,200,101])
    self.assertEqual(sum(c[0]==rid for c in calls),3)
    self.assertEqual((r['category'],r['complete']),('PARTIAL',False))
 def test_invalid_discarded_suffix_not_projected(self):
  for rid,obj in t.OBJ.items():
   for malformed in (True,False):
    with self.subTest(rid=rid,malformed=malformed):
     objs=t.objects(obj,501)
     if malformed:objs[500]['spec']='bad'
     else:objs[500]['spec']['UNKNOWN']='SYNTHETIC_SUFFIX_CANARY'
     rc,calls,r,n=self.execute(rid,t.R(0,t.page(rid,objs)))
     self.assertEqual(n,500)
     self.assertEqual((r['category'],r['complete']),('PARTIAL',False))
     self.assertEqual(len(json.loads(r['output'])),500)
     self.assertNotIn('SYNTHETIC_SUFFIX_CANARY',json.dumps(r))
 def test_validated_count_on_midpage_error(self):
  for rid,obj in t.OBJ.items():
   with self.subTest(rid=rid):
    bad=copy.deepcopy(obj);bad['spec']='bad'
    rc,calls,r,n=self.execute(rid,[t.R(0,t.page(rid,[obj,bad],'next')),t.R(0,t.page(rid,[obj]))])
    self.assertEqual((rc,r['category'],r['complete'],r['output']),(1,'PARSE_ERROR',False,''))
    self.assertEqual(sum(c[0]==rid for c in calls),1)
    self.assertEqual(r['journal'][0]['received'],2)
    self.assertEqual(r['journal'][0]['validated'],1)
if __name__=='__main__':unittest.main(verbosity=2)

