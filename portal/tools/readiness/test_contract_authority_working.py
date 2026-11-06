"""Offline controls for R5, production main/window/predicates, virtual clock and fake transport.
Run at repository root with P8C_REVIEW_ROOT=$PWD python3 <this-file>. No network or cluster.
Reuses the published R4 fixture; it is SYNTHETIC, not new runtime evidence.
"""
import contextlib,copy,importlib.util,io,json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(os.environ.get('P8C_REVIEW_ROOT',Path.cwd())).resolve()
def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
old=load('r4_fixture',ROOT/'evidence/P8/20261105-974e069-architect-review/scheduler_regression_test.py')
w,wal=old.w,old.wal
SOURCE='783502a7eff2662d6f7612ccc56c4a9251e16ace'

class WindowRoutes(unittest.TestCase):
    def setUp(self):
        old.MainContract.setUp(self);self.g['source_sha']=SOURCE
        self.rs=json.loads(w.READSET.read_text())['reads'];self.idle=False;self.archived_before_baseline=False
        self.metrics_starts=[];self.health_calls=[]
        self.docs[self.rs['HC-PORTAL']['path']]={'apiVersion':'apps/v1','kind':'Deployment','metadata':{'name':'portal','namespace':'portal','generation':1},'spec':{'replicas':1},'status':{'observedGeneration':1,'readyReplicas':1,'availableReplicas':1,'updatedReplicas':1}}
        self.docs[self.rs['HC-GW']['path']]={'apiVersion':'gateway.networking.k8s.io/v1','kind':'Gateway','metadata':{'name':'portal-gateway','namespace':'portal','generation':1},'status':{'conditions':[{'type':x,'status':'True','observedGeneration':1} for x in ['Accepted','Programmed']]}}
        self.docs[self.rs['PR-5']['path']]=old.listing('ServiceList','v1',[{'metadata':{'name':'envoy','namespace':'envoy-gateway-system','uid':'envoy-service','labels':{'gateway.envoyproxy.io/owning-gateway-name':'portal-gateway','gateway.envoyproxy.io/owning-gateway-namespace':'portal'}},'spec':{'type':'LoadBalancer','externalTrafficPolicy':'Local','ports':[{'port':443,'targetPort':10443,'protocol':'TCP'}]},'status':{'loadBalancer':{'ingress':[{'ip':'172.30.140.110'}]}}}])
    def raw(self,*args):
        self.health_calls.append((args[1],self.mono[0]));return old.MainContract.raw(self,*args)
    def http(self,url,timeout,cap):
        self.metrics_starts.append(self.mono[0]);self.sample_count+=1
        count=1 if self.idle else self.sample_count
        when=old.NOW-20 if self.idle else self.now[0]-1
        if self.archived_before_baseline:when=old.NOW-100+self.sample_count
        b=old.text_metrics(old.metrics(count,when));self.calls.append(('http',url));self.nbytes+=len(b);return b
    def invoke(self,stage='S0',state=None):
        state=state or self.state;state.mkdir(exist_ok=True);self.seq+=1
        gp=self.root/'gate.json';gp.write_text(json.dumps(self.g));out=self.root/f'out{self.seq}.json'
        def sleep(n):self.now[0]+=n;self.mono[0]+=n
        with contextlib.ExitStack() as s:
            s.enter_context(patch.object(w,'RESERVATION_BASE',str(self.root/'authority')))
            s.enter_context(patch.object(w.time,'time',side_effect=lambda:self.now[0]))
            s.enter_context(patch.object(w.time,'monotonic',side_effect=lambda:self.mono[0]))
            s.enter_context(patch.object(w.time,'sleep',side_effect=sleep))
            s.enter_context(patch.object(w,'run_kubectl_raw',side_effect=self.raw))
            s.enter_context(patch.object(w,'default_http_get',side_effect=self.http))
            s.enter_context(contextlib.redirect_stdout(io.StringIO()));s.enter_context(contextlib.redirect_stderr(io.StringIO()))
            code=w.main(['--gate',str(gp),'--out',str(out),'--state-dir',str(state),'--stage',stage,'--kubectl','FAKE'])
        return code,json.loads(out.read_text()) if out.exists() else None
    def test_positive_s0_through_s4_mock_transport_control(self):
        for stage in w.STAGE_ORDER:
            if stage!='S0':
                self.g['operation_end_utc']=self.now[0]
                self.g['action_receipt']={'source_sha':self.g['source_sha'],'package_sha256':self.g['package_sha256'],'operation_end_utc':self.now[0]}
            code,j=self.invoke(stage);self.assertEqual((code,j['aggregate']),(0,w.PASS),stage)
        self.assertEqual(json.loads((self.state/'stage.receipt').read_text())['stage'],'S4')
    def test_clean_failed_window_cannot_restart_three_more_samples(self):
        self.idle=True;self.assertNotEqual(self.invoke()[0],0);self.assertEqual(self.sample_count,3)
        self.calls=[];self.assertNotEqual(self.invoke()[0],0)
        self.assertEqual(self.calls,[],'Three exhausted slots must not authorize another whole window')
    def test_new_state_directory_after_nonpass_cannot_start_fresh_window(self):
        self.idle=True;self.invoke();self.calls=[]
        self.invoke(state=self.root/'other-state');self.assertEqual(self.calls,[])
    def test_s0_progress_must_be_after_first_sample_end(self):
        self.archived_before_baseline=True
        code,j=self.invoke();self.assertNotEqual(code,0,j)
    def test_post_operation_stage_requires_its_action_boundary(self):
        self.assertEqual(self.invoke()[0],0);code,j=self.invoke('S1')
        self.assertNotEqual(code,0,j)
    def test_shared_db_arch_metadata_not_read_twice_at_same_tick(self):
        self.invoke();path=self.rs['HC-DB']['path'];ts=[t for p,t in self.health_calls if p==path]
        self.assertLessEqual(ts.count(0.0),3,'one shared HC GET plus two WAL bracket GETs')
    def test_success_receipt_requires_fresh_operator_observation(self):
        code,j=self.invoke();self.assertEqual(code,0,j)
        latest=max(t for p,t in self.health_calls if p==self.rs['HC-OP']['path'])
        self.assertLessEqual(self.mono[0]-latest,30,'HC-OP observation is stale at PASS')
    def test_failed_request_attempts_are_charged(self):
        def failing(*a):self.calls.append(('failed',a[1]));raise w.ReadError('synthetic timeout')
        self.raw=failing
        _,j=self.invoke();self.assertEqual(j['budget']['requests'],len(self.calls));self.assertGreater(len(self.calls),0)
    def test_negative_budget_not_accepted(self):
        (self.state/'budget.json').write_text(json.dumps({'requests':-1000,'bytes':-1000,'seconds':-1000}))
        code,j=self.invoke();self.assertNotEqual(code,0,j);self.assertEqual(self.calls,[])
    def test_first_slot_failure_metrics_do_not_replace_valid_baseline(self):
        valid=old.metrics(0,old.NOW-30);w.persist_wal_baseline(self.state,self.g,valid)
        self.g.update(wal_baseline=valid,operation_end_utc=old.NOW-20)
        def failed_metrics(url,timeout,cap):
            m=old.metrics(1,old.NOW-1);m['cnpg_pg_stat_archiver_failed_count']=1
            b=old.text_metrics(m);self.calls.append(('http',url));return b
        self.http=failed_metrics;code,j=self.invoke();self.assertEqual(j['aggregate'],w.FAIL)
        self.assertEqual(w.read_wal_baseline(self.state,self.g),valid)

