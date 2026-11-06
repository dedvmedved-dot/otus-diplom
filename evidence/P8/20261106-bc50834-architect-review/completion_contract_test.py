"""Single-pass completion contract, offline. No cluster/SSH/registry/CI.
Uses published synthetic fixtures; executes production main/window/sample/predicates.
Only transport/clock/external tools are replaced. Failing assertions denote contract gaps.
Run at repository root: P8C_REVIEW_ROOT=$PWD python3 independent/completion_contract_test.py -v
"""
import contextlib, copy, importlib.util, io, json, os, shutil, subprocess, sys, tempfile, time, unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(os.environ.get('P8C_REVIEW_ROOT',Path.cwd())).resolve()
def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
fixture=load('completion_fixture',ROOT/'evidence/P8/20261105-c8007f5-architect-review/contract_test.py')
old,w,wal=fixture.old,fixture.w,fixture.wal
sys.path.insert(0,str(ROOT/'portal/tools'))
import release_qualification as qual
SOURCE='d2e8598a8720cb2dc5935ac33d218498cf846c45'

class ReadinessCompletion(unittest.TestCase):
    setUp=fixture.WindowRoutes.setUp
    raw=fixture.WindowRoutes.raw
    http=fixture.WindowRoutes.http
    invoke=fixture.WindowRoutes.invoke
    def test_positive_existing_six_stage_route(self):
        for st in w.STAGE_ORDER:
            if st!='S0':self.g['operation_end_utc']=self.now[0]
            self.assertEqual(self.invoke(st)[0],0,st)
    def test_overall_remaining_one_request_stops_before_second_io(self):
        (self.state/'budget.json').write_text(json.dumps({'requests':232,'bytes':0,'seconds':0}))
        code,j=self.invoke()
        self.assertLessEqual(len(self.calls),1,(code,len(self.calls),j['budget']))
    def test_wal_remaining_one_request_stops_before_second_wal_io(self):
        (self.state/'budget.json').write_text(json.dumps({'requests':0,'bytes':0,'seconds':0,'wal_requests':89}))
        code,j=self.invoke()
        self.assertLessEqual(j['budget']['wal_requests'],90,j['budget'])
    def test_nan_budget_blocks_before_io(self):
        (self.state/'budget.json').write_text('{"requests":NaN,"bytes":0,"seconds":0}')
        code,j=self.invoke()
        self.assertEqual(self.calls,[],(code,j))
    def test_budget_cannot_reset_with_new_state_directory_and_same_receipt(self):
        self.assertEqual(self.invoke()[0],0)
        (self.state/'budget.json').write_text(json.dumps({'requests':233,'bytes':0,'seconds':0}))
        other=self.root/'other';other.mkdir();shutil.copyfile(self.state/'stage.receipt',other/'stage.receipt')
        self.calls=[];self.g['operation_end_utc']=self.now[0]
        self.invoke('S1',state=other)
        self.assertEqual(self.calls,[],'Copying a valid receipt must not reset consumed budget')
    def test_wal_elapsed_includes_slot_waits(self):
        code,j=self.invoke();self.assertEqual(code,0)
        self.assertGreaterEqual(j['budget']['wal_seconds'],300,j['budget'])
    def test_inflight_attempt_persisted_before_crash(self):
        def crash(*args):raise RuntimeError('SYNTHETIC process crash after attempt')
        self.raw=crash
        with self.assertRaises(RuntimeError):self.invoke()
        candidates=[self.state/'budget.json',self.root/'authority'/self.g['package_sha256'][:32]/'budget.json']
        records=[json.loads(p.read_text()) for p in candidates if p.exists()]
        self.assertTrue(any(r.get('requests',0)>=1 for r in records),records)
    def test_partial_error_body_bytes_are_charged(self):
        f=self.root/'fake-kubectl';f.write_text('#!'+sys.executable+'\nimport sys\nsys.stdout.write("x"*64)\nsys.exit(1)\n');f.chmod(0o700)
        real=w.run_kubectl_raw
        def raw(k,path,timeout,cap):
            self.calls.append(('failed',path));return real(str(f),path,timeout,cap)
        self.raw=raw;code,j=self.invoke()
        self.assertGreaterEqual(j['budget']['bytes'],64*len(self.calls),j['budget'])
    def test_incomplete_metrics_do_not_overwrite_valid_baseline(self):
        baseline=old.metrics(0,old.NOW-30);w.persist_wal_baseline(self.state,self.g,baseline)
        def bad_http(url,timeout,cap):
            m=old.metrics(1,self.now[0]-1);del m['cnpg_pg_stat_archiver_failed_count']
            return old.text_metrics(m)
        self.http=bad_http;self.invoke()
        self.assertEqual(w.read_wal_baseline(self.state,self.g),baseline)
    def test_health_transient_missing_then_ready_is_polled(self):
        raw=self.raw;count=[0];path=self.rs['HC-DB']['path']
        def transition(*args):
            body,rc=raw(*args)
            if args[1]==path and args[2]==15:
                count[0]+=1
                if count[0]==1:
                    d=json.loads(body);d['status']['conditions']=[{'type':'ContinuousArchiving','status':'True'}];body=json.dumps(d).encode()
            return body,rc
        self.raw=transition;code,j=self.invoke()
        self.assertGreaterEqual(count[0],2,j)
        self.assertEqual(code,0,j)
    def test_health_freshness_rechecked_at_final_pass(self):
        for st in w.STAGE_ORDER[:-1]:
            if st!='S0':self.g['operation_end_utc']=self.now[0]
            self.assertEqual(self.invoke(st)[0],0)
        self.g['operation_end_utc']=self.now[0];raw=self.raw;observations=[]
        def slow(*args):
            b,rc=raw(*args)
            if args[2]==15:self.mono[0]+=14;self.now[0]+=14
            if args[1]==self.rs['HC-DB']['path'] and args[2]==15:observations.append(self.mono[0])
            return b,rc
        self.raw=slow;code,j=self.invoke('S4')
        self.assertTrue(code!=0 or self.mono[0]-observations[-1]<=30,(code,self.mono[0]-observations[-1],j))
    def test_hc_db_wrong_kind_cannot_pass_actual_read_path(self):
        self.docs[self.rs['HC-DB']['path']]['kind']='Pod'
        code,j=self.invoke();self.assertNotEqual(code,0,j)
    def test_pr6_wrong_resource_list_cannot_pass(self):
        self.docs[self.rs['PR-6']['paths'][0]]['kind']='PodList'
        self.docs[self.rs['PR-6']['paths'][0]]['apiVersion']='v1'
        code,j=self.invoke();self.assertNotEqual(code,0,j)
    def test_list_item_cap_enforced(self):
        doc=self.docs[self.rs['HC-OP']['path']];doc['items']=[copy.deepcopy(doc['items'][0]) for _ in range(201)]
        for i,p in enumerate(doc['items']):p['metadata']['name']='op-'+str(i)
        code,j=self.invoke();self.assertNotEqual(code,0,j)
    def test_secondary_role_cannot_pass_primary_sample(self):
        self.docs['/api/v1/namespaces/portal/pods/portal-db-1']['metadata']['labels']['cnpg.io/instanceRole']='replica'
        code,j=self.invoke();self.assertNotEqual(code,0,j)
    def test_pr5_without_uid_namespace_ownership_cannot_pass(self):
        for st in w.STAGE_ORDER[:-1]:
            if st!='S0':self.g['operation_end_utc']=self.now[0]
            self.assertEqual(self.invoke(st)[0],0)
        self.g['operation_end_utc']=self.now[0]
        del self.docs[self.rs['PR-5']['path']]['items'][0]['metadata']
        code,j=self.invoke('S4');self.assertNotEqual(code,0,j)
    def test_post_operation_boundary_requires_bound_action_receipt(self):
        self.assertEqual(self.invoke()[0],0)
        self.g['operation_end_utc']=1
        code,j=self.invoke('S1');self.assertNotEqual(code,0,j)
    def test_receipt_from_different_gate_not_authority(self):
        self.assertEqual(self.invoke()[0],0)
        other=dict(self.g,issued_at_utc='2026-11-05T06:00:01Z')
        self.assertIsNone(w.read_receipt(str(self.state/'stage.receipt'),other))
    def test_journal_does_not_echo_malformed_condition_value(self):
        self.docs[self.rs['HC-DB']['path']]['status']['conditions'][0]['status']='CANARY_PRIVATE_VALUE'
        code,j=self.invoke();self.assertNotIn('CANARY_PRIVATE_VALUE',json.dumps(j))
    def test_postgres_restart_is_checked_by_container_name(self):
        path='/api/v1/namespaces/portal/pods/portal-db-1';raw=self.raw;reads=[0]
        def restarted(*args):
            b,rc=raw(*args)
            if args[1]==path:
                reads[0]+=1;d=json.loads(b)
                d['status']['containerStatuses']=[{'name':'sidecar','restartCount':0},{'name':'postgres','restartCount':reads[0]}]
                b=json.dumps(d).encode()
            return b,rc
        self.raw=restarted;code,j=self.invoke();self.assertNotEqual(code,0,j)
    def test_malformed_health_returns_journal_not_uncaught_exception(self):
        self.docs[self.rs['HC-OP']['path']]['items']=[None]
        try:code,j=self.invoke()
        except Exception as e:self.fail('uncaught '+type(e).__name__)
        self.assertNotEqual(code,0);self.assertIsNotNone(j)

