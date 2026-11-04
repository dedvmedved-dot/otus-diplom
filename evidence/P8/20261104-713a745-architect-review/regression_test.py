"""Desired-contract regression tests for 713a745. Offline: no cluster/registry calls.

Usage: python3 regression_test.py /path/to/otus-diplom
Failures on the reviewed package are evidence of missing task requirements.
"""
import base64
import calendar
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

ROOT = Path(sys.argv.pop(1)).resolve()
TOOLS = ROOT / 'portal/tools'

def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

w = module('review_wrapper', TOOLS / 'readiness/wrapper.py')
q = module('review_qualification', TOOLS / 'release_qualification.py')
pins = module('review_pins', TOOLS / 'verify-pins.py')
release = module('review_release', TOOLS / 'release-check.py')
NOW = calendar.timegm((2026, 11, 4, 1, 0, 0))

def gate(**kw):
    d = dict(mode='LIVE', context=w.CONTEXT, source_sha='a' * 40,
             issued_at_utc='2026-11-04T00:00:00Z', expiry_hours=24,
             run_budget_consumed=False)
    d.update(kw)
    return d

class TestReadinessContract(unittest.TestCase):
    def test_missing_runtime_hash_manifest_rejected(self):
        self.assertFalse(w.validate_gate(gate(), NOW)[0])

    def test_unknown_gate_mode_rejected(self):
        self.assertFalse(w.validate_gate(gate(mode='ARBITRARY'), NOW)[0])

    def test_future_gate_rejected(self):
        self.assertFalse(w.validate_gate(gate(issued_at_utc='2027-01-01T00:00:00Z'), NOW)[0])

    def test_expiry_not_caller_expandable(self):
        self.assertFalse(w.validate_gate(gate(expiry_hours=100000), NOW + 48 * 3600)[0])

    def test_invalid_stage_not_success(self):
        with tempfile.TemporaryDirectory() as d:
            g = Path(d) / 'gate.json'; out = Path(d) / 'out.json'
            g.write_text(json.dumps(gate()))
            with patch.object(w, 'run_kubectl_raw', side_effect=AssertionError('unexpected transport')), patch('sys.stdout', new=io.StringIO()):
                rc = w.main(['--gate', str(g), '--out', str(out), '--stage', 'TYPO', '--now', str(NOW)])
            self.assertNotEqual(rc, 0)

    def test_list_continue_null_rejected(self):
        body = b'{"kind":"PodList","apiVersion":"v1","metadata":{"resourceVersion":"1","continue":null},"items":[]}'
        with self.assertRaises(w.ReadError):
            w.validate_envelope(body)

    def test_wrong_envelope_types_rejected(self):
        with self.assertRaises(w.ReadError):
            w.validate_envelope(b'{"kind":"PodList","apiVersion":false,"metadata":[],"items":"bad"}')

    def test_unhealthy_objects_never_pass(self):
        cases = {
            'HC-DB': {'spec': {'instances': 3}, 'status': {'instances': 3, 'readyInstances': 0, 'conditions': [{'type': 'Ready', 'status': 'False'}]}},
            'HC-ARCH-STATE': {'status': {'conditions': [{'type': 'ContinuousArchiving', 'status': 'False'}]}},
            'HC-PORTAL': {'status': {'readyReplicas': 0}},
            'HC-GW': {'status': {'conditions': [{'type': 'Programmed', 'status': 'False'}]}},
            'HC-DNS': {'items': []}, 'HC-OP': {'items': []}, 'PR-3': {'items': []}, 'PR-5': {'items': []},
        }
        for rid, doc in cases.items():
            with self.subTest(read=rid):
                self.assertNotEqual(w.classify(doc, rid), w.PASS)

    def test_pr6_list_of_responses_not_exception(self):
        docs = [{'kind':'List', 'apiVersion':'v1', 'items':[]} for _ in range(9)]
        try:
            result = w.classify(docs, 'PR-6')
        except Exception as e:
            self.fail('PR-6 escaped exception: ' + type(e).__name__)
        self.assertNotEqual(result, w.PASS)  # Missing Tier/Felix/identity baseline.

    def test_arbitrary_raw_read_not_executed(self):
        with patch.object(w.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, b'{}', b'')) as proc:
            try:
                w.run_kubectl_raw('kubectl', '/api/v1/namespaces/portal/secrets', 5, 1024)
            except w.ReadError:
                pass
            self.assertEqual(proc.call_count, 0)

    def test_readset_item_cap_enforced(self):
        rs = w.load_readset()
        body = json.dumps({'kind':'ServiceList','apiVersion':'v1','metadata':{'resourceVersion':'1'},'items':[{},{}]}).encode()
        with patch.object(w, 'run_kubectl_raw', return_value=body):
            with self.assertRaises(w.ReadError):
                w.run_read(rs, 'PR-5', 'unused')

    def test_nonpass_exit_not_zero(self):
        with tempfile.TemporaryDirectory() as d:
            g=Path(d)/'gate.json';out=Path(d)/'out.json';g.write_text(json.dumps(gate()))
            with patch.object(w, 'run_kubectl_raw', side_effect=w.ReadError('TIMEOUT')), patch('sys.stdout',new=io.StringIO()):
                rc=w.main(['--gate',str(g),'--out',str(out),'--stage','S1','--now',str(NOW)])
            self.assertNotEqual(rc,0)

    def test_same_gate_cannot_restart_with_fresh_output(self):
        with tempfile.TemporaryDirectory() as d:
            g=Path(d)/'gate.json';g.write_text(json.dumps(gate()))
            with patch.object(w,'run_kubectl_raw',side_effect=w.ReadError('TIMEOUT')) as transport, patch('sys.stdout',new=io.StringIO()):
                w.main(['--gate',str(g),'--out',str(Path(d)/'first.json'),'--stage','S1','--now',str(NOW)])
                before=transport.call_count
                w.main(['--gate',str(g),'--out',str(Path(d)/'second.json'),'--stage','S1','--now',str(NOW)])
            self.assertEqual(transport.call_count,before)

    def test_utc_expiry_independent_of_host_timezone(self):
        previous=os.environ.get('TZ')
        try:
            os.environ['TZ']='Etc/GMT+3';time.tzset()
            self.assertFalse(w.validate_gate(gate(),NOW+24*3600)[0])
        finally:
            if previous is None: os.environ.pop('TZ',None)
            else: os.environ['TZ']=previous
            time.tzset()

