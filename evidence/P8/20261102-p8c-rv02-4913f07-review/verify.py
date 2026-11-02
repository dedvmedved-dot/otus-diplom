"""Independent offline MI review. No network; collector harness mocks subprocesses."""
import copy,datetime,hashlib,io,json,platform,subprocess,sys,unittest
from pathlib import Path
from unittest import mock
ROOT=Path(__file__).resolve().parent
SRC=ROOT/'repo/portal/networkpolicy'
sys.path.insert(0,str(SRC))
import item_diag_regression_test as reg

def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def main():
    hashes={}
    for name,expected in json.loads((ROOT/'source-blobs.json').read_text()).items():
        b=(ROOT/name).read_bytes()
        assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==expected
        hashes[name]={'blob':expected,'sha256':hashlib.sha256(b).hexdigest()}
    start=now()
    p=subprocess.run([sys.executable,'item_diag_regression_test.py'],cwd=SRC,capture_output=True,text=True)
    (ROOT/'item-diag-before.txt').write_text(p.stdout+p.stderr)
    assert p.returncode==1 and 'FAILED (failures=6)' in p.stderr
    before={'command':[sys.executable,'item_diag_regression_test.py'],'start':start,'end':now(),'exit':p.returncode,'methods':4,'subcases':14,'passed_subcases':8,'failed_subcases':6}
    fw=reg.t.fw; orig=fw._i1_item_diag
    def review_candidate(item):
        item=dict(item)
        if item.get('status') is None:item['status']={}
        return orig(item)
    out=io.StringIO();start=now()
    with mock.patch.object(fw,'_i1_item_diag',review_candidate):
        result=unittest.TextTestRunner(stream=out,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(reg.TestOptionalStatusDiagnostic))
    (ROOT/'item-diag-candidate.txt').write_text(out.getvalue())
    assert result.wasSuccessful() and result.testsRun==4
    # Actual request adapter receives a shared decoded object: confirm no mutation of it.
    d=json.loads(reg.t.podlist([copy.deepcopy(reg.t.POD_CFG)]))
    for item in d['items']:
        item.pop('kind');item.pop('apiVersion')
    original=copy.deepcopy(d)
    with mock.patch.object(fw.json,'loads',return_value=d):r=fw._read_podlist('synthetic')
    assert d==original and r['category'] is None and r['complete'] is True
    report={'review_head':'4913f07abd2914dbfa24f39526e05bbc9f0f4ca1','actual_parent':'239c593b76830889b290c8c091be671f522218f3','python':platform.python_version(),'hashes':hashes,'before':before,'review_only_candidate':{'start':start,'end':now(),'methods':4,'subcases':14,'passed_subcases':14,'source_changed':False},'mi01_no_input_mutation':'PASS','mi01':'CLOSED','mi02_value_free_fail_closed':'PASS','mi02_diagnostic_accuracy':'PARTIAL: absent/null optional status masks IMAGE/PORTS/RESTART_POLICY','live_failing_field':'UNKNOWN','live_calls':0}
    (ROOT/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'hashes':'PASS','before':before,'candidate':'4 methods / 14 subcases PASS','mi01_no_input_mutation':'PASS','live_calls':0}))
if __name__=='__main__':main()
