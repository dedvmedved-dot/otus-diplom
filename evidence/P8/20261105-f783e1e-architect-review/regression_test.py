"""Architect desired-contract regressions against 8ffd457; OFFLINE ONLY.

Run from an extracted repository root with portal/tools available:
 python3 regression_test.py
External transports are mocked. Seed lifecycle executes actual template shell
with fake unshare/rootlesskit/buildctl; no OCI build/download/push or kubectl.
Expected assertions are the existing completion-task contract, not new scope.
"""
import base64
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(os.environ.get('P8C_REVIEW_ROOT', str(Path.cwd()))).resolve()
TOOLS = ROOT / 'portal/tools'
sys.path.insert(0, str(TOOLS / 'readiness'))
sys.path.insert(0, str(TOOLS))
import wrapper as w
import wal
import release_qualification as q

def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

rc = module('release_check', TOOLS / 'release-check.py')
pins = module('pins', TOOLS / 'verify-pins.py')
NOW = w.parse_utc('2026-11-04T01:00:00Z')

def gate():
    return dict(mode='LIVE', context=w.CONTEXT, source_sha='8ffd45792123e8e2ae1ccdd330ee5e1d013523f9',
                package_sha256=w.package_hash(), issued_at_utc='2026-11-04T00:00:00Z', expiry_hours=24)

def clock():
    return dict(bound=1, source='synthetic-clock-evidence', provenance_sha256='a'*64,
                node='node-01', backend='exporter', observed_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()), validity_hours=1)

def docs():
    c={'metadata':{'uid':'c','name':'portal-db'},'status':{'currentPrimary':'portal-db-1'}}
    p={'metadata':{'uid':'p','name':'portal-db-1','namespace':'portal',
                   'ownerReferences':[{'uid':'c','kind':'Cluster','name':'portal-db'}],
                   'labels':{'cnpg.io/cluster':'portal-db','cnpg.io/instanceRole':'primary'}},
       'spec':{'nodeName':'node-01'},'status':{'podIP':'10.244.1.1','containerStatuses':[{'name':'postgres','restartCount':0}]}}
    return c,p

def metrics(count=2, when=100):
    return dict(zip(wal.ARCHIVER_SERIES,[count,0,when,0,1]))

def metric_text(m):
    return ''.join(f'{k} {v}\n' for k,v in m.items())

class Predicates(unittest.TestCase):
    def test_pr3_wrong_slice_ports_and_unready_rejected(self):
        d={'items':[{'ports':[{'port':9999,'protocol':'UDP'}], 'endpoints':[
            {'addresses':['172.30.140.101','172.30.140.102','172.30.140.103','172.30.140.250'], 'conditions':{'ready':False}}]}]}
        self.assertNotEqual(w.pred_pr3(d)[0], w.PASS)

    def test_pr6_changed_felix_tier_baseline_rejected(self):
        ds=[{'items':[]} for _ in range(9)]
        ds[5]={'items':[{'metadata':{'name':'unexpected'},'spec':{'order':1}}]}
        ds[6]={'items':[{'metadata':{'name':'node.changed'},'spec':{'bpfEnabled':True}}]}
        self.assertNotEqual(w.pred_pr6(ds)[0],w.PASS)

    def test_operator_running_not_ready_rejected(self):
        d={'items':[{'metadata':{'deletionTimestamp':'2026-11-04T00:00:00Z'},'status':{'phase':'Running','conditions':[{'type':'Ready','status':'False'}]}}]}
        self.assertNotEqual(w.pred_hc_op(d)[0],w.PASS)

    def test_dns_ready_without_ports_rejected(self):
        self.assertNotEqual(w.pred_hc_dns({'items':[{'endpoints':[{'conditions':{'ready':True}}]}]})[0],w.PASS)

    def test_wrong_list_kind_and_explicit_null_continue_rejected(self):
        with self.assertRaises(w.ReadError):
            w.validate_envelope(json.dumps({'apiVersion':'wrong/v1','kind':'SecretList','metadata':{'continue':None},'items':[]}),True)

