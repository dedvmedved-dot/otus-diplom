"""Residual R1-R4 controls; synthetic transport only, run from repository root.
P8C_REVIEW_ROOT=$PWD python3 <this-file> -v
"""
import contextlib,json,os,pathlib,subprocess,sys,tempfile,unittest
from unittest.mock import patch
ROOT=pathlib.Path(os.environ.get('P8C_REVIEW_ROOT',pathlib.Path.cwd())).resolve()
sys.path.insert(0,str(ROOT/'portal/tools/readiness'));sys.path.insert(0,str(ROOT/'portal/tools'))
import wrapper as w
import test_contract_authority_working as f
import test_route_e2e as routes

class Budgets(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=pathlib.Path(self.tmp.name)
  p=patch.object(w,'RESERVATION_BASE',str(self.root/'authority'));p.start();self.addCleanup(p.stop)
  self.g={'package_sha256':'b'*64};w._reset_transport();w._reset_read_cache();w._set_budget_base({});w._set_budget_context(self.g,None,{})
  self.addCleanup(w._set_budget_context,None,None,None);self.addCleanup(w._set_budget_base,{});self.addCleanup(w._reset_transport)
 def test_wal_timeout_respects_overall_remaining(self):
  base={'seconds':w.OVERALL_SEC_CAP-1};w.write_budget(self.g,base);w._set_budget_base(base);seen=[]
  def raw(k,p,timeout,cap):seen.append(timeout);raise w.ReadError('synthetic timeout')
  with patch.object(w,'run_kubectl_raw',side_effect=raw):w.run_wal_sample('FAKE',None,None,self.g)
  self.assertEqual(len(seen),1);self.assertLessEqual(seen[0],1,seen)
 def test_wal_timeout_respects_wal_remaining(self):
  base={'wal_seconds':w.WAL_SEC_CAP-1};w.write_budget(self.g,base);w._set_budget_base(base);seen=[]
  def raw(k,p,timeout,cap):seen.append(timeout);raise w.ReadError('synthetic timeout')
  with patch.object(w,'run_kubectl_raw',side_effect=raw):w.run_wal_sample('FAKE',None,None,self.g)
  self.assertEqual(len(seen),1);self.assertLessEqual(seen[0],1,seen)
 def test_read_timeout_uses_current_authority_remaining(self):
  # Another completed charge advanced authority since this process loaded its base.
  w.write_budget(self.g,{'seconds':w.OVERALL_SEC_CAP-1});seen=[]
  def raw(k,p,timeout,cap):seen.append(timeout);raise w.ReadError('synthetic timeout')
  with patch.object(w,'run_kubectl_raw',side_effect=raw):
   with self.assertRaises(w.ReadError):w.run_read(json.loads(w.READSET.read_text()),'HC-OP','FAKE')
  self.assertEqual(len(seen),1);self.assertLessEqual(seen[0],1,seen)
 def test_late_http_chunk_still_counts_bytes(self):
  clock=[0.0]
  class Response:
   def __enter__(self):return self
   def __exit__(self,*a):pass
   def read(self,n):clock[0]=6;return b'x'*64
  class Opener:
   def open(self,*a,**k):return Response()
  with patch('urllib.request.build_opener',return_value=Opener()),patch.object(w.time,'monotonic',side_effect=lambda:clock[0]):
   with self.assertRaises(w.ReadError):w._io_call(w.default_http_get,'http://127.0.0.1:9187/metrics',5,1024)
  self.assertGreaterEqual(w.read_budget(self.g).get('bytes',0),64)
 def test_http_partial_charged_to_wal_subset(self):
  cluster={'kind':'Cluster','apiVersion':'postgresql.cnpg.io/v1','metadata':{'uid':'c'},'status':{'currentPrimary':'portal-db-1'}}
  pod={'kind':'Pod','apiVersion':'v1','metadata':{'uid':'p'},'status':{'podIP':'127.0.0.1'}}
  bodies=[json.dumps(cluster).encode(),json.dumps(pod).encode()];seq=iter(bodies)
  class Response:
   n=0
   def __enter__(self):return self
   def __exit__(self,*a):pass
   def read(self,n):
    self.n+=1
    if self.n==1:return b'x'*64
    raise OSError('synthetic partial')
  class Opener:
   def open(self,*a,**k):return Response()
  with patch.object(w,'run_kubectl_raw',side_effect=lambda *a:(next(seq),0)),patch('urllib.request.build_opener',return_value=Opener()):
   result=w.run_wal_sample('FAKE',w.default_http_get,None,self.g)
  b=w.read_budget(self.g);expected=sum(map(len,bodies))+64
  self.assertEqual(result[0],w.INCONCLUSIVE);self.assertEqual(b['bytes'],expected)
  self.assertEqual(b['wal_bytes'],expected,b)

class HealthWindow(unittest.TestCase):
 setUp=f.WindowRoutes.setUp
 raw=f.WindowRoutes.raw
 http=f.WindowRoutes.http
 invoke=f.WindowRoutes.invoke
 def test_positive_s0(self):self.assertEqual(self.invoke()[0],0)
 def test_retry_response_after_dns_deadline_not_pass(self):
  original=self.raw;path=self.rs['HC-DNS']['path'];calls=[]
  def raw(*args):
   if args[1]==path:
    calls.append({'start':self.mono[0],'timeout':args[2]})
    if len(calls)<5:return json.dumps(f.old.listing('EndpointSliceList','discovery.k8s.io/v1',[])).encode(),0
    if len(calls)==5:
     elapsed=min(11,args[2]);self.mono[0]+=elapsed;self.now[0]+=elapsed
     if args[2]<11:raise w.ReadError('synthetic deadline')
   return original(*args)
  self.raw=raw;code,j=self.invoke()
  self.assertNotEqual(code,0,{'calls':calls,'dns':j['reads']['HC-DNS'],'aggregate':j['aggregate']})

class SeedBinding(unittest.TestCase):
 def run_gate(self,mutation=None,runtime='1'):
  with tempfile.TemporaryDirectory() as td:
   gate=routes._gate()
   if mutation:mutation(gate)
   p=pathlib.Path(td)/'g.json';p.write_text(json.dumps(gate));env=dict(os.environ,GITHUB_SHA=gate['source_sha'],GITHUB_REPOSITORY=routes.REPO,GITHUB_WORKFLOW_SHA=gate['workflow_sha'])
   env.pop('GITHUB_RUN_ATTEMPT',None)
   if runtime is not None:env['GITHUB_RUN_ATTEMPT']=runtime
   return subprocess.run([sys.executable,str(ROOT/'portal/tools/release-check.py'),'first-creation',str(p)],env=env,capture_output=True,text=True,timeout=10)
 def test_positive_bound_attempt_one(self):
  r=self.run_gate();self.assertEqual(r.returncode,0,r.stderr)
 def test_missing_runtime_binding_rejected(self):
  r=self.run_gate(runtime=None);self.assertNotEqual(r.returncode,0,r.stdout)
 def test_missing_document_binding_rejected(self):
  r=self.run_gate(lambda g:g.pop('attempt'));self.assertNotEqual(r.returncode,0,r.stdout)
 def test_null_document_binding_rejected(self):
  r=self.run_gate(lambda g:g.update(attempt=None));self.assertNotEqual(r.returncode,0,r.stdout)

class CleanupOutcome(unittest.TestCase):
 def test_cleanup_nonzero_cannot_report_route_pass(self):
  case=routes.ReleaseRouteE2E('test_full_route_all_mandatory_steps_zero');case.setUp();self.addCleanup(case.doCleanups);case._prep_release()
  # Inject a process result at the cleanup-step boundary; this tests the runner's
  # handling of nonzero, not a claim that the production cleanup shell currently fails.
  seen=[];real=routes._run_step
  def track(step,*a,**k):
   if step.get('name','').startswith('Cleanup buildkit'):
    rr=subprocess.CompletedProcess(['synthetic-cleanup-process'],42,'','synthetic cleanup failure')
   else:rr=real(step,*a,**k)
   seen.append((step.get('name'),rr.returncode));return rr
  with patch.object(routes,'_run_step',side_effect=track):
   names,failures=routes._run_job_steps(case.release['jobs']['release']['steps'],case.env,case.ctx)
  self.assertTrue(any('Cleanup buildkit' in n and rc==42 for n,rc in seen),seen)
  self.assertTrue(failures,{'failures':failures,'trace':seen})

if __name__=='__main__':unittest.main(verbosity=2)
