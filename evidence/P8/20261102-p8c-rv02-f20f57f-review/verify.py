"""Source/hash/schema checks against Connector-fetched files; no network/cluster."""
import datetime, hashlib, json, pathlib, platform
import yaml
import followup as f

old=pathlib.Path('../review-3a0afb4')
sha=lambda p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
expected={
 'followup.py':'7456851ef3c1d679b5a9ca1ec666bf3b7c4ee34c7d7ca761757e9185a5621ea9',
 'followup_test.py':'f7ba3d960e39229562c2023a918221c3509dc18837621154b381a14dfe326967',
 'followup-typed-contract.json':'95d76352cb4235820af2684660379ff0436b624e5ebe4d55401f2a3343b3fd6b',
 'supplemental.py':'ddd9a4dc17bca97d6b36ae6b4d501e1722c5d38d6e5ac8c7b051698fa0b15491',
}
hashes={k:sha(k) for k in expected};assert hashes==expected
manifest=old/'calico-v3.32.0.yaml'
assert sha(manifest)=='8d4b2b1bb97a36d7bf196cc84047aafa41fea5152d678a3fe3994604e8ade3c1'
crd=next(d for d in yaml.safe_load_all(manifest.read_text()) if d and d.get('metadata',{}).get('name')=='clusternetworkpolicies.policy.networking.k8s.io')
projected=f.project_crd_schema(json.dumps(crd));assert projected['compatible'] is True
contract=json.loads(pathlib.Path('followup-typed-contract.json').read_text())
prior=json.loads((old/'followup-typed-contract.json').read_text())
assert {k:v for k,v in contract.items() if k!='cnp'}=={k:v for k,v in prior.items() if k!='cnp'}
spec=next(v for v in crd['spec']['versions'] if v['name']=='v1alpha2')['schema']['openAPIV3Schema']['properties']['spec']
assert f.normalize_schema(spec)==f.normalize_schema(contract['cnp']['spec_schema'])
oldhash=hashlib.sha256(f._canonicalize(f.normalize_schema(prior['cnp']['spec_schema'])).encode()).hexdigest()
assert oldhash=='770130a412fd6fab2f02d953edf35f8cc68bf4379db8307e2185937c1e699568'
assert oldhash!=f.CNP_SPEC_SHA256
report={
 'review_head':'f20f57f8da94bf0bed81a29d4323de6887b56b72',
 'actual_parent':'65d4676e363bfe5e60214c29828bfea447a8cebb',
 'generated_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'python':platform.python_version(),'pyyaml':yaml.__version__,
 'hashes':hashes,'schema_projection':projected,'non_cnp_contract_unchanged':True,
 'source_manifest_subtree_match':True,'old_candidate_hash':oldhash,
 'author_suite_independent_runs':[
  {'argv':['python3','followup_test.py'],'exit':0,'tests':116},
  {'argv':['python3','supplemental_test.py'],'exit':0,'tests':36}],
 'reviewer_regression':{'argv':['python3','compatibility_regression_test.py'],'exit':1,
   'methods':4,'passed_methods':2,'failing_methods':2,'failing_cases':7,
   'transcript':'reviewer-regressions.txt'},
 'cluster_calls':0,'source_mutations':0,
 'limits':['Author suites emitted ResourceWarning in test harnesses; no assertion failures.',
           'This timestamp is report generation, not an invented test start timestamp.',
           'Negative fixtures are synthetic and all subprocess calls are mocked.']}
pathlib.Path('verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
