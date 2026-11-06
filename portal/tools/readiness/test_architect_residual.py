"""Active working copy of the Architect residual contract (evidence/P8/.../residual_test.py).

ORIGINAL: evidence/P8/20261105-64e36a6-architect-review/residual_test.py (frozen, not edited).

CHANGE FROM ORIGINAL (test-harness isolation only, assertions unchanged):
  - The original StateAndExecution.invoke did NOT patch RESERVATION_BASE, so all three
    StateAndExecution tests shared one window-authority keyed by the fixed gate. Under the
    corrected "failed/completed -> no replay" window semantics, test_failed_stage_cannot_authorize_next
    (S0 -> failed) then polluted test_replay_new_parent_directory_rejected (S0 -> blocked at rc=2
    instead of a fresh success). This is a cross-test artifact, not a production defect.
  - Fix: each StateAndExecution test now gets a private temporary authority directory
    (RESERVATION_BASE) so a failed/completed window in one test cannot leak into another.
    Explicit shared state remains ONLY inside the replay scenario (same test, same authority).
  - Production protections (failed/completed/UNKNOWN_OUTCOME = no new budget; state-dir change
    cannot bypass authority) are preserved verbatim; no assertion is weakened, skipped or xfail'ed.
"""
import copy,importlib.util,io,json,os,subprocess,sys,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(os.environ.get('P8C_REVIEW_ROOT',str(Path.cwd()))).resolve()
TOOLS=ROOT/'portal/tools'
sys.path[:0]=[str(TOOLS),str(TOOLS/'readiness')]
import wrapper as w
import wal
import release_qualification as q

def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
old=load('old_review',ROOT/'evidence/P8/20261105-f783e1e-architect-review/regression_test.py')
rc=load('rc',TOOLS/'release-check.py')
neg=load('neg',TOOLS/'test_release_negative.py')
pins=load('pins',TOOLS/'verify-pins.py')
NOW=1793836800 # 2026-11-05T00:00:00Z, synthetic test clock

def gate():
    return dict(mode='LIVE',context=w.CONTEXT,source_sha='235b41295521096e308d545045f1eec3d256bec3',package_sha256=w.package_hash(),issued_at_utc='2026-11-05T00:00:00Z',expiry_hours=24)

def listing(kind='PodList',api='v1',cont_marker='ABSENT'):
    d=dict(kind=kind,apiVersion=api,metadata={'resourceVersion':'1'},items=[])
    if cont_marker!='ABSENT':d['metadata']['continue']=cont_marker
    return d

def pr6_listing(kind):
    return dict(kind=kind, apiVersion='v1', metadata={'resourceVersion': '1'}, items=[])

PR6_KINDS = ["NetworkPolicyList", "NetworkPolicyList", "GlobalNetworkPolicyList",
             "HostEndpointList", "ClusterNetworkPolicyList", "TierList",
             "FelixConfigurationList", "NamespaceList", "PodList"]


class ListsAndBaseline(unittest.TestCase):
    def test_complete_list_absent_continue_positive(self):
        self.assertEqual(w.validate_envelope(json.dumps(listing()),True)['items'],[])

    def test_complete_list_empty_continue_positive(self):
        self.assertEqual(w.validate_envelope(json.dumps(listing(cont_marker='')),True)['items'],[])

    def test_explicit_null_continue_negative(self):
        with self.assertRaises(w.ReadError):w.validate_envelope(json.dumps(listing(cont_marker=None)),True)

    def test_pinned_cnp_api_positive(self):
        self.assertEqual(w.validate_envelope(json.dumps(listing('ClusterNetworkPolicyList','policy.networking.k8s.io/v1alpha2')),True)['items'],[])

    def test_unrecognized_api_suffix_negative(self):
        with self.assertRaises(w.ReadError):w.validate_envelope(json.dumps(listing(api='v1-unapproved')),True)

    def test_archived_nonempty_tier_felix_baseline_is_not_drift(self):
        a=json.loads((ROOT/'evidence/P8/20261105-64e36a6-architect-review/accepted-baseline.json').read_text())
        records={r['id']:json.loads(r['output']) for r in a['records']}
        ds=[pr6_listing(k) for k in PR6_KINDS]
        ds[5]['items']=records['F-TIER'];ds[6]['items']=[records['F-FELIX']]
        self.assertEqual(w.pred_pr6(ds)[0],w.PASS)

    def test_missing_expected_tiers_felix_not_pass(self):
        self.assertNotEqual(w.pred_pr6([pr6_listing(k) for k in PR6_KINDS])[0],w.PASS)

    def test_api_tuple_requires_port(self):
        d={'items':[{'endpoints':[{'addresses':['172.30.140.101','172.30.140.102','172.30.140.103'],'conditions':{'ready':True}}]}]}
        self.assertNotEqual(w.pred_pr3(d)[0],w.PASS)

    def test_portal_required_generation_not_none_equals_none(self):
        d={'spec':{'replicas':1},'status':{'readyReplicas':1,'availableReplicas':1,'updatedReplicas':1}}
        self.assertNotEqual(w.pred_hc_portal(d)[0],w.PASS)