class SourceBoundaries(unittest.TestCase):
    def test_slot_offsets_include_elapsed_sample_time(self):
        with tempfile.TemporaryDirectory() as tmp:
            clock=[0.0];starts=[]
            def sample(*args):starts.append(clock[0]);clock[0]+=10;return w.INCONCLUSIVE,'idle',None
            with patch.object(w,'run_wal_sample',side_effect=sample),patch.object(w.time,'monotonic',side_effect=lambda:clock[0]),patch.object(w.time,'sleep',side_effect=lambda n:clock.__setitem__(0,clock[0]+n)):
                w.run_wal_window('FAKE',None,{},tmp,None)
            self.assertEqual(starts,[0,300,600])
    def test_pr6_missing_expected_nftables_mode_rejected(self):
        ds=old.fixtures();paths=json.loads(w.READSET.read_text())['reads']['PR-6']['paths'];docs=[ds[p] for p in paths]
        docs[6]['items'][0]['spec']={}
        self.assertNotEqual(w.pred_pr6(docs)[0],w.PASS)
    def test_pr3_wrong_resource_kind_rejected_on_actual_read_path(self):
        rs=json.loads(w.READSET.read_text());d=old.fixtures()[rs['reads']['PR-3']['path']];d['kind']='PodList';d['apiVersion']='v1'
        verdict=None
        with patch.object(w,'run_kubectl_raw',return_value=(json.dumps(d).encode(),0)):
            try:verdict=w.pred_pr3(w.run_read(rs,'PR-3','FAKE'))[0]
            except w.ReadError:pass
        self.assertNotEqual(verdict,w.PASS)
    def test_pr5_requires_service_identity(self):
        d={'items':[{'spec':{'type':'LoadBalancer','externalTrafficPolicy':'Local','ports':[{'port':443,'targetPort':10443,'protocol':'TCP'}]},'status':{'loadBalancer':{'ingress':[{}]}}}]}
        self.assertNotEqual(w.pred_pr5(d)[0],w.PASS)
    def test_first_creation_does_not_accept_expired_future_test_only_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'gate.json'
            for case,issued,mode in [('expired','2000-01-01T00:00:00Z','LIVE'),('future','2099-01-01T00:00:00Z','LIVE'),('test-only','2026-11-05T06:00:00Z','TEST_ONLY')]:
                with self.subTest(case=case):
                    p.write_text(json.dumps({'source_sha':SOURCE,'issued_at_utc':issued,'expiry_hours':24,'mode':mode}))
                    r=subprocess.run([sys.executable,str(ROOT/'portal/tools/release-check.py'),'first-creation',str(p)],capture_output=True,text=True)
                    self.assertNotEqual(r.returncode,0,r.stdout)

if __name__=='__main__':unittest.main(verbosity=2)
