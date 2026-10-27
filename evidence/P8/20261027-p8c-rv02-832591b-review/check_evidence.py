import collections, datetime, hashlib, importlib.util, json, pathlib, re
root=pathlib.Path(__file__).parent
checks={}
for line in (root/'SHA256SUMS').read_text().splitlines():
    expected,name=line.split(None,1);name=name.strip()
    assert name in ['result/supplemental.jsonl','version.json','script-check.txt','run-manifest.txt']
    actual=hashlib.sha256((root/name).read_bytes()).hexdigest()
    assert actual==expected,(name,actual,expected)
    checks[name]=actual
src=(root/'supplemental.py').read_bytes()
assert hashlib.sha256(src).hexdigest()=='69dac4747856e5f88ac4666e884fe1263777ca5cb64b197741a4b370c093aa4c'
assert hashlib.sha1(b'blob '+str(len(src)).encode()+b'\0'+src).hexdigest()=='ad2edaa92de59f657599190842fa7fe68373b582'
spec=importlib.util.spec_from_file_location('collector',root/'supplemental.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
records=[json.loads(x) for x in (root/'result/supplemental.jsonl').read_text().splitlines()]
assert [r['id'] for r in records]==[c[0] for c in m.READ_CONTRACT]
manifest=dict(l.split('=',1) for l in (root/'run-manifest.txt').read_text().splitlines() if '=' in l)
assert manifest['GATE_SHA']=='a7c14cd9942f8a353d6ea846b2e22ea93ab9ca2e'
assert manifest['SCRIPT_SOURCE_SHA']=='b623afb2fa9fd624e3e1ff418adeb9c71b1074df'
assert manifest['SCRIPT_GIT_BLOB']=='ad2edaa92de59f657599190842fa7fe68373b582'
assert manifest['SCRIPT_SHA256']==hashlib.sha256(src).hexdigest()
assert manifest['HOST']=='node-01' and manifest['CONTEXT']=='kubernetes-admin@pak-portal'
assert manifest['INVENTORY_EXIT_CODE']=='1'
dt=datetime.datetime.fromisoformat
start=dt(manifest['START_UTC']);end=dt(manifest['END_UTC'])+datetime.timedelta(seconds=1)
prev=start;ok=set()
for r,c in zip(records,m.READ_CONTRACT):
    rid,phase,tail,key,deps,shape,name=c
    assert r['phase']==phase
    unmet=[d for d in deps if d not in ok]
    if unmet:
        assert r['category']=='BLOCKED_NOT_EXECUTED' and r['blocked_by']==unmet
        assert r['argv'] is None and r['exit'] is None and r['start'] is None and r['output']==''
    else:
        assert r['argv']==['kubectl','--context',manifest['CONTEXT'],'--request-timeout=15s']+tail
        assert r['exit']==0
        assert prev<=dt(r['start'])<=dt(r['end'])
        json.loads(r['output'])
    assert start<=dt(r['end'])<end
    prev=dt(r['end'])
    if r['category'] is None:ok.add(rid)
counts=collections.Counter(r['category'] or 'OK' for r in records)
assert counts=={'OK':5,'UNSUPPORTED':2,'BLOCKED_NOT_EXECUTED':3}
v=json.loads((root/'version.json').read_text())
assert v['clientVersion']['gitVersion']==v['serverVersion']['gitVersion']=='v1.36.2'
identity=json.loads(records[2]['output'])
try:
    m.verify_calico_identity(identity)
    raise AssertionError('identity unexpectedly accepted')
except m.UnsupportedIdentity as e:
    reason=str(e.reason)
assert reason.startswith('invalid imageID ')
runtime=sorted({c['imageID'] for p in identity for c in p['containers']})
assert runtime==['sha256:6bc9fa4dc2b10ca1d4b97a1cd570036651898cea8b3c3bcbb1d55cf813e43f65']
# Targeted indicators supplement structural/manual review, not a universal secret proof.
payload=(root/'result/supplemental.jsonl').read_text()
patterns=[r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',r'AKIA[0-9A-Z]{16}',r'Bearer\s+[A-Za-z0-9._-]+',r'https?://[^\s/"]+:[^\s/"]+@']
assert not any(re.search(p,payload) for p in patterns)
out={'reviewed_commit':'832591b8735dd8dfef0523cf8e0432d840125468','checksum_matches':checks,
'script_sha256':hashlib.sha256(src).hexdigest(),'records':10,'categories':dict(counts),
'executed_record_argv':7,'blocked_record_argv':3,'manifest_and_versions':'PASS',
'timestamps':'PASS (manifest second precision)','identity_reproduction':reason,
'calico_runtime_image_ids':runtime,'digest_relationship':'UNPROVEN',
'secret_review':'No secret values observed in safe projections; targeted indicators absent; not a universal guarantee',
'live_operations_by_reviewer':0,'one_run_budget':'CONSUMED; no repeat authorized',
'limitations':['repository artifacts do not independently prove absence of other executions','ssh-keyscan alone does not authenticate a host key; prior trust verification not evidenced','credential-file use reported; non-use of previously disclosed credential not independently evidenced']}
print(json.dumps(out,indent=2))
