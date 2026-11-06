"""R4 offline contract controls. All responses synthetic; no cluster/HTTP/CI access.
Run from repository root with P8C_REVIEW_ROOT=$PWD python3 <this-file>.
Production main, predicates and wal_sample execute; only transports/time are injected.
"""
import contextlib,copy,io,json,os,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(os.environ.get('P8C_REVIEW_ROOT',Path.cwd())).resolve()
sys.path.insert(0,str(ROOT/'portal/tools/readiness'))
import wrapper as w
import wal
NOW=w.parse_utc('2026-11-05T06:00:00Z')
SOURCE='317ebc7ab1839f7dac5a22690b24aabafcc98283'
def metrics(count=1,when=NOW-20):
    return dict(zip(wal.ARCHIVER_SERIES,[count,0,when,0,1]))
def text_metrics(m):return ''.join(f'{k} {v}\n' for k,v in m.items()).encode()
def listing(kind,api,items):return dict(kind=kind,apiVersion=api,metadata={'resourceVersion':'1'},items=items)
def fixtures():
    c=dict(kind='Cluster',apiVersion='postgresql.cnpg.io/v1',metadata={'name':'portal-db','namespace':'portal','uid':'cluster'},spec={'instances':3},status={'instances':3,'readyInstances':3,'currentPrimary':'portal-db-1','conditions':[{'type':'Ready','status':'True'},{'type':'ContinuousArchiving','status':'True'}]})
    p=dict(kind='Pod',apiVersion='v1',metadata={'name':'portal-db-1','namespace':'portal','uid':'primary','ownerReferences':[{'uid':'cluster','kind':'Cluster','name':'portal-db'}],'labels':{'cnpg.io/cluster':'portal-db','cnpg.io/instanceRole':'primary'}},spec={'nodeName':'node-01'},status={'podIP':'10.244.1.1','containerStatuses':[{'name':'postgres','restartCount':0}]})
    rs=json.loads(w.READSET.read_text())['reads']; d={}
    d[rs['HC-DB']['path']]=c
    d['/api/v1/namespaces/portal/pods/portal-db-1']=p
    def eps(addrs,ports,ns,name):return listing('EndpointSliceList','discovery.k8s.io/v1',[{'metadata':{'namespace':ns,'labels':{'kubernetes.io/service-name':name}},'ports':ports,'endpoints':[{'addresses':addrs,'conditions':{'ready':True}}]}])
    d[rs['PR-3']['path']]=eps(['172.30.140.101','172.30.140.102','172.30.140.103'],[{'port':6443,'protocol':'TCP'}],'default','kubernetes')
    d[rs['HC-DNS']['path']]=eps(['10.244.254.65'],[{'port':53,'protocol':v} for v in ['TCP','UDP']],'kube-system','kube-dns')
    d[rs['HC-OP']['path']]=listing('PodList','v1',[{'metadata':{'name':'operator','namespace':'cnpg-system'},'status':{'conditions':[{'type':'Ready','status':'True'}]}}])
    kinds=['NetworkPolicyList','NetworkPolicyList','GlobalNetworkPolicyList','HostEndpointList','ClusterNetworkPolicyList','TierList','FelixConfigurationList','NamespaceList','PodList']
    apis=['networking.k8s.io/v1']+['crd.projectcalico.org/v1']*3+['policy.networking.k8s.io/v1alpha2']+['crd.projectcalico.org/v1']*2+['v1']*2
    for path,k,a in zip(rs['PR-6']['paths'],kinds,apis):d[path]=listing(k,a,[])
    d[rs['PR-6']['paths'][5]]['items']=[{'metadata':{'name':n},'spec':{'order':o,'defaultAction':a}} for n,o,a in [('default',1000000,'Deny'),('kube-admin',1000,'Pass'),('kube-baseline',10000000,'Pass')]]
    d[rs['PR-6']['paths'][6]]['items']=[{'metadata':{'name':'default'},'spec':{'nftablesMode':'Auto'}}]
    return d

