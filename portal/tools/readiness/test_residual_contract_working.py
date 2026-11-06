"""Offline review of 52e2e38 against the existing 8784116 contract.
Synthetic transport/clock, actual main/CLI/template steps; no cluster/registry/CI.
Expected assertions specify required behavior, not the current implementation.
"""
import copy,importlib.util,json,os,shutil,subprocess,sys,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
REAL_MONOTONIC=time.monotonic
ROOT=Path(os.environ.get('P8C_REVIEW_ROOT',Path.cwd())).resolve()
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
f=load('r8fixture',ROOT/'evidence/P8/20261105-c8007f5-architect-review/contract_test.py')
w,wal,old=f.w,f.wal,f.old
sys.path.insert(0,str(ROOT/'portal/tools'))
import release_qualification as q
import test_release_negative as rn

class Readiness(unittest.TestCase):
 raw=f.WindowRoutes.raw
 http=f.WindowRoutes.http
 invoke=f.WindowRoutes.invoke
 def setUp(self):
  f.WindowRoutes.setUp(self)
  self.g['clock_evidence']['gate_sha256']=w.gate_identity_sha256(self.g)
 def op_gate(self, stage):
  prev = w.STAGES[w.STAGES.index(stage) - 1]
  self.g['operation_end_utc']=self.now[0]
  self.g['action_receipt']={'source_sha':self.g['source_sha'],'package_sha256':self.g['package_sha256'],'gate_sha256':w.gate_identity_sha256(self.g),'stage':prev,'outcome':w.PASS,'operation_end_utc':self.now[0]}
 def authority(self,**values):
  with patch.object(w,'RESERVATION_BASE',str(self.root/'authority')):
   w.write_budget(self.g,dict(requests=0,bytes=0,seconds=0,**{})|values)
 def test_corrected_authority_exhaustion_blocks_new_state(self):
  self.assertEqual(self.invoke()[0],0)
  self.authority(requests=233)
  other=self.root/'other';other.mkdir();shutil.copyfile(self.state/'stage.receipt',other/'stage.receipt')
  self.calls=[];self.op_gate('S1')
  code,j=self.invoke('S1',state=other)
  self.assertNotEqual(code,0);self.assertEqual(self.calls,[])
 def test_remaining_body_byte_is_enforced_inside_io(self):
  self.authority(bytes=w.OVERALL_BODY_CAP-1)
  code,j=self.invoke()
  self.assertLessEqual(j['budget']['bytes'],w.OVERALL_BODY_CAP,(code,j['budget']))
 def test_remaining_elapsed_second_cannot_authorize_300s_window(self):
  self.authority(seconds=w.OVERALL_SEC_CAP-1)
  code,j=self.invoke()
  self.assertLessEqual(self.mono[0],1,(code,self.mono[0],j['budget']))
 def test_timeout_partial_stdout_is_accounted(self):
  fake=self.root/'kubectl';fake.write_text('#!'+sys.executable+'\nimport sys,time\nsys.stdout.write("x"*64);sys.stdout.flush();time.sleep(2)\n');fake.chmod(0o700)
  real=w.run_kubectl_raw
  def raw(*args):
   self.calls.append(('raw',args[1]))
   with patch.object(w.time,'monotonic',side_effect=REAL_MONOTONIC):
    return real(str(fake),args[1],.03,args[3])
  self.raw=raw;code,j=self.invoke()
  self.assertGreaterEqual(j['budget']['bytes'],64*len(self.calls),(code,len(self.calls),j['budget']))
 def test_first_health_failure_is_not_erased_by_final_sweep(self):
  raw=self.raw;seen=[0]
  def transition(*args):
   body,rc=raw(*args)
   if args[1]==self.rs['HC-DB']['path'] and args[2]==15:
    seen[0]+=1
    if seen[0]==1:
     d=json.loads(body);d['status']['readyInstances']=2;body=json.dumps(d).encode()
   return body,rc
  self.raw=transition;code,j=self.invoke()
  self.assertNotEqual(code,0,(seen[0],j))
 def test_portal_observation_fresh_at_s4_verdict(self):
  for stage in w.STAGE_ORDER[:-1]:
   if stage!='S0':self.op_gate(stage)
   self.assertEqual(self.invoke(stage)[0],0)
  self.op_gate('S4');raw=self.raw;ends=[]
  def slow(*args):
   body,rc=raw(*args)
   if args[2]==15:self.mono[0]+=14;self.now[0]+=14
   if args[1]==self.rs['HC-PORTAL']['path']:ends.append(self.mono[0])
   return body,rc
  self.raw=slow;code,j=self.invoke('S4')
  self.assertTrue(code!=0 or self.mono[0]-ends[-1]<=30,(code,'portal_age',self.mono[0]-ends[-1],j['budget']))
 def test_health_retry_obeys_interval(self):
  raw=self.raw;ends=[]
  def transient(*args):
   body,rc=raw(*args)
   if args[1]==self.rs['HC-DB']['path'] and args[2]==15:
    ends.append(self.mono[0])
    if len(ends)==1:
     d=json.loads(body);d['status']['conditions']=[{'type':'ContinuousArchiving','status':'True'}];body=json.dumps(d).encode()
   return body,rc
  self.raw=transient;code,j=self.invoke()
  self.assertTrue(code!=0 or len(ends)>=2 and ends[1]-ends[0]>=10,(code,ends))
 def test_nested_malformed_health_returns_typed_verdict(self):
  self.docs[self.rs['HC-OP']['path']]['items'][0]['status']='MALFORMED'
  try:code,j=self.invoke()
  except Exception as e:self.fail('uncaught '+type(e).__name__)
  self.assertNotEqual(code,0);self.assertIsNotNone(j)
 def test_pr6_namespace_items_are_validated(self):
  self.docs[self.rs['PR-6']['paths'][7]]['items']=[None]
  code,j=self.invoke();self.assertNotEqual(code,0,j['reads']['PR-6'])
 def test_pr6_list_cap_enforced(self):
  self.docs[self.rs['PR-6']['paths'][8]]['items']=[{'metadata':{'name':'p'+str(i),'namespace':'portal','uid':'u'+str(i)}} for i in range(201)]
  code,j=self.invoke();self.assertNotEqual(code,0,j['reads']['PR-6'])
 def test_after_sample_role_change_blocks_pass(self):
  raw=self.raw;n=[0]
  def role(*args):
   body,rc=raw(*args)
   if args[1]=='/api/v1/namespaces/portal/pods/portal-db-1':
    n[0]+=1
    if n[0]%2==0:
     d=json.loads(body);d['metadata']['labels']['cnpg.io/instanceRole']='replica';body=json.dumps(d).encode()
   return body,rc
  self.raw=role;code,j=self.invoke();self.assertNotEqual(code,0,j['reads']['HC-WAL-PROGRESS'])
 def test_baseline_identity_survives_cross_sample_change(self):
  raw=self.raw;n=[0]
  def replaced(*args):
   body,rc=raw(*args)
   if args[1]=='/api/v1/namespaces/portal/pods/portal-db-1':
    n[0]+=1;d=json.loads(body);d['metadata']['uid']='uid-window-'+str((n[0]-1)//2);body=json.dumps(d).encode()
   return body,rc
  self.raw=replaced;code,j=self.invoke();self.assertNotEqual(code,0,j['reads']['HC-WAL-PROGRESS'])
 def test_current_operation_number_without_action_receipt_is_not_authority(self):
  self.assertEqual(self.invoke()[0],0)
  self.g['operation_end_utc']=self.now[0]
  code,j=self.invoke('S1');self.assertNotEqual(code,0,j['aggregate'])
 def test_pr5_rejects_wrong_service_namespace(self):
  for stage in w.STAGE_ORDER[:-1]:
   if stage!='S0':self.op_gate(stage)
   self.assertEqual(self.invoke(stage)[0],0)
  self.op_gate('S4')
  self.docs[self.rs['PR-5']['path']]['items'][0]['metadata']['namespace']='other'
  code,j=self.invoke('S4');self.assertNotEqual(code,0,j['reads']['PR-5'])

class HTTP(unittest.TestCase):
 def test_eof_after_deadline_is_not_accepted(self):
  class Response:
   n=0
   def __enter__(self):return self
   def __exit__(self,*a):return False
   def read(self,n):
    self.n+=1
    if self.n==1:return b'body'
    time.sleep(.08);return b''
  class Opener:
   def open(self,*a,**kw):return Response()
  with patch('urllib.request.build_opener',return_value=Opener()):
   with self.assertRaises(w.ReadError):w.default_http_get('http://127.0.0.1:9187/metrics',.02,1024)

class Release(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  self.seed=q.parse_template(ROOT/'portal/tools/p8c-portal-seed.yml.template')
  self.release=q.parse_template(ROOT/'portal/tools/p8c-portal-release.yml.template')
 def test_scan_exact_image_digest_positive_control(self):
  d=rn.make_dir();self.addCleanup(shutil.rmtree,d)
  image='ghcr.io/dedvmedved-dot/otus-diplom-portal';ref=image+'@sha256:'+'a'*64
  (d/'scan-image.json').write_text(json.dumps({'ArtifactName':ref,'Metadata':{'RepoDigests':[ref]},'Results':[]}))
  p=rn.run_verified(d);self.assertEqual(p.returncode,0,p.stderr)
 def test_scan_same_image_wrong_digest_rejected(self):
  d=rn.make_dir();self.addCleanup(shutil.rmtree,d)
  ref='ghcr.io/dedvmedved-dot/otus-diplom-portal@sha256:'+'b'*64
  (d/'scan-image.json').write_text(json.dumps({'ArtifactName':ref,'Metadata':{'RepoDigests':[ref]},'Results':[]}))
  p=rn.run_verified(d);self.assertNotEqual(p.returncode,0,p.stdout)
 def test_release_gate_cannot_pass_without_gate_document(self):
  step=next(s for s in self.release['jobs']['release']['steps'] if s.get('name','').startswith('Future execution gate'))
  script=step['run'].replace('${{ github.sha }}','a'*40).replace('${{ github.repository }}','dedvmedved-dot/otus-diplom').replace('${{ github.run_attempt }}','1')
  p=subprocess.run(['bash','-c',script],cwd=self.root,env={'PATH':os.environ['PATH'],'GITHUB_RUN_ATTEMPT':'1'},capture_output=True,text=True)
  self.assertNotEqual(p.returncode,0,p.stdout)
 def test_first_creation_wrong_package_rejected(self):
  source='a'*40
  g={'source_sha':source,'issued_at_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'expiry_hours':24,'mode':'LIVE','repository':'other/repo','package':'ghcr.io/other/image','workflow_sha':'b'*40}
  gp=self.root/'gate.json';gp.write_text(json.dumps(g))
  p=subprocess.run([sys.executable,str(ROOT/'portal/tools/release-check.py'),'first-creation',str(gp)],env={**os.environ,'GITHUB_SHA':source,'GITHUB_REPOSITORY':'dedvmedved-dot/otus-diplom'},capture_output=True,text=True)
  self.assertNotEqual(p.returncode,0,p.stdout)
 def test_seed_record_positive_bootstrap_without_previous_app(self):
  step=next(s for s in self.seed['jobs']['seed']['steps'] if s.get('name','').startswith('Record seed digest'))
  shim=self.root/'python3';shim.write_text('#!/bin/sh\nif [ "$2" = private ]; then echo "{}"; exit 0; fi\nexec "'+sys.executable+'" "$@"\n');shim.chmod(0o700)
  env={**os.environ,'PATH':str(self.root)+':'+os.environ['PATH'],'RUNNER_TEMP':str(self.root),'SEED_DIGEST':'sha256:'+'a'*64};env.pop('APP_IMAGE_DIGEST',None)
  p=subprocess.run(['bash','-c',step['run']],cwd=ROOT,env=env,capture_output=True,text=True)
  self.assertEqual(p.returncode,0,p.stderr)

if __name__=='__main__':unittest.main(verbosity=2)
