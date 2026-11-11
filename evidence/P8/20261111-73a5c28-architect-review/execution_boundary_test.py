"""Remaining R1/R4 execution boundaries. Offline: synthetic transport and local AF_UNIX pair.
No TCP/DNS/SSH/registry/cluster. Run from repo root with P8C_REVIEW_ROOT=$PWD.
"""
import contextlib,http.client,json,os,pathlib,socket,subprocess,sys,tempfile,threading,time,unittest
from unittest.mock import patch
ROOT=pathlib.Path(os.environ.get('P8C_REVIEW_ROOT',pathlib.Path.cwd())).resolve()
sys.path.insert(0,str(ROOT/'portal/tools/readiness'));sys.path.insert(0,str(ROOT/'portal/tools'))
import wrapper as w
import test_route_e2e as routes

class TransportBoundaries(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=pathlib.Path(self.tmp.name)
  p=patch.object(w,'RESERVATION_BASE',str(self.root/'authority'));p.start();self.addCleanup(p.stop)
  self.g={'package_sha256':'c'*64};w._reset_transport();w._reset_read_cache();w._set_budget_base({});w._set_budget_context(self.g,None,{})
  self.addCleanup(w._set_budget_context,None,None,None);self.addCleanup(w._set_budget_base,{});self.addCleanup(w._reset_transport)
 def test_http_absolute_deadline_during_trickle_read(self):
  # HTTPResponse's real blocking read on an anonymous local socketpair. No IP network.
  left,right=socket.socketpair();left.settimeout(.05);self.addCleanup(left.close);self.addCleanup(right.close)
  def writer():
   try:
    right.sendall(b'HTTP/1.1 200 OK\r\nContent-Length: 20\r\n\r\n')
    for _ in range(20):time.sleep(.02);right.sendall(b'x')
   except OSError:pass
  thread=threading.Thread(target=writer,daemon=True);thread.start()
  resp=http.client.HTTPResponse(left);resp.begin()
  class Opener:
   def open(self,*a,**k):return resp
  begin=time.monotonic()
  with patch('urllib.request.build_opener',return_value=Opener()):
   with self.assertRaises(w.ReadError):w._io_call(w.default_http_get,'http://127.0.0.1:9187/metrics',.05,1024)
  elapsed=time.monotonic()-begin
  left.close();right.close();thread.join(1)
  self.assertLessEqual(elapsed,.11,{'deadline':.05,'allowed_scheduling_margin':.06,'elapsed':elapsed})
 def test_wal_remaining_decreases_inside_sample(self):
  w.write_budget(self.g,{'wal_seconds':w.WAL_SEC_CAP-1});clock=[0.0];seen=[]
  cluster=json.dumps({'kind':'Cluster','apiVersion':'postgresql.cnpg.io/v1','metadata':{'uid':'c'},'status':{'currentPrimary':'portal-db-1'}}).encode()
  def raw(k,p,timeout,cap):
   seen.append(timeout)
   if len(seen)==1:clock[0]+=.75;return cluster,0
   raise w.ReadError('synthetic stop')
  with patch.object(w.time,'monotonic',side_effect=lambda:clock[0]),patch.object(w,'run_kubectl_raw',side_effect=raw):w.run_wal_sample('FAKE',None,None,self.g)
  self.assertEqual(len(seen),2,seen);self.assertLessEqual(seen[1],.25,seen)
 def test_kubectl_partial_error_counts_wal_subset(self):
  fake=self.root/'fake-kubectl';fake.write_text('#!'+sys.executable+'\nimport os,time\nos.write(1,b"x"*64)\ntime.sleep(1)\n');fake.chmod(0o700)
  with patch.object(w.wal,'REQ_TIMEOUT',.05):result=w.run_wal_sample(str(fake),None,None,self.g)
  b=w.read_budget(self.g);self.assertEqual(result[0],w.INCONCLUSIVE);self.assertEqual(b['bytes'],64,b);self.assertEqual(b['wal_bytes'],64,b)
 def test_overall_overrun_does_not_skip_wal_consumption(self):
  w.write_budget(self.g,{'bytes':w.OVERALL_BODY_CAP-1})
  class Response:
   def __enter__(self):return self
   def __exit__(self,*a):pass
   def read(self,n):return b'xx'
  class Opener:
   def open(self,*a,**k):return Response()
  with patch('urllib.request.build_opener',return_value=Opener()):
   with self.assertRaises(w.ReadError):w.default_http_get('http://127.0.0.1:9187/metrics',5,1)
  b=w.read_budget(self.g);self.assertEqual(b['bytes'],w.OVERALL_BODY_CAP+1,b);self.assertEqual(b['wal_bytes'],2,b)
 def test_window_wait_cannot_outspend_wal_remaining(self):
  w.write_budget(self.g,{'wal_seconds':w.WAL_SEC_CAP-1});clock=[0.0];waits=[]
  def raw(*a):raise w.ReadError('synthetic request failure')
  def sleep(n):waits.append(n);clock[0]+=n
  with patch.object(w.time,'monotonic',side_effect=lambda:clock[0]),patch.object(w.time,'sleep',side_effect=sleep),patch.object(w,'run_kubectl_raw',side_effect=raw):
   w.run_wal_window('FAKE',None,self.g,str(self.root),None)
  self.assertLessEqual(sum(waits),1,{'waits':waits,'authority':w.read_budget(self.g)})

class RouteMatrix(unittest.TestCase):
 def setup_route(self,kind,private_rc=2):
  if kind=='seed':
   case=routes.SeedRouteE2E('test_create_allowed_full_route');case.setUp();case._ctx(private_rc)
   case.ctx['FIRST_CREATION_GATE']=json.dumps(routes._gate())
   _,fail=routes._run_job_steps(case.seed['jobs']['precheck']['steps'],case.env,case.ctx)
   outputs=dict(line.split('=',1) for line in (case.t/'gout').read_text().splitlines() if '=' in line)
   case.ctx['PRECHECK_RESULT']=outputs.get('result','STOP');steps=case.seed['jobs']['seed']['steps']
  else:
   case=routes.ReleaseRouteE2E('test_full_route_all_mandatory_steps_zero');case.setUp();case._prep_release();steps=case.release['jobs']['release']['steps'];fail=[]
  self.addCleanup(case.doCleanups)
  return case,steps,fail
 def test_seed_reuse_stop_full_routing_no_build(self):
  for rc,want in [(0,'REUSE'),(1,'STOP')]:
   with self.subTest(outcome=want):
    case,steps,prefail=self.setup_route('seed',rc);calls=[]
    self.assertEqual(case.ctx['PRECHECK_RESULT'],want)
    routes._write(case.d/'buildctl','#!/bin/sh\necho called >> "'+str(case.t/'forbidden-build')+'"\nexit 97\n')
    if not prefail:
     names,fail=routes._run_job_steps(steps,case.env,case.ctx);self.assertFalse(fail);calls=names
    else:self.assertEqual(want,'STOP') # needs:precheck blocks dependent job
    self.assertFalse((case.t/'forbidden-build').exists(),calls)
 def test_readiness_build_proof_failure_matrix(self):
  for kind in ['seed','release']:
   for fault in ['readiness','build','proof']:
    with self.subTest(route=kind,fault=fault):
     case,steps,prefail=self.setup_route(kind);self.assertFalse(prefail)
     routes._write(case.d/'sleep','#!/bin/sh\nexit 0\n') # virtualize retry delay only
     if fault=='readiness':routes._write(case.d/'buildctl','#!/bin/sh\nexit 42\n')
     elif fault=='build':routes._write(case.d/'buildctl','#!/bin/sh\ncase "$*" in *debug*) exit 0;; esac\nexit 42\n')
     else:
      shim=(case.d/'python3').read_text();shim=shim.replace('  registry)\n','  registry)\n    exit 42\n');routes._write(case.d/'python3',shim)
     trace=[];real=routes._run_step
     def track(step,*a,**k):
      r=real(step,*a,**k);trace.append({'name':step.get('name'),'always':step.get('if')=='always()','exit':r.returncode});return r
     with patch.object(routes,'_run_step',side_effect=track):names,fail=routes._run_job_steps(steps,case.env,case.ctx)
     self.assertTrue(fail,trace);first=next(i for i,x in enumerate(trace) if x['exit']!=0)
     self.assertTrue(all(x['always'] for x in trace[first+1:]),trace)
     self.assertTrue(any('Cleanup buildkit' in x['name'] and x['exit']==0 for x in trace),trace)
 def test_timeout_exception_still_reaches_cleanup(self):
  case,steps,_=self.setup_route('release');trace=[];real=routes._run_step;thrown=False
  def track(step,*a,**k):
   trace.append(step.get('name',''))
   if step.get('name','').startswith('Build OCI image'):raise subprocess.TimeoutExpired(['synthetic-build-process'],90)
   return real(step,*a,**k)
  with patch.object(routes,'_run_step',side_effect=track):
   try:routes._run_job_steps(steps,case.env,case.ctx)
   except subprocess.TimeoutExpired:thrown=True
  self.assertTrue(any(x.startswith('Cleanup buildkit') for x in trace),{'uncaught_timeout':thrown,'trace':trace})

if __name__=='__main__':unittest.main(verbosity=2)