class TransportCompletion(unittest.TestCase):
    def test_kubectl_hard_timeout_not_plus_five_seconds(self):
        with tempfile.TemporaryDirectory() as tmp:
            f=Path(tmp)/'fake-kubectl';f.write_text('#!'+sys.executable+'\nimport time\ntime.sleep(1.6)\nprint("{}")\n');f.chmod(0o700)
            start=time.monotonic();error=None
            try:w.run_kubectl_raw(str(f),'/api/v1/pods',1,1024)
            except w.ReadError as e:error=e
            elapsed=time.monotonic()-start
            self.assertIsNotNone(error,('response after 1s accepted',elapsed))
    def test_http_read_receives_absolute_deadline_not_only_socket_timeout(self):
        class Response:
            def __enter__(self):return self
            def __exit__(self,*args):return False
            def read(self,n):time.sleep(.12);return b'ok'
        class Opener:
            def open(self,*args,**kwargs):return Response()
        with patch('urllib.request.build_opener',return_value=Opener()):
            start=time.monotonic();error=None
            try:w.default_http_get('http://127.0.0.1:9187/metrics',.03,1024)
            except w.ReadError as e:error=e
            self.assertIsNotNone(error,('response after deadline accepted',time.monotonic()-start))

class ReleaseCompletion(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.seed=qual.parse_template(ROOT/'portal/tools/p8c-portal-seed.yml.template')
        self.release=qual.parse_template(ROOT/'portal/tools/p8c-portal-release.yml.template')
    def first_gate(self):
        return {'source_sha':'b'*40,'issued_at_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'expiry_hours':24,'mode':'LIVE'}
    def test_seed_gate_requires_actual_source_repository_package_binding(self):
        p=self.root/'gate.json';p.write_text(json.dumps(self.first_gate()))
        r=subprocess.run([sys.executable,str(ROOT/'portal/tools/release-check.py'),'first-creation',str(p)],env={**os.environ,'GITHUB_SHA':SOURCE,'GITHUB_REPOSITORY':'dedvmedved-dot/otus-diplom'},capture_output=True,text=True)
        self.assertNotEqual(r.returncode,0,r.stdout)
    def test_seed_untrusted_input_is_data_not_shell(self):
        step=next(s for s in self.seed['jobs']['precheck']['steps'] if 'Deliver typed' in s.get('name',''))
        payload=json.dumps({'note':"'; : > ${RUNNER_TEMP}/INJECTED; #"})
        script=step['run'].replace('${{ github.event.inputs.first_creation_gate }}',payload)
        r=subprocess.run(['bash','-c',script],env={**os.environ,'RUNNER_TEMP':str(self.root)},capture_output=True,text=True)
        self.assertFalse((self.root/'INJECTED').exists(),'Workflow input executed shell syntax (benign local sentinel)')
    def test_seed_private_probe_error_plus_gate_does_not_create(self):
        (self.root/'first-creation-gate.json').write_text(json.dumps(self.first_gate()))
        b=self.root/'bin';b.mkdir();shim=b/'python3'
        shim.write_text('#!/bin/sh\nif [ "$2" = private ]; then exit 7; fi\nexec "'+sys.executable+'" "$@"\n');shim.chmod(0o700)
        step=next(s for s in self.seed['jobs']['precheck']['steps'] if s.get('id')=='pre')
        env={**os.environ,'PATH':str(b)+':'+os.environ['PATH'],'RUNNER_TEMP':str(self.root),'GITHUB_OUTPUT':str(self.root/'out'),'GITHUB_SHA':SOURCE}
        r=subprocess.run(['bash','-c',step['run']],cwd=ROOT,env=env,capture_output=True,text=True)
        output=(self.root/'out').read_text() if (self.root/'out').exists() else ''
        self.assertNotIn('CREATE_ALLOWED',output,(r.returncode,output))
    def test_seed_reuse_control_no_gate_evaluation(self):
        b=self.root/'bin';b.mkdir();shim=b/'python3';shim.write_text('#!/bin/sh\nif [ "$2" = private ]; then exit 0; fi\nexit 99\n');shim.chmod(0o700)
        step=next(s for s in self.seed['jobs']['precheck']['steps'] if s.get('id')=='pre')
        r=subprocess.run(['bash','-c',step['run']],cwd=ROOT,env={**os.environ,'PATH':str(b)+':'+os.environ['PATH'],'RUNNER_TEMP':str(self.root),'GITHUB_OUTPUT':str(self.root/'out')},capture_output=True,text=True)
        self.assertEqual(r.returncode,0);self.assertIn('result=REUSE',(self.root/'out').read_text())
    def test_seed_equal_application_digest_is_nonzero(self):
        b=self.root/'bin';b.mkdir();shim=b/'python3'
        shim.write_text('#!/bin/sh\nif [ "$2" = private ]; then echo "{}"; exit 0; fi\nexec "'+sys.executable+'" "$@"\n');shim.chmod(0o700)
        step=next(s for s in self.seed['jobs']['seed']['steps'] if s.get('name','').startswith('Record seed digest'))
        r=subprocess.run(['bash','-c',step['run']],cwd=ROOT,env={**os.environ,'PATH':str(b)+':'+os.environ['PATH'],'RUNNER_TEMP':str(self.root),'SEED_DIGEST':'sha256:'+'a'*64,'APP_IMAGE_DIGEST':'sha256:'+'a'*64},capture_output=True,text=True)
        self.assertNotEqual(r.returncode,0,(self.root/'seed-evidence.json').read_text())
    def test_scan_other_image_cannot_bind_release(self):
        negative=load('completion_negative',ROOT/'portal/tools/test_release_negative.py')
        d=negative.make_dir();self.addCleanup(shutil.rmtree,d)
        (d/'scan-image.json').write_text(json.dumps({'ArtifactName':'ghcr.io/other/image@sha256:'+'b'*64,'Metadata':{'RepoDigests':['ghcr.io/other/image@sha256:'+'b'*64]},'Results':[]}))
        r=negative.run_verified(d);self.assertNotEqual(r.returncode,0,r.stdout)
    def test_seed_has_failure_cleanup_route(self):
        steps=self.seed['jobs']['seed']['steps']
        always_cleanup=any(s.get('if') in ('always()','${{ always() }}') and ('kill ' in s.get('run','') or 'cleanup' in s.get('run','')) for s in steps)
        trapped_cleanup=any('trap ' in s.get('run','') and 'buildctl build' in s.get('run','') for s in steps)
        self.assertTrue(always_cleanup or trapped_cleanup,'kill only after successful build, no failure/cancel cleanup')
    def test_seed_tag_is_source_bound(self):
        self.assertNotEqual(self.seed['env'].get('SEED_TAG'),'bootstrap-seed')
    def test_seed_has_registry_byte_proof_before_acceptance(self):
        runs='\n'.join(s.get('run','') for s in self.seed['jobs']['seed']['steps'])
        self.assertIn('release-check.py registry',runs)
    def test_release_has_execution_gate_before_protected_steps(self):
        runs='\n'.join(s.get('run','') for s in self.release['jobs']['release']['steps'])
        self.assertTrue('gate' in runs and 'run_attempt' in str(self.release),'No runtime gate binding/expiry/one-attempt enforcement')
    def test_qualifier_rejects_missing_seed_precheck_job(self):
        seed=copy.deepcopy(self.seed);seed['jobs'].pop('precheck')
        self.assertTrue(qual.checks(self.release,seed),'qualifier accepts seed without precheck')

if __name__=='__main__':unittest.main(verbosity=2)