class GateState(unittest.TestCase):
    def invoke(self, root, stage, state_name, output_name, g=None):
        gp=root/'gate.json';gp.write_text(json.dumps(g or gate()))
        state=root/state_name;state.mkdir(exist_ok=True)
        predicates={k:(v[0],lambda d:(w.PASS,'synthetic valid observation')) for k,v in w.PREDICATES.items()}
        with patch.object(w,'run_read',return_value={}) as transport, patch.object(w,'PREDICATES',predicates), patch.object(w,'run_wal_sample',return_value=(w.PASS,'synthetic WAL')), patch('sys.stdout',new=io.StringIO()), patch('sys.stderr',new=io.StringIO()):
            code=w.main(['--gate',str(gp),'--stage',stage,'--state-dir',str(state),'--out',str(root/output_name),'--now',str(NOW)])
            return code,transport.call_count

    def test_s4_before_s0_no_requests(self):
        with tempfile.TemporaryDirectory() as d:
            code,n=self.invoke(Path(d),'S4','state','out')
            self.assertNotEqual(code,0);self.assertEqual(n,0)

    def test_same_gate_new_state_directory_no_replay(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);self.invoke(root,'S0','state1','one')
            code,n=self.invoke(root,'S0','state2','two')
            self.assertNotEqual(code,0);self.assertEqual(n,0)

    def test_existing_output_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'out').write_text('existing-evidence')
            self.invoke(root,'S0','state','out')
            self.assertEqual((root/'out').read_text(),'existing-evidence')

    def test_expired_gate_cannot_use_cli_now(self):
        with tempfile.TemporaryDirectory() as d, patch.object(w.time,'time',return_value=NOW+10*86400):
            code,n=self.invoke(Path(d),'S0','state','out')
            self.assertNotEqual(code,0);self.assertEqual(n,0)

    def test_wal_bytes_participate_in_package_hash(self):
        old=w.package_hash(); original=Path.read_bytes
        def changed(p):
            b=original(p)
            return b+b'\n# altered WAL source\n' if p.name=='wal.py' else b
        with patch.object(Path,'read_bytes',changed):
            self.assertNotEqual(w.package_hash(),old)

class WALContract(unittest.TestCase):
    def test_clock_expired_wrong_node_not_valid(self):
        e=clock();e['node']='different-node';e['gate_sha256']='wrong';e['observed_utc']='2020-01-01T00:00:00Z'
        self.assertFalse(wal.validate_clock(e)[0])

    def test_first_baseline_not_progress_pass(self):
        c,p=docs()
        self.assertNotEqual(wal.wal_sample(c,p,metric_text(metrics()),c,p,clock())[0],w.PASS)

    def test_primary_swap_after_sample_rejected(self):
        c,p=docs();c2=copy.deepcopy(c);c2['status']['currentPrimary']='portal-db-2'
        self.assertNotEqual(wal.wal_sample(c,p,metric_text(metrics()),c2,p,clock(),metrics(1,50),60)[0],w.PASS)

    def test_pod_ip_restart_owner_change_rejected(self):
        c,p=docs();p2=copy.deepcopy(p);p2['status']['podIP']='10.244.9.9';p2['status']['containerStatuses'][0]['restartCount']=1
        p2['metadata']['ownerReferences'][0]['uid']='other'
        self.assertNotEqual(wal.wal_sample(c,p,metric_text(metrics()),c,p2,clock(),metrics(1,50),60)[0],w.PASS)

    def test_future_metric_timestamp_rejected(self):
        c,p=docs()
        self.assertNotEqual(wal.wal_sample(c,p,metric_text(metrics(2,10**15)),c,p,clock(),metrics(1,50),60)[0],w.PASS)

    def test_duplicate_series_rejected(self):
        c,p=docs();s=metric_text(metrics())+'cnpg_pg_stat_archiver_archived_count 10\n'
        self.assertNotEqual(wal.wal_sample(c,p,s,c,p,clock(),metrics(1,50),60)[0],w.PASS)

    def test_sample_metadata_budget_5s_256k(self):
        c,p=docs();responses=[c,p,p,c];calls=[]
        def raw(pathbin,path,timeout,cap):
            calls.append((timeout,cap));v=responses.pop(0);v=dict(v,apiVersion='v1');return json.dumps(v).encode(),0
        with patch.object(w,'run_kubectl_raw',side_effect=raw):
            w.run_wal_sample('FAKE',lambda *a:metric_text(metrics()).encode(),clock(),gate())
        self.assertEqual(calls,[(5,256*1024)]*4)

    def test_default_http_has_no_environment_proxy(self):
        import urllib.request
        with patch.dict(os.environ,{'http_proxy':'http://example.invalid:3128','https_proxy':'http://example.invalid:3128'}), patch.object(urllib.request,'build_opener',wraps=urllib.request.build_opener) as op:
            # Replace open, never network. Inspect the actual constructed opener.
            with patch.object(urllib.request.OpenerDirector,'open',side_effect=RuntimeError('offline')):
                with self.assertRaises(w.ReadError):w.default_http_get('http://127.0.0.1:9187/metrics',5,1024)
            explicit=[h for h in op.call_args.args if isinstance(h,urllib.request.ProxyHandler)]
            self.assertTrue(explicit and explicit[0].proxies=={})