class MainContract(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.state=self.root/'state';self.state.mkdir();self.now=[float(NOW)];self.mono=[0.0]
        self.docs=fixtures();self.calls=[];self.nbytes=0;self.sample_count=0
        self.g=dict(mode='LIVE',context=w.CONTEXT,source_sha=SOURCE,package_sha256=w.package_hash(),issued_at_utc='2026-11-05T06:00:00Z',expiry_hours=24)
        self.g['clock_evidence']=dict(bound=1,source='SYNTHETIC',provenance_sha256='a'*64,node='node-01',backend='exporter',observed_utc='2026-11-05T06:00:00Z',validity_hours=24,gate_sha256=self.g['package_sha256'])
        self.g['clock_evidence']['gate_sha256']=w.gate_identity_sha256(self.g)
        self.seq=0
    def raw(self,kubectl,path,timeout,cap):
        b=json.dumps(self.docs[path]).encode();self.calls.append(('kubectl',path));self.nbytes+=len(b);return b,0
    def http(self,url,timeout,cap):
        self.sample_count+=1;b=text_metrics(metrics(self.sample_count,self.now[0]-1));self.calls.append(('http',url));self.nbytes+=len(b);return b
    def invoke(self,state=None):
        state=state or self.state;state.mkdir(exist_ok=True);self.seq+=1
        gp=self.root/'gate.json';gp.write_text(json.dumps(self.g));out=self.root/f'out{self.seq}.json'
        def sleep(seconds):self.now[0]+=seconds;self.mono[0]+=seconds
        with contextlib.ExitStack() as s:
            s.enter_context(patch.object(w,'RESERVATION_BASE',str(self.root/'authority')))
            s.enter_context(patch.object(w.time,'time',side_effect=lambda:self.now[0]))
            s.enter_context(patch.object(w.time,'monotonic',side_effect=lambda:self.mono[0]))
            s.enter_context(patch.object(w.time,'sleep',side_effect=sleep))
            s.enter_context(patch.object(w,'run_kubectl_raw',side_effect=self.raw))
            s.enter_context(patch.object(w,'default_http_get',side_effect=self.http))
            s.enter_context(contextlib.redirect_stdout(io.StringIO()));s.enter_context(contextlib.redirect_stderr(io.StringIO()))
            code=w.main(['--gate',str(gp),'--out',str(out),'--state-dir',str(state),'--stage','S0','--kubectl','FAKE'])
        return code,json.loads(out.read_text()) if out.exists() else None
    def test_positive_prebound_sample_control(self):
        self.g.update(wal_baseline=metrics(0,NOW-30),operation_end_utc=NOW-20)
        code,j=self.invoke();self.assertEqual((code,j['aggregate']),(0,w.PASS))
    def test_s0_collects_own_baseline_then_progress_in_one_window(self):
        code,j=self.invoke()
        self.assertEqual(code,0,j)
        self.assertGreaterEqual(self.sample_count,2)
        self.assertGreaterEqual(self.mono[0],300)
    def test_first_valid_baseline_is_preserved_without_claiming_progress(self):
        code,j=self.invoke();p=self.state/'wal-baseline.json'
        self.assertTrue(p.exists(),'Valid first sample is INCONCLUSIVE, but baseline must survive for slot 2')
    def test_budget_counts_requests_and_bytes_not_logical_checks(self):
        _,j=self.invoke()
        self.assertEqual(j['budget']['requests'],len(self.calls))
        self.assertEqual(j['budget']['bytes'],self.nbytes)
    def test_exhausted_budget_blocks_before_any_request(self):
        (self.state/'budget.json').write_text(json.dumps({'requests':233,'bytes':179*1024*1024,'seconds':5265}))
        code,_=self.invoke();self.assertNotEqual(code,0);self.assertEqual(self.calls,[])
    def test_corrupt_budget_cannot_reset_to_zero(self):
        (self.state/'budget.json').write_text('{')
        code,_=self.invoke();self.assertNotEqual(code,0);self.assertEqual(self.calls,[])
    def test_same_clock_new_invocation_is_not_second_slot(self):
        self.invoke();self.calls=[]
        code,_=self.invoke();self.assertNotEqual(code,0);self.assertEqual(self.calls,[])
    def test_crash_inflight_marker_does_not_authorize_second_process(self):
        with patch.object(w,'RESERVATION_BASE',str(self.root/'authority')):self.assertEqual(w.open_window(self.g,'S0')[0],'first')
        code,_=self.invoke();self.assertNotEqual(code,0);self.assertEqual(self.calls,[])
    def test_new_state_directory_does_not_reset_budget(self):
        self.invoke();self.calls=[]
        code,_=self.invoke(self.root/'other-state');self.assertNotEqual(code,0);self.assertEqual(self.calls,[])
    def test_last_response_cannot_cross_sample_deadline_and_pass(self):
        self.g.update(wal_baseline=metrics(0,NOW-30),operation_end_utc=NOW-20)
        calls=[0]
        def slow_raw(*args):
            calls[0]+=1;r=self.raw(*args)
            if calls[0]==3:self.mono[0]=29
            if calls[0]==4:self.mono[0]=31
            return r
        with patch.object(w,'run_kubectl_raw',side_effect=slow_raw),patch.object(w.time,'monotonic',side_effect=lambda:self.mono[0]),patch.object(w.time,'time',side_effect=lambda:self.now[0]):
            result=w.run_wal_sample('FAKE',self.http,self.g['clock_evidence'],self.g)
        self.assertNotEqual(result[0],w.PASS,result)

class ExistingReadContract(unittest.TestCase):
    def test_gateway_missing_generation_not_none_equals_none(self):
        d={'status':{'conditions':[{'type':x,'status':'True'} for x in ['Accepted','Programmed']]}}
        self.assertNotEqual(w.pred_hc_gw(d)[0],w.PASS)
    def test_pr3_port_belongs_to_same_slice_as_addresses(self):
        d={'items':[{'ports':[{'port':6443,'protocol':'TCP'}],'endpoints':[]},{'ports':[],'endpoints':[{'addresses':['172.30.140.101','172.30.140.102','172.30.140.103'],'conditions':{'ready':True}}]}]}
        self.assertNotEqual(w.pred_pr3(d)[0],w.PASS)
    def test_dns_ports_on_empty_slice_not_proof_for_ready_endpoint(self):
        d={'items':[{'ports':[{'port':53,'protocol':p} for p in ['TCP','UDP']],'endpoints':[]},{'ports':[],'endpoints':[{'addresses':['10.244.254.65'],'conditions':{'ready':True}}]}]}
        self.assertNotEqual(w.pred_hc_dns(d)[0],w.PASS)
    def test_pr6_changed_bpf_field_not_silently_ignored(self):
        rs=json.loads(w.READSET.read_text());docs=fixtures();ds=[docs[p] for p in rs['reads']['PR-6']['paths']]
        ds[6]['items'][0]['spec']['bpfEnabled']=True
        self.assertNotEqual(w.pred_pr6(ds)[0],w.PASS)

if __name__=='__main__':unittest.main(verbosity=2)
