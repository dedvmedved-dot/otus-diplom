"""Offline review of 980cee5. No live calls; all collector subprocesses mocked."""
import copy
import datetime
import hashlib
import io
import json
import platform
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock
import podlist_boundary_regression_test as regression

ROOT = Path(__file__).resolve().parent
def utc(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def blob(p):
    b=p.read_bytes()
    return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()

def candidate(obj, expect_ns=None):
    # REVIEW-ONLY hypothesis: inherit missing type metadata from validated PodList.
    # This monkeypatch is never written to application/collector source.
    if not isinstance(obj, dict): raise ValueError('object required')
    c = copy.copy(obj)
    for k, v in [('kind', 'Pod'), ('apiVersion', 'v1')]:
        if k not in c: c[k] = v
    return ORIGINAL(c, expect_ns)

ORIGINAL = regression.t.fw.project_pod_identity

def main():
    start = utc()
    hashes={}
    for name, expected in json.loads((ROOT/'source-blobs.json').read_text()).items():
        p=ROOT/name; assert blob(p)==expected, name
        hashes[name]={'blob': expected, 'sha256': sha(p)}
    for line in (ROOT/'live/SHA256SUMS.result').read_text().splitlines():
        expected,name=line.split()
        p=ROOT/({'followup-output/followup.jsonl':'live/followup.jsonl','run-meta.txt':'live/run-meta.txt'}.get(name,name))
        assert sha(p)==expected, name
    rows=[json.loads(x) for x in (ROOT/'live/followup.jsonl').read_text().splitlines()]
    by={r['id']:r for r in rows}; assert len(by)==len(rows)==9
    assert sum(r['argv'] is not None for r in rows)==4
    assert by['F-I1']['diag']=='ITEM' and by['F-I1']['category']=='PARSE_ERROR'
    assert by['F-I1']['output']=='' and by['F-I1']['complete'] is False
    assert json.loads(by['F-CS']['output'])['compatible'] is True
    assert by['F-CNP']['complete'] is True and by['F-CNP']['category'] is None
    assert by['F-CNP']['journal'][0]['received']==by['F-CNP']['journal'][0]['validated']==0
    for dep in regression.DEPS:
        assert by[dep]['category']=='BLOCKED_NOT_EXECUTED' and by[dep]['blocked_by']==['F-I1']
        assert by[dep]['argv'] is None and by[dep]['exit'] is None
    t0=utc()
    p=subprocess.run([sys.executable,'podlist_boundary_regression_test.py'],cwd=ROOT,text=True,capture_output=True)
    (ROOT/'regression-before.txt').write_text(p.stdout+p.stderr)
    assert p.returncode==1 and 'FAILED (failures=4)' in p.stderr
    before={'command':[sys.executable,'podlist_boundary_regression_test.py'],'start':t0,'end':utc(),'exit':p.returncode,'methods':6,'passed':2,'failed':4}
    stream=io.StringIO(); t0=utc()
    with mock.patch.object(regression.t.fw, 'project_pod_identity', candidate):
        result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(regression.TestTypedPodListBoundary))
    (ROOT/'review-only-adapter.txt').write_text(stream.getvalue())
    assert result.wasSuccessful() and result.testsRun==6
    report={'review_head':'980cee55e32bf87451919d37c898d40ae33d4557','accepted_source':'fdfc776570c7f44e559eefcd092e2ca58595ee48','python':platform.python_version(),'start':start,'end':utc(),'hashes':hashes,'live_artifact':{'records':9,'collector_calls':4,'ok':3,'parse_error':1,'blocked':5,'reported_exit':1,'all_four_SHA256SUMS_matches':True},'regression_before':before,'review_only_adapter':{'command':'verify.py: unittest with in-memory F-I1 projector adapter','start':t0,'end':utc(),'methods':6,'passed':6,'failed':0,'source_changed':False},'live_failing_field':'UNKNOWN — no raw response retained','proven_source_defect':'legal typed PodList item without TypeMeta rejected by standalone Pod projector','preflight_and_remote_hash_checks':'operator attested; separate raw preflight transcript not in committed package','live_or_ssh_calls':0,'full_previously_accepted_suites_rerun':False}
    (ROOT/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'artifact_hashes':'PASS','before':before,'review_only_adapter':'6/6 PASS','source_changed':False,'live_calls':0},indent=2))

if __name__=='__main__': main()
