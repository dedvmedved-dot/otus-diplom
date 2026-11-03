import copy,datetime,hashlib,json,pathlib,re,subprocess,yaml
p=pathlib.Path(__file__).parent
entries=json.loads((p/'connector-input.json').read_text())
by={e['path']:e for e in entries}
for e in entries:
 b=e['content'].encode()
 assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==e['sha'],e['path']
root='evidence/P8/20261103T094000Z-p8c-candidate-and-gates-r4-finalization/'
m=json.loads(by[root+'source-manifest.json']['content'])
scan_hashes=dict(line.rsplit(' ',1) for line in by[root+'scan-input-hashes.txt']['content'].splitlines())
paths=[]
for f in m['files']:
 e=by[f['path']]; b=e['content'].encode()
 assert e['sha']==f['blob'] and hashlib.sha256(b).hexdigest()==f['sha256']==scan_hashes[f['path']]
 dst=p/'frozen'/f['path'];dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(b);paths.append(str(dst))
fixture_path='portal/networkpolicy/testdata/accepted-policy-contract.json'
review_root='evidence/P8/20261103-c96a998-architect-review/'
assert by[fixture_path]['content']==by[review_root+'accepted-policy-contract.json']['content']
assert by['portal/networkpolicy/reviewer_exact_rule_regression_test.go']['content']==by[review_root+'exact_rule_regression_test.go']['content']
candidate=[x for x in yaml.safe_load_all(by['portal/manifests/networkpolicy.yaml']['content']) if x]
expected=json.loads(by[fixture_path]['content'])['objects']
assert candidate==expected and len(expected)==6
assert by['portal/manifests/networkpolicy.yaml']['sha']=='15f0b3245586bf5086e5a24ed02b0460121f7712'
# Mirror the inspected Go mutation predicate, then prove only DNS PodSelector removals occurred.
w=copy.deepcopy(candidate); touched=[]
for i,obj in enumerate(w):
 for j,rule in enumerate(obj['spec'].get('egress',[])):
  for k,peer in enumerate(rule.get('to',[])):
   if peer.get('namespaceSelector',{}).get('matchLabels',{}).get('kubernetes.io/metadata.name')=='kube-system' and peer.get('podSelector',{}).get('matchLabels',{}).get('k8s-app')=='kube-dns':
    del peer['podSelector']; touched.append((i,j,k))
assert len(touched)==5
restored=copy.deepcopy(w)
for i,j,k in touched: restored[i]['spec']['egress'][j]['to'][k]['podSelector']=copy.deepcopy(candidate[i]['spec']['egress'][j]['to'][k]['podSelector'])
assert restored==candidate
passes=re.findall(r'^\s*--- PASS: (.+?) ',by[root+'raw-transcript.txt']['content'],re.M)
assert (sum('/' not in x for x in passes),sum('/' in x for x in passes))==(4,107)
assert sum(x.startswith('TestReviewerExactRuleContract/') for x in passes)==10
pat=r'AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{36}|gho_[A-Za-z0-9]{36}|-----BEGIN (RSA|OPENSSH|EC) PRIVATE KEY'
cmd=['grep','-rnE',pat,*paths];scan=subprocess.run(cmd,capture_output=True,text=True)
assert scan.returncode==1 and not scan.stdout and not scan.stderr
result={'reviewed_sha':'4a55a7ec799243e0804b12c939dd2dd29c2366f0','audit_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'connector_blob_checks':len(entries),'source_manifest_hashes':'6/6 MATCH','fixture_byte_identical':True,'reviewer_regression_byte_identical':True,'candidate_contract_exact_objects':6,'dns_mutation_only_expected_fields':len(touched),'author_go_transcript':{'top_level_pass':4,'subtest_pass':107,'reviewer_cases':10,'independently_executed_go':False},'independent_scan':{'command_argv':cmd,'scanner':subprocess.run(['grep','--version'],capture_output=True,text=True).stdout.splitlines()[0],'exit':scan.returncode,'stdout_bytes':0,'stderr_bytes':0,'scope':'6 manifest-listed source/draft/fixture files','limits':'Same narrow heuristic only; not all evidence, not proof of absence of every secret form.'},'limits':'Python source/artifact verification; not Go re-execution, not runtime CNI or WAL test.'}
(p/'audit-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