class Transport(unittest.TestCase):
    def test_blocking_body_obeys_hard_deadline(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'fake';p.write_text('#!'+sys.executable+'\nimport time\ntime.sleep(6)\nprint("{}")\n');p.chmod(0o700)
            start=time.monotonic()
            try:w.run_kubectl_raw(str(p),'/api/v1/pods',0,1024)
            except w.ReadError:pass
            self.assertLess(time.monotonic()-start,5.5)

class Qualification(unittest.TestCase):
    def test_invalid_templates_rejected(self):
        release=q.parse_template(TOOLS/'p8c-portal-release.yml.template');seed=q.parse_template(TOOLS/'p8c-portal-seed.yml.template')
        for label in ('extra-trigger','extra-permission','mutable-checkout','seed-no-build'):
            r,s=copy.deepcopy(release),copy.deepcopy(seed)
            if label=='extra-trigger':r['on']['push']={}
            if label=='extra-permission':r['jobs']['release']['permissions']['actions']='write'
            if label=='mutable-checkout':
                for j in r['jobs'].values():
                    for step in j['steps']:
                        if step.get('uses','').startswith('actions/checkout@'):step['uses']='actions/checkout@main';step['with']['ref']='main'
            if label=='seed-no-build':
                s['jobs']['seed']['steps']=[dict(run='private',env={'GITHUB_TOKEN':'${{ secrets.GITHUB_TOKEN }}'})]
            with self.subTest(case=label):self.assertTrue(q.checks(r,s))

def artifact_fixture(d):
    source='a'*40;digest='sha256:'+'b'*64
    sbom={'spdxVersion':'SPDX-2.3','SPDXID':'SPDXRef-DOCUMENT'};prov=rc.predicate(source)
    def att(pred,typ):
        st={'_type':'https://in-toto.io/Statement/v1','predicateType':typ,'subject':[{'name':rc.IMAGE,'digest':{'sha256':digest[7:]}}],'predicate':pred}
        return {'payload':base64.b64encode(json.dumps(st).encode()).decode()}
    objects={'build-metadata.json':{'containerimage.digest':digest},'sbom.spdx.json':sbom,'provenance.json':prov,
             'signature.json':[{'critical':{'image':{'docker-manifest-digest':digest},'identity':{'docker-reference':rc.IMAGE}},'optional':{'ref':source}}],
             'attestation-sbom.jsonl':att(sbom,rc.SPDX),'attestation-provenance.jsonl':att(prov,rc.SLSA),
             'scan-binary.json':{'Results':[]},'scan-image.json':{'Results':[]},
             'registry.json':{'image':rc.IMAGE,'digest':digest,'manifestVerified':True},
             'private-before.json':{'name':'otus-diplom-portal','package_type':'container','visibility':'private','repository':rc.REPO},
             'private-after.json':{'name':'otus-diplom-portal','package_type':'container','visibility':'private','repository':rc.REPO}}
    for name,obj in objects.items():(d/name).write_text(json.dumps(obj))
    for name in ['sign.txt','attest-sbom.txt','attest-provenance.txt','go-version.txt','go-binary.sha256']:(d/name).write_text('SYNTHETIC not cryptographic evidence')
    return [sys.executable,str(TOOLS/'release-check.py'),'verified',str(d),digest,source]

class Release(unittest.TestCase):
    def test_positive_payload_binding_control(self):
        with tempfile.TemporaryDirectory() as t:
            r=subprocess.run(artifact_fixture(Path(t)),capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stderr)

    def test_invalid_semantics_rejected_from_valid_baseline(self):
        cases={'private-before.json':{'visibility':'public'},'private-after.json':{'repository':'wrong'},
               'registry.json':{'digest':'sha256:'+'c'*64,'manifestVerified':False},
               'scan-image.json':{'Results':[{'Vulnerabilities':[{'Severity':'CRITICAL'}]}]},
               'scan-binary.json':[]}
        for name,bad in cases.items():
            with self.subTest(artifact=name),tempfile.TemporaryDirectory() as t:
                d=Path(t);cmd=artifact_fixture(d);(d/name).write_text(json.dumps(bad))
                r=subprocess.run(cmd,capture_output=True,text=True)
                self.assertNotEqual(r.returncode,0,r.stdout)

    def test_author_negative_fixtures_reach_named_check(self):
        # These five author cases share {} build metadata and stop there first.
        names=['scan-binary.json','provenance.json','sbom.spdx.json']
        neg=module('negative',TOOLS/'test_release_negative.py')
        for name in names:
            with self.subTest(name=name):
                d=neg.make_dir();(d/name).write_text('invalid')
                with patch.object(sys,'argv',['release-check.py','verified',str(d),'sha256:'+'a'*64,'a'*40]):
                    try:rc.main()
                    except ValueError as e:self.assertNotIn('build-metadata digest',str(e))

class Seed(unittest.TestCase):
    def precheck(self, approval):
        seed=q.parse_template(TOOLS/'p8c-portal-seed.yml.template')
        step=next(s for s in seed['jobs']['precheck']['steps'] if s.get('id')=='pre')
        with tempfile.TemporaryDirectory() as t:
            d=Path(t);fake=d/'python3';fake.write_text('#!/bin/sh\nexit 1\n');fake.chmod(0o700)
            env=dict(os.environ,PATH=str(d)+':'+os.environ['PATH'],RUNNER_TEMP=t,GITHUB_OUTPUT=str(d/'output'),SEED_FIRST_CREATION_GATE=approval)
            r=subprocess.run(['bash','-c',step['run']],env=env,capture_output=True,text=True,timeout=3)
            return r.returncode,(d/'output').read_text()

    def test_failed_precheck_cannot_create_from_magic_env(self):
        code,out=self.precheck('approved-by-separate-owner-gate')
        self.assertNotIn('CREATE_ALLOWED',out,'All private-check failures must not become first-creation approval')

    def test_stop_is_non_success(self):
        code,out=self.precheck('')
        self.assertIn('STOP',out)
        self.assertNotEqual(code,0)

    def test_recipe_resolves_at_actual_working_directory(self):
        seed=q.parse_template(TOOLS/'p8c-portal-seed.yml.template')
        s=next(x for x in seed['jobs']['seed']['steps'] if x.get('name','').startswith('Build + push'))
        self.assertTrue((ROOT/s.get('working-directory','.')/'Seed.Containerfile').is_file())

    def test_daemon_survives_until_build_step(self):
        seed=q.parse_template(TOOLS/'p8c-portal-seed.yml.template')
        s=next(x for x in seed['jobs']['seed']['steps'] if x.get('name','').startswith('Start rootless'))
        with tempfile.TemporaryDirectory() as t:
            d=Path(t);alive=d/'alive';pidfile=d/'pid'
            scripts={'unshare':'#!/bin/sh\nexit 0\n',
                     'buildctl':'#!/bin/sh\ntest -f "$ALIVE"\n',
                     'rootlesskit':'#!'+sys.executable+'\nimport os,signal,time\nfrom pathlib import Path\np=Path(os.environ["ALIVE"]);p.write_text("up");Path(os.environ["PIDFILE"]).write_text(str(os.getpid()))\ndef stop(*a):\n p.unlink(missing_ok=True);raise SystemExit(0)\nsignal.signal(signal.SIGTERM,stop)\nwhile True:time.sleep(.01)\n'}
            for name,text in scripts.items():(d/name).write_text(text);(d/name).chmod(0o700)
            env=dict(os.environ,PATH=str(d)+':'+os.environ['PATH'],ALIVE=str(alive),PIDFILE=str(pidfile),GITHUB_ENV=str(d/'env'))
            try:
                # Substitute only log output path; execute actual start-step logic.
                r=subprocess.run(['bash','-c',s['run'].replace('/tmp/seed-buildkitd.log',str(d/'log'))],env=env,capture_output=True,text=True,timeout=8)
                self.assertEqual(r.returncode,0,r.stderr)
                for _ in range(50):
                    if not alive.exists():break
                    time.sleep(.01)
                self.assertTrue(alive.exists(),'start-step EXIT trap killed the fake daemon before next step')
            finally:
                if pidfile.exists():
                    try:os.kill(int(pidfile.read_text()),15)
                    except ProcessLookupError:pass

class PinDiagnostics(unittest.TestCase):
    def test_exception_diagnostic_cannot_echo_signed_query(self):
        with patch.object(pins,'http_get_follow',side_effect=RuntimeError('https://example.invalid/x?sig=SYNTHETIC_CANARY')), tempfile.TemporaryDirectory() as t, patch.object(pins,'CACHE',t):
            result=pins.verify_binary({'id':'fixture','url':'https://example.invalid/x','sha256':'a'*64})
            self.assertNotIn('SYNTHETIC_CANARY',json.dumps(result))

if __name__=='__main__':unittest.main(verbosity=2)