class StateAndExecution(unittest.TestCase):
    def setUp(self):
        # ISOLATION FIX (see module docstring): per-test private authority directory.
        self._authority_tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self._authority_tmp.cleanup)
        self.authority=str(Path(self._authority_tmp.name)/'authority')

    def invoke(self,root,stage,reads_fail=False):
        root.mkdir(parents=True,exist_ok=True);gp=root/'gate.json';gp.write_text(json.dumps(gate()))
        def transport(rs,rid,*args):
            if reads_fail:raise w.ReadError('synthetic transport failure')
            return {}
        predicates={k:(v[0],lambda d:(w.PASS,'synthetic healthy')) for k,v in w.PREDICATES.items()}
        with patch.object(w,'RESERVATION_BASE',self.authority),patch.object(w.time,'time',return_value=NOW+10),patch.object(w,'run_read',side_effect=transport) as tr,patch.object(w,'PREDICATES',predicates),patch.object(w,'run_wal_sample',return_value=(w.PASS,'synthetic progress')),patch('sys.stdout',new=io.StringIO()),patch('sys.stderr',new=io.StringIO()):
            code=w.main(['--gate',str(gp),'--state-dir',str(root/'state'),'--out',str(root/(stage+'.json')),'--stage',stage])
        return code,tr.call_count

    def test_failed_stage_cannot_authorize_next(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);first,_=self.invoke(root,'S0',True);self.assertNotEqual(first,0)
            second,calls=self.invoke(root,'S1');self.assertNotEqual(second,0);self.assertEqual(calls,0)

    def test_replay_new_parent_directory_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);self.assertEqual(self.invoke(root/'a','S0')[0],0)
            code,calls=self.invoke(root/'b','S0');self.assertNotEqual(code,0);self.assertEqual(calls,0)

    def test_unbound_plain_text_receipt_not_authority(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'state').mkdir();(root/'state/stage.receipt').write_text('S3')
            code,calls=self.invoke(root,'S4');self.assertNotEqual(code,0);self.assertEqual(calls,0)

    def test_child_stdout_eof_is_not_child_failure(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'fake-kubectl'
            f.write_text('#!'+sys.executable+'\nimport os,time\nos.write(1,b"{}")\nos.close(1)\ntime.sleep(.1)\n')
            f.chmod(0o700)
            body,status=w.run_kubectl_raw(str(f),'/api/v1/pods',1,1024)
            self.assertEqual((body,status),(b'{}',0))

class WALRoutes(unittest.TestCase):
    def prepared(self):
        c,p=old.docs();e=old.clock();e['observed_utc']='2026-11-05T00:00:00Z'
        c.update(apiVersion='postgresql.cnpg.io/v1',kind='Cluster');c['metadata']['namespace']='portal'
        p.update(apiVersion='v1',kind='Pod')
        return c,p,e

    def test_positive_fresh_progress_control(self):
        c,p,e=self.prepared()
        self.assertEqual(wal.wal_sample(c,p,old.metric_text(old.metrics(2,NOW+8)),c,p,e,old.metrics(1,NOW-30),NOW-10,now=NOW+10)[0],w.PASS)

    def test_future_clock_not_accepted(self):
        _,_,e=self.prepared();e['observed_utc']='2099-01-01T00:00:00Z'
        self.assertFalse(wal.validate_clock(e,now=NOW)[0])

    def test_absent_owner_not_identity_proof(self):
        c,p,e=self.prepared();p['metadata'].pop('ownerReferences')
        self.assertNotEqual(wal.wal_sample(c,p,old.metric_text(old.metrics(2,NOW+8)),c,p,e,old.metrics(1,NOW-30),NOW-10,now=NOW+10)[0],w.PASS)

    def test_main_sample_deadline_enforced(self):
        c,p,e=self.prepared();responses=[c,p,p,c];elapsed=[0]
        def raw(*args):return json.dumps(responses.pop(0)).encode(),0
        def http(*args):elapsed[0]+=31;return old.metric_text(old.metrics(2,NOW+8)).encode()
        g=gate();g.update(wal_baseline=old.metrics(1,NOW-30),operation_end_utc=NOW-10)
        with patch.object(w,'run_kubectl_raw',side_effect=raw),patch.object(w.time,'time',side_effect=lambda:NOW+elapsed[0]),patch.object(w.time,'monotonic',side_effect=lambda:elapsed[0]):
            self.assertNotEqual(w.run_wal_sample('FAKE',http,e,g)[0],w.PASS)

    def test_clock_gate_binding_checked_on_actual_sample_route(self):
        c,p,e=self.prepared();e['gate_sha256']='wrong';responses=[c,p,p,c]
        g=gate();g.update(wal_baseline=old.metrics(1,NOW-30),operation_end_utc=NOW-10)
        def raw(*args):return json.dumps(responses.pop(0)).encode(),0
        with patch.object(w,'run_kubectl_raw',side_effect=raw),patch.object(w.time,'time',return_value=NOW+10):
            self.assertNotEqual(w.run_wal_sample('FAKE',lambda *a:old.metric_text(old.metrics(2,NOW+8)).encode(),e,g)[0],w.PASS)

class SeedAndRelease(unittest.TestCase):
    def test_first_creation_mode_exists(self):
        with patch.object(sys,'argv',['release-check.py','first-creation','SYNTHETIC-NONEXISTENT-GATE']):
            try:rc.main()
            except Exception as ex:self.assertNotEqual(str(ex),'unknown check','template invokes an unimplemented CLI mode')

    def test_author_valid_baseline_really_passes_verified(self):
        d=neg.make_dir();r=neg.run_verified(d)
        self.assertEqual(r.returncode,0,r.stderr)

    def test_independent_valid_artifact_control(self):
        with tempfile.TemporaryDirectory() as t:self.assertEqual(subprocess.run(old.artifact_fixture(Path(t)),capture_output=True).returncode,0)

    def test_wrong_registry_image_binding_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            d=Path(t);cmd=old.artifact_fixture(d);p=d/'registry.json';v=json.loads(p.read_text());v['image']='ghcr.io/other/repository';p.write_text(json.dumps(v))
            self.assertNotEqual(subprocess.run(cmd,capture_output=True).returncode,0)

    def test_malformed_scan_leaf_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            d=Path(t);cmd=old.artifact_fixture(d);(d/'scan-image.json').write_text(json.dumps({'Results':[{'Vulnerabilities':[None]}]}))
            self.assertNotEqual(subprocess.run(cmd,capture_output=True).returncode,0)

    def test_qualifier_missing_checkout_and_inherited_write_all(self):
        r=q.parse_template(TOOLS/'p8c-portal-release.yml.template');s=q.parse_template(TOOLS/'p8c-portal-seed.yml.template')
        for case in ['no-checkout','inherited-write-all','seed-extra-trigger']:
            rr,ss=copy.deepcopy(r),copy.deepcopy(s)
            if case=='no-checkout':
                for j in rr['jobs'].values():j['steps']=[x for x in j['steps'] if not x.get('uses','').startswith('actions/checkout@')]
            elif case=='inherited-write-all':rr['permissions']='write-all'
            else:ss['on']['push']={}
            with self.subTest(case=case):self.assertTrue(q.checks(rr,ss))

    def test_action_pin_error_diagnostic_no_signed_url(self):
        with patch.object(pins,'http_get',side_effect=RuntimeError('https://example.invalid/x?sig=SYNTHETIC_CANARY')):
            result=pins.verify_action({'id':'x','repo':'owner/repo','sha':'a'*40})
            self.assertNotIn('SYNTHETIC_CANARY',json.dumps(result))

if __name__=='__main__':unittest.main(verbosity=2)
