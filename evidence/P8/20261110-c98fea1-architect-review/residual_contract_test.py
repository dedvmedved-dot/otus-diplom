"""Residual controls for existing e60d1db review. Synthetic offline transports only.
P8C_REVIEW_ROOT=$PWD python3 <this-file> -v
"""
import contextlib,importlib.util,io,json,os,pathlib,subprocess,sys,tempfile,time,unittest
from unittest.mock import patch
ROOT=pathlib.Path(os.environ.get('P8C_REVIEW_ROOT',pathlib.Path.cwd())).resolve()
sys.path.insert(0,str(ROOT/'portal/tools/readiness'))
import wrapper as w
import test_contract_authority_working as f
SOURCE='61e4a44e34cd680bafefc29851f382e2eb2102dd';REPO='dedvmedved-dot/otus-diplom';IMAGE='ghcr.io/'+REPO+'-portal'

def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

class RouteControls(unittest.TestCase):
 setUp=f.WindowRoutes.setUp
 raw=f.WindowRoutes.raw
 http=f.WindowRoutes.http
 invoke=f.WindowRoutes.invoke
 def test_positive_s0_control(self):
  code,j=self.invoke();self.assertEqual((code,j['aggregate']),(0,w.PASS))
 def test_fifth_operator_observation_within_accepted_window(self):
  original=self.raw;seen=[];path=self.rs['HC-OP']['path']
  def raw(*args):
   if args[1]==path:
    seen.append(self.mono[0])
    if len(seen)<5:return json.dumps(f.old.listing('PodList','v1',[])).encode(),0
   return original(*args)
  self.raw=raw;code,j=self.invoke();self.assertEqual(code,0,{'observations':seen,'verdict':j['reads']['HC-OP']})
 def test_actual_transport_elapsed_persists_in_overall_budget(self):
  raw0=self.raw;http0=self.http
  def advance():self.now[0]+=1;self.mono[0]+=1
  def raw(*a):advance();return raw0(*a)
  def http(*a):advance();return http0(*a)
  self.raw=raw;self.http=http;code,j=self.invoke();self.assertEqual(code,0,j['aggregate'])
  self.assertGreaterEqual(j['budget']['seconds'],self.mono[0],{'budget':j['budget']['seconds'],'elapsed':self.mono[0]})
 def action(self,stage):
  self.g['operation_end_utc']=self.now[0]
  self.g['action_receipt']={'source_sha':self.g['source_sha'],'package_sha256':self.g['package_sha256'],'gate_sha256':w.gate_identity_sha256(self.g),'stage':w.STAGES[w.STAGES.index(stage)-1],'outcome':w.PASS,'operation_end_utc':self.now[0]}
 def test_gateway_observations_stay_within_accepted_n12(self):
  for st in w.STAGE_ORDER[:-1]:
   if st!='S0':self.action(st)
   self.assertEqual(self.invoke(st)[0],0,st)
  original=self.raw;seen=[];path=self.rs['HC-GW']['path']
  def raw(*args):
   if args[1]==path:
    seen.append(self.mono[0]);doc=json.loads(json.dumps(self.docs[path]));doc['status']['conditions']=[];return json.dumps(doc).encode(),0
   return original(*args)
  self.raw=raw;self.action('S4');code,j=self.invoke('S4');self.assertNotEqual(code,0)
  self.assertLessEqual(len(seen),12,seen)
 def test_wal_remaining_byte_limits_first_metadata_read(self):
  with patch.object(w,'RESERVATION_BASE',str(self.root/'wal-authority')):
   b={'wal_bytes':w.WAL_BODY_CAP-1};w.write_budget(self.g,b);w._set_budget_base(b);w._set_budget_context(self.g,None,b);w._reset_transport();caps=[]
   original=self.raw
   def raw(*args):caps.append(args[3]);return original(*args)
   try:
    with patch.object(w,'run_kubectl_raw',side_effect=raw):w.run_wal_sample('FAKE',self.http,self.g['clock_evidence'],self.g)
    self.assertTrue(caps);self.assertLessEqual(caps[0],1,caps)
   finally:w._set_budget_context(None,None,None);w._set_budget_base({});w._reset_transport()