class TestQualificationContract(unittest.TestCase):
    def docs(self):
        return (q.parse_template(TOOLS/'p8c-portal-release.yml.template'), q.parse_template(TOOLS/'p8c-portal-seed.yml.template'))

    def test_empty_seed_rejected(self):
        r,s=self.docs()
        self.assertTrue(q.checks(r,{}))

    def test_additional_trigger_rejected(self):
        r,s=self.docs();r['on']['push']={}
        self.assertTrue(q.checks(r,s))

    def test_extra_release_permission_rejected(self):
        r,s=self.docs();r['jobs']['release']['permissions']['actions']='write'
        self.assertTrue(q.checks(r,s))

    def test_mutable_checkout_action_ref_rejected(self):
        r,s=self.docs()
        for job in r['jobs'].values():
            for step in job['steps']:
                if step.get('uses','').startswith('actions/checkout@'):step['uses']='actions/checkout@main'
        self.assertTrue(q.checks(r,s))

    def test_first_job_persist_credentials_rejected(self):
        r,s=self.docs();r['jobs']['test']['steps'][0]['with']['persist-credentials']=True
        self.assertTrue(q.checks(r,s))

class TestEvidenceContract(unittest.TestCase):
    def test_pin_mismatch_nonzero_exit(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.object(pins,'CACHE',d), patch.object(pins,'verify_binary',return_value={'id':'synthetic','status':'MISMATCH'}), patch.object(pins,'verify_action',return_value={'id':'synthetic-action','status':'UNAVAILABLE'}), patch.object(pins,'verify_image',return_value={'id':'synthetic-image','status':'UNAVAILABLE'}), patch('sys.stdout',new=io.StringIO()):
                rc=pins.main()
            self.assertTrue(isinstance(rc,int) and rc!=0)

    def test_signed_cdn_query_not_persisted(self):
        data=b'synthetic-public-binary'; pin={'id':'fixture','url':'https://github.com/example/asset','sha256':pins.sha256(data)}
        with tempfile.TemporaryDirectory() as d:
            with patch.object(pins,'CACHE',d),patch.object(pins,'http_get_follow',return_value=(data,'https://release-assets.githubusercontent.com/fixture?sig=SYNTHETIC_CANARY&jwt=SYNTHETIC_CANARY',200)):
                result=pins.verify_binary(pin)
            self.assertNotIn('SYNTHETIC_CANARY',json.dumps(result))

    def test_invalid_scan_private_registry_evidence_rejected(self):
        digest='sha256:'+'b'*64;source='a'*40
        signature={'critical':{'image':{'docker-manifest-digest':digest},'identity':{'docker-reference':release.IMAGE}},'optional':{'ref':source}}
        def att(typ,predicate):
            statement={'_type':'https://in-toto.io/Statement/v1','subject':[{'name':release.IMAGE,'digest':{'sha256':digest[7:]}}],'predicateType':typ,'predicate':predicate}
            return json.dumps({'payload':base64.b64encode(json.dumps(statement).encode()).decode()})
        required=['sbom.spdx.json','provenance.json','build-metadata.json','scan-binary.json','scan-image.json','signature.json','attestation-sbom.jsonl','attestation-provenance.jsonl','private-before.json','private-after.json','registry.json','sign.txt','attest-sbom.txt','attest-provenance.txt','go-version.txt','go-binary.sha256']
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            for name in required:(p/name).write_text('INVALID_NOT_EVIDENCE')
            (p/'signature.json').write_text(json.dumps(signature))
            (p/'sbom.spdx.json').write_text('{}')
            (p/'attestation-sbom.jsonl').write_text(att(release.SPDX,{}))
            (p/'attestation-provenance.jsonl').write_text(att(release.SLSA,release.predicate(source)))
            with patch.object(sys,'argv',['release-check.py','verified',d,digest,source]),patch('sys.stdout',new=io.StringIO()):
                with self.assertRaises((ValueError,KeyError,TypeError)):
                    release.main()

if __name__=='__main__':unittest.main(verbosity=2)
