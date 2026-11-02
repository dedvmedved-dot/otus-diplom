"""Independent acceptance checks. Local inputs, synthetic fixtures, mocked kubectl."""
import copy, datetime, hashlib, json, pathlib, platform, sys
import yaml

root=pathlib.Path(__file__).resolve().parent
code=root/'repo/portal/networkpolicy'
sys.path.insert(0,str(code))
import followup as f
import followup_test as t
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
expected={'followup.py':'fc78d03af06f60bbcdde967810ee65a28f37df96a0d85a003807f097fa179e2b',
          'followup_test.py':'c912db861c7dd5b0b8c8b89f4f905e61251585fa258c36d872c9ad7a4d23325c',
          'supplemental.py':'ddd9a4dc17bca97d6b36ae6b4d501e1722c5d38d6e5ac8c7b051698fa0b15491',
          'followup-typed-contract.json':'95d76352cb4235820af2684660379ff0436b624e5ebe4d55401f2a3343b3fd6b'}
hashes={n:sha(code/n) for n in expected};assert hashes==expected
start=datetime.datetime.now(datetime.timezone.utc).isoformat()
observations=[]
for label,value,present,good in [('absent',None,False,True),('empty','',True,True),
 ('null',None,True,False),('false',False,True,False),('true',True,True,False),
 ('zero',0,True,False),('number',3,True,False),('array',[],True,False),
 ('object',{},True,False),('token','SYNTHETIC_SECRET_CANARY',True,False)]:
    p=json.loads(t.podlist([t.POD_CFG]))
    if present:p['metadata']['continue']=value
    rc,calls,rows=t.run({'F-I1':t.R(0,json.dumps(p))})
    r=t.by_id(rows)['F-I1'];n=sum(i in {'F-NP','F-GNP','F-FELIX','F-HEP','F-TIER'} for i,_ in calls)
    assert (rc,r['category'],r['complete'],n)==((0,None,True,5) if good else (1,'PARSE_ERROR',False,0))
    if not good:assert r['output']=='' and r['diag']=='COMPLETENESS'
    assert 'SYNTHETIC_SECRET_CANARY' not in json.dumps(rows)
    observations.append({'case':'continue_'+label,'pass':True,'category':r['category'],'dependents':n})
cidrs=[('10.0.0.5/24',True),('2001:db8::5/64',True),('0.0.0.0/0',True),('::/0',True),
 ('255.255.255.255/32',True),('ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff/128',True),
 ('10.0.0.1/33',False),('::1/129',False),('10.0.0.1/+24',False),('10.0.0.1/-1',False),
 ('10.0.0.1/٢٤',False),('010.0.0.1/24',False),('10.0.0.1/255.255.255.0',False),
 ('10.0.0.1/0.0.0.255',False),('fe80::1%eth0/64',False),('::ffff:192.0.2.1/128',False),
 ('10.0.0.1/024',False),('2001:0db8:0000:0000:0000:0000:192.168.100.100/128',False)]
assert len(cidrs[5][0])==43
for value,good in cidrs:
    obj=copy.deepcopy(t.CNP);obj['spec']['egress'][0]['to']=[{'networks':[value]}]
    rc,calls,rows=t.run({'F-CNP':t.R(0,t.page('F-CNP',[obj]))});r=t.by_id(rows)['F-CNP']
    assert (rc,r['category'],r['complete'])==((0,None,True) if good else (1,'PARSE_ERROR',False))
    if good:assert json.loads(r['output'])[0]['spec']['egress'][0]['to'][0]['networks']==[value]
    else:assert r['output']==''
    observations.append({'case':'cidr_'+value,'pass':True,'category':r['category']})
manifest=root/'repo/ansible/playbooks/files/calico-v3.32.0.yaml'
assert sha(manifest)=='8d4b2b1bb97a36d7bf196cc84047aafa41fea5152d678a3fe3994604e8ade3c1'
crd=next(d for d in yaml.safe_load_all(manifest.read_text()) if d and d.get('metadata',{}).get('name')=='clusternetworkpolicies.policy.networking.k8s.io')
assert f.project_crd_schema(json.dumps(crd))['compatible']
contract=json.loads((code/'followup-typed-contract.json').read_text())
subtree=next(v for v in crd['spec']['versions'] if v['name']=='v1alpha2')['schema']['openAPIV3Schema']['properties']['spec']
assert f.normalize_schema(subtree)==f.normalize_schema(contract['cnp']['spec_schema'])
old=json.loads((root.parent/'review-3a0afb4/followup-typed-contract.json').read_text())
oldhash=hashlib.sha256(f._canonicalize(f.normalize_schema(old['cnp']['spec_schema'])).encode()).hexdigest()
assert oldhash=='770130a412fd6fab2f02d953edf35f8cc68bf4379db8307e2185937c1e699568' and oldhash!=f.CNP_SPEC_SHA256
report={'review_head':'fdfc776570c7f44e559eefcd092e2ca58595ee48','actual_parent':'c1644950c618f7ca7221a9500dc3049363d7bfee',
        'start_utc':start,'end_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'python':platform.python_version(),'pyyaml':yaml.__version__,'hashes':hashes,
        'observations':observations,'all_pass':True,'manifest_schema_match':True,'old_candidate_hash':oldhash,
        'live_calls':0,'fixture_type':'SYNTHETIC; subprocess.run mocked by harness'}
(root/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'cases':len(observations),'all_pass':True,'manifest_match':True,'old_candidate_mismatch':True}))