class TransportDurability(unittest.TestCase):
 def test_consumed_bytes_are_not_lost_on_remaining_cap_error(self):
  with tempfile.TemporaryDirectory() as t,patch.object(w,'RESERVATION_BASE',t+'/authority'):
   g={'package_sha256':'a'*64};b={'bytes':w.OVERALL_BODY_CAP-2};w.write_budget(g,b);w._set_budget_base(b);w._set_budget_context(g,None,b);w._reset_transport()
   fake=pathlib.Path(t)/'fake-kubectl';fake.write_text('#!'+sys.executable+'\nimport os\nos.write(1,b"{}X")\n');fake.chmod(0o700)
   try:
    with self.assertRaises(w.ReadError):w.run_kubectl_raw(str(fake),'/api/v1/pods',2,2)
    stored=json.loads(pathlib.Path(w.budget_path(g)).read_text())['bytes']
    self.assertGreaterEqual(stored,b['bytes']+2,{'stored':stored,'initial':b['bytes'],'consumed_at_least':2})
   finally:w._set_budget_context(None,None,None);w._set_budget_base({});w._reset_transport()
 def test_wal_seconds_cap_overrun_is_not_silently_dropped(self):
  with tempfile.TemporaryDirectory() as t,patch.object(w,'RESERVATION_BASE',t+'/authority'):
   g={'package_sha256':'b'*64};b={'wal_seconds':w.WAL_SEC_CAP-1};w.write_budget(g,b);w._set_budget_context(g,None,b);w._reset_transport()
   try:
    raised=False
    try:w._count_wal_seconds(2)
    except w.ReadError:raised=True
    stored=json.loads(pathlib.Path(w.budget_path(g)).read_text())['wal_seconds']
    self.assertTrue(raised or stored>=w.WAL_SEC_CAP,{'raised':raised,'authority':stored,'runtime':w._WAL_TRANSPORT['seconds']})
   finally:w._set_budget_context(None,None,None);w._reset_transport()

class ReleaseGateControls(unittest.TestCase):
 def gate(self):return {'source_sha':SOURCE,'repository':REPO,'package':IMAGE,'workflow_sha':SOURCE,'mode':'LIVE','issued_at_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'expiry_hours':1,'attempt':1}
 def run_gate(self,g,attempt='1'):
  with tempfile.TemporaryDirectory() as t:
   p=pathlib.Path(t)/'gate.json';p.write_text(json.dumps(g))
   return subprocess.run([sys.executable,str(ROOT/'portal/tools/release-check.py'),'release-gate',str(p),SOURCE,REPO,attempt],capture_output=True,text=True,env=dict(os.environ,GITHUB_SHA=SOURCE,GITHUB_REPOSITORY=REPO,GITHUB_WORKFLOW_SHA=SOURCE),timeout=10)
 def test_bound_gate_positive_control(self):
  p=self.run_gate(self.gate());self.assertEqual(p.returncode,0,p.stderr)
 def test_actual_attempt_two_rejected_with_gate_attempt_one(self):
  p=self.run_gate(self.gate(),'2');self.assertNotEqual(p.returncode,0,p.stdout)
 def test_different_runtime_workflow_sha_rejected(self):
  g=self.gate();g['workflow_sha']='b'*40;p=self.run_gate(g);self.assertNotEqual(p.returncode,0,p.stdout)
 def test_future_gate_is_not_active_yet(self):
  g=self.gate();g['issued_at_utc']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime(time.time()+120));p=self.run_gate(g);self.assertNotEqual(p.returncode,0,p.stdout)
 def test_offline_image_evidence_requires_observed_digest_binding(self):
  m=load('pins_residual',ROOT/'portal/tools/verify-pins.py')
  with tempfile.TemporaryDirectory() as t:
   p=pathlib.Path(t)/'lock.json';digest='sha256:'+'a'*64
   p.write_text(json.dumps({'binaries':[],'actions':[],'images':[{'id':'postgres','digest':digest,'ref':'postgres:synthetic'}]}))
   (pathlib.Path(t)/'pin-verification.json').write_text(json.dumps({'results':[{'id':'postgres','status':'VERIFIED','declared':digest,'manifest_sha256':'sha256:'+'b'*64,'ref':'postgres:synthetic'}]}))
   with patch.object(m,'LOCK',str(p)),patch.object(m,'CACHE',t),contextlib.redirect_stdout(io.StringIO()):code=m.verify_offline()
   self.assertNotEqual(code,0)

if __name__=='__main__':unittest.main(verbosity=2)
