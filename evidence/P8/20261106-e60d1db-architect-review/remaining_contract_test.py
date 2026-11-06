"""Existing f975527/8784116 contract controls; offline synthetic fixtures only.
Run from repository root: P8C_REVIEW_ROOT=$PWD python3 independent/remaining_contract_test.py -v
No cluster, registry, CI or network. Historical fixtures/source are not modified.
"""
import contextlib,importlib.util,io,json,multiprocessing,os,subprocess,sys,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(os.environ.get('P8C_REVIEW_ROOT',Path.cwd())).resolve()
sys.path.insert(0,str(ROOT/'portal/tools/readiness'))
import wrapper as w
import test_contract_authority_working as fixture
SOURCE='9a4ed77d3131d0b2078b6917e1a7d4419ec02b65'
REPO='dedvmedved-dot/otus-diplom'
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def charge_worker(authority,gate,base,barrier,queue):
 w.RESERVATION_BASE=authority;w._reset_transport();w._set_budget_base(base);w._set_budget_context(gate,None,base)
 barrier.wait(timeout=10)
 try:w._count_request();queue.put('charged')
 except w.ReadError:queue.put('blocked')

class BudgetTransport(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.root=Path(self.t.name)
  self.g={'package_sha256':'a'*64};self.p=patch.object(w,'RESERVATION_BASE',str(self.root/'authority'));self.p.start();self.addCleanup(self.p.stop)
  w._reset_transport();w._set_budget_base({});w._set_budget_context(None,None,None)
  self.addCleanup(w._set_budget_context,None,None,None)
 def concurrent(self,base):
  w.write_budget(self.g,base);ctx=multiprocessing.get_context('fork');barrier=ctx.Barrier(2);q=ctx.Queue()
  ps=[ctx.Process(target=charge_worker,args=(w.RESERVATION_BASE,self.g,base,barrier,q)) for _ in range(2)]
  for p in ps:p.start()
  for p in ps:p.join(10);self.assertEqual(p.exitcode,0)
  results=[q.get(timeout=2) for _ in ps];q.close()
  return results,json.loads(Path(w.budget_path(self.g)).read_text())
 def test_independent_concurrent_charges_are_additive(self):
  results,b=self.concurrent({'requests':0});self.assertEqual(results.count('charged'),2);self.assertEqual(b['requests'],2,b)
 def test_last_request_slot_cannot_be_spent_twice(self):
  results,b=self.concurrent({'requests':232});self.assertEqual(results.count('charged'),1,(results,b))
 def test_elapsed_seconds_persist_before_next_io(self):
  w._set_budget_context(self.g,None,{'seconds':0});w._count_seconds(10)
  self.assertEqual(json.loads(Path(w.budget_path(self.g)).read_text())['seconds'],10)
 def fake(self,payload):
  p=self.root/'fake-kubectl';p.write_text('#!'+sys.executable+'\nimport os\nos.write(1,'+repr(payload)+')\n');p.chmod(0o700);return str(p)
 def test_exact_cap_control(self):
  body,code=w.run_kubectl_raw(self.fake(b'{}'),'/api/v1/pods',2,2);self.assertEqual((body,code),(b'{}',0))
 def test_valid_prefix_cannot_hide_over_cap_suffix(self):
  with self.assertRaises(w.ReadError):w.run_kubectl_raw(self.fake(b'{}UNVALIDATED_SUFFIX'),'/api/v1/pods',2,2)

class MainRoutes(unittest.TestCase):
 setUp=fixture.WindowRoutes.setUp
 raw=fixture.WindowRoutes.raw
 http=fixture.WindowRoutes.http
 invoke=fixture.WindowRoutes.invoke
 def test_realistic_cluster_scoped_namespace_list_control(self):
  path=self.rs['PR-6']['paths'][7]
  self.docs[path]['items']=[{'apiVersion':'v1','kind':'Namespace','metadata':{'name':'portal','uid':'namespace-portal','labels':{'kubernetes.io/metadata.name':'portal'}}}]
  code,j=self.invoke();self.assertEqual(code,0,j['reads']['PR-6'])
 def test_s0_positive_control(self):
  code,j=self.invoke();self.assertEqual((code,j['aggregate']),(0,w.PASS))
 def test_transient_operator_has_full_accepted_health_window(self):
  original=self.raw;seen=[];path=self.rs['HC-OP']['path']
  def raw(*args):
   if args[1]==path:
    seen.append(self.mono[0])
    if len(seen)<=2:return json.dumps(fixture.old.listing('PodList','v1',[])).encode(),0
   return original(*args)
  self.raw=raw;code,j=self.invoke()
  self.assertEqual(code,0,{'operator_reads_at':seen,'operator':j['reads']['HC-OP']})
 def test_wrong_stage_gate_failed_action_receipt_blocks(self):
  self.assertEqual(self.invoke()[0],0);self.g['operation_end_utc']=self.now[0]
  self.g['action_receipt']={'source_sha':self.g['source_sha'],'package_sha256':self.g['package_sha256'],
    'operation_end_utc':self.now[0],'stage':'S4','gate_sha256':'0'*64,'outcome':'FAIL'}
  code,j=self.invoke('S1');self.assertNotEqual(code,0,j['aggregate'])
 def test_wal_metrics_cap_uses_remaining_overall_body(self):
  w._reset_transport();w._set_budget_context(None,None,None)
  paths=['/apis/postgresql.cnpg.io/v1/namespaces/portal/clusters/portal-db','/api/v1/namespaces/portal/pods/'+self.docs[self.rs['HC-DB']['path']]['status']['currentPrimary']]
  initial=sum(len(json.dumps(self.docs[p]).encode()) for p in paths)
  w._set_budget_base({'bytes':w.OVERALL_BODY_CAP-initial-1});caps=[]
  def http(url,timeout,cap):caps.append(cap);return b'xx'
  try:
   with patch.object(w,'run_kubectl_raw',side_effect=self.raw):w.run_wal_sample('FAKE',http,self.g['clock_evidence'],self.g)
   self.assertEqual(caps,[1],caps)
  finally:w._set_budget_base({});w._reset_transport()

class ReleaseBindings(unittest.TestCase):
 def check(self,mode,gate,attempt='1'):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'gate.json';p.write_text(json.dumps(gate));args=[sys.executable,str(ROOT/'portal/tools/release-check.py'),mode,str(p)]
   if mode=='release-gate':args += [SOURCE,REPO,attempt]
   env=dict(os.environ,GITHUB_SHA=SOURCE,GITHUB_REPOSITORY=REPO,GITHUB_WORKFLOW_SHA=SOURCE)
   return subprocess.run(args,capture_output=True,text=True,env=env,timeout=10)
 def test_release_missing_fields_rejected(self):
  r=self.check('release-gate',{'source_sha':SOURCE});self.assertNotEqual(r.returncode,0,r.stdout)
 def test_release_expired_test_only_rejected(self):
  r=self.check('release-gate',{'source_sha':SOURCE,'repository':REPO,'attempt':1,'expiry_hours':24,'issued_at_utc':'2000-01-01T00:00:00Z','mode':'TEST_ONLY'});self.assertNotEqual(r.returncode,0,r.stdout)
 def test_release_attempt_two_rejected(self):
  r=self.check('release-gate',{'source_sha':SOURCE,'attempt':2},'2');self.assertNotEqual(r.returncode,0,r.stdout)
 def seed(self):return {'source_sha':SOURCE,'mode':'LIVE','issued_at_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'expiry_hours':1}
 def test_seed_missing_package_repository_workflow_rejected(self):
  r=self.check('first-creation',self.seed());self.assertNotEqual(r.returncode,0,r.stdout)
 def test_seed_unbound_workflow_rejected(self):
  g=self.seed();g.update(repository=REPO,package='ghcr.io/dedvmedved-dot/otus-diplom-portal',workflow_sha='b'*40)
  r=self.check('first-creation',g);self.assertNotEqual(r.returncode,0,r.stdout)
 def test_seed_positive_bound_control(self):
  g=self.seed();g.update(repository=REPO,package='ghcr.io/dedvmedved-dot/otus-diplom-portal',workflow_sha=SOURCE)
  r=self.check('first-creation',g);self.assertEqual(r.returncode,0,r.stderr)
 def test_cached_verified_status_does_not_verify_another_pin(self):
  m=load('pins_review',ROOT/'portal/tools/verify-pins.py')
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'lock.json';p.write_text(json.dumps({'binaries':[],'actions':[{'id':'checkout','repo':'actions/checkout','sha':'a'*40,'tag_annotation':'synthetic'}],'images':[]}))
   (Path(tmp)/'pin-verification.json').write_text(json.dumps({'results':[{'id':'checkout','status':'VERIFIED','commit_sha':'b'*40,'tag_annotation_not_authoritative':'synthetic'}]}))
   with patch.object(m,'LOCK',str(p)),patch.object(m,'CACHE',tmp),contextlib.redirect_stdout(io.StringIO()):code=m.verify_offline()
   self.assertNotEqual(code,0)

if __name__=='__main__':unittest.main(verbosity=2)
