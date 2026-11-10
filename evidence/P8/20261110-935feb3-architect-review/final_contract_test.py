"""Existing R1-R4 contract: final controls, synthetic/offline only.
Run from repository root with P8C_REVIEW_ROOT=$PWD python3 <this-file> -v.
"""
import contextlib,copy,io,json,os,pathlib,subprocess,sys,tempfile,time,unittest
from unittest.mock import patch
ROOT=pathlib.Path(os.environ.get('P8C_REVIEW_ROOT',pathlib.Path.cwd())).resolve()
sys.path.insert(0,str(ROOT/'portal/tools/readiness'));sys.path.insert(0,str(ROOT/'portal/tools'))
import wrapper as w
import test_contract_authority_working as f
import test_route_e2e as routes
SOURCE='3422e31e97742dd32ad5044451eb062ee5dacf1d'

class BudgetTermination(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=pathlib.Path(self.tmp.name)
  self.g={'package_sha256':'a'*64};p=patch.object(w,'RESERVATION_BASE',str(self.root/'authority'));p.start();self.addCleanup(p.stop)
  w._reset_transport();w._reset_read_cache();self.addCleanup(w._set_budget_context,None,None,None);self.addCleanup(w._set_budget_base,{})
 def test_no_second_io_after_overall_time_exhaustion(self):
  base={'seconds':w.OVERALL_SEC_CAP-1};w.write_budget(self.g,base);w._set_budget_base(base);w._set_budget_context(self.g,None,base)
  rs=json.loads(w.READSET.read_text());doc=f.old.fixtures()[rs['reads']['HC-OP']['path']];clock=[0.0];calls=[]
  def raw(k,path,timeout,cap):
   calls.append({'timeout':timeout,'start':clock[0]});clock[0]+=min(2,timeout)
   if timeout<=2:raise w.ReadError('synthetic deadline')
   return json.dumps(doc).encode(),0
  with patch.object(w,'run_kubectl_raw',side_effect=raw),patch.object(w.time,'monotonic',side_effect=lambda:clock[0]):
   for _ in range(2):
    w._reset_read_cache()
    try:w.run_read(rs,'HC-OP','FAKE')
    except w.ReadError:pass
  self.assertEqual(len(calls),1,{'calls':calls,'authority':w.read_budget(self.g)})
 def test_timeout_argument_is_bounded_by_remaining_overall(self):
  base={'seconds':w.OVERALL_SEC_CAP-1};w.write_budget(self.g,base);w._set_budget_base(base);w._set_budget_context(self.g,None,base)
  rs=json.loads(w.READSET.read_text());seen=[]
  def raw(k,path,timeout,cap):seen.append(timeout);raise w.ReadError('synthetic')
  with patch.object(w,'run_kubectl_raw',side_effect=raw):
   with self.assertRaises(w.ReadError):w.run_read(rs,'HC-OP','FAKE')
  self.assertTrue(seen);self.assertLessEqual(seen[0],1,seen)
 def test_http_partial_body_is_charged_on_read_error(self):
  w.write_budget(self.g,{});w._set_budget_base({});w._set_budget_context(self.g,None,{})
  class Response:
   n=0
   def __enter__(self):return self
   def __exit__(self,*a):pass
   def read(self,size):
    self.n+=1
    if self.n==1:return b'x'*64
    raise OSError('synthetic read failure')
  class Opener:
   def open(self,*a,**k):return Response()
  with patch('urllib.request.build_opener',return_value=Opener()):
   with self.assertRaises(w.ReadError):w._io_call(w.default_http_get,'http://127.0.0.1:9187/metrics',5,1024)
  self.assertGreaterEqual(w.read_budget(self.g)['bytes'],64)

class HealthWindows(unittest.TestCase):
 setUp=f.WindowRoutes.setUp
 raw=f.WindowRoutes.raw
 http=f.WindowRoutes.http
 invoke=f.WindowRoutes.invoke
 def test_positive_s0_control(self):self.assertEqual(self.invoke()[0],0)
 def test_late_dns_cannot_turn_expired_window_into_pass(self):
  original=self.raw;ops=[];dns=[];op=self.rs['HC-OP']['path'];dp=self.rs['HC-DNS']['path']
  def raw(*args):
   if args[1]==op:
    ops.append(self.mono[0])
    if len(ops)<4:return json.dumps(f.old.listing('PodList','v1',[])).encode(),0
   if args[1]==dp:
    dns.append(self.mono[0])
    if self.mono[0]<340:return json.dumps(f.old.listing('EndpointSliceList','discovery.k8s.io/v1',[])).encode(),0
   return original(*args)
  self.raw=raw;code,j=self.invoke()
  self.assertNotEqual(code,0,{'dns_times':dns,'operator_times':ops,'dns':j['reads']['HC-DNS'],'aggregate':j['aggregate']})

class SeedGate(unittest.TestCase):
 def test_actual_second_seed_run_rejected(self):
  with tempfile.TemporaryDirectory() as tmp:
   g=routes._gate();p=pathlib.Path(tmp)/'gate.json';p.write_text(json.dumps(g))
   env=dict(os.environ,GITHUB_SHA=g['source_sha'],GITHUB_REPOSITORY=routes.REPO,GITHUB_WORKFLOW_SHA=g['workflow_sha'],GITHUB_RUN_ATTEMPT='2')
   r=subprocess.run([sys.executable,str(ROOT/'portal/tools/release-check.py'),'first-creation',str(p)],env=env,capture_output=True,text=True,timeout=10)
   self.assertNotEqual(r.returncode,0,r.stdout)

class NegativeRoute(unittest.TestCase):
 def test_release_build_failure_executes_always_cleanup(self):
  case=routes.ReleaseRouteE2E('test_full_route_all_mandatory_steps_zero');case.setUp();self.addCleanup(case.doCleanups);case._prep_release()
  # Fault only the external build binary; production template steps remain unchanged.
  (case.d/'buildctl').write_text('#!/bin/sh\ncase "$*" in *debug*) exit 0;; esac\nexit 42\n');(case.d/'buildctl').chmod(0o700)
  executed=[];real=routes._run_step
  def tracked(step,*a,**k):
   p=real(step,*a,**k);executed.append({'name':step.get('name'),'exit':p.returncode});return p
  with patch.object(routes,'_run_step',side_effect=tracked):
   try:case._run_release_route()
   except AssertionError:pass  # expected failure of the protected operation
  self.assertTrue(any(x['name'].startswith('Build OCI image') and x['exit']==42 for x in executed),executed)
  self.assertFalse(any(x['name'].startswith('Sign keyless') for x in executed),executed)
  self.assertTrue(any(x['name'].startswith('Cleanup buildkit daemon') for x in executed),executed)

if __name__=='__main__':unittest.main(verbosity=2)
