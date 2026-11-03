import hashlib, json, pathlib, re
root = pathlib.Path(__file__).parent
entries = json.loads((root / 'connector-input.json').read_text())
by_path = {e['path']:e for e in entries}
manifest = []
for e in entries:
    raw = e['content'].encode()
    blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
    assert blob == e['sha'], (e['path'], blob, e['sha'])
    manifest.append({'path':e['path'], 'git_blob':blob, 'sha256':hashlib.sha256(raw).hexdigest()})
base='evidence/P8/20261103T033000Z-p8c-candidate-and-gates-r2-residual/'
scan=by_path[base+'secret-scan.txt']['content']
assert 'grep_exit=2' in scan and 'input file is also the output' in scan
transcript=by_path[base+'raw-transcript.txt']['content']
passes=re.findall(r'^\s*--- PASS: (.+?) ', transcript, re.M)
top=[x for x in passes if '/' not in x]
sub=[x for x in passes if '/' in x]
assert (len(top),len(sub)) == (3,91)
go=by_path['portal/networkpolicy/flows_test.go']['content']
start=go.index('func validateStructure(')
end=go.index('func TestCandidatePolicyStructure(',start)
guard=go[start:end]
ing=guard[guard.index('for _, ing := range p.Spec.Ingress'):]
assert 'len(ing.From) == 0' in ing and 'ing.Ports' not in ing
assert 'p.Spec.PodSelector' not in guard
draft=by_path['docs/architecture/P8C_DEPLOYMENT_GATE_DRAFT_20261102.md']['content']
assert 'любые namespace вне portal+velero' in draft
rbac=by_path['portal/manifests/rbac.yaml']['content']
assert 'kind: ClusterRoleBinding' in rbac
result={'reviewed_sha':'dfb9130a4c1b2ba9278d1feda234cd7e444f6611', 'connector_blob_checks':'PASS', 'author_transcript':{'top_level_pass':len(top),'subtest_pass':len(sub),'independently_executed':False}, 'secret_scan_actual':'ERROR_EXIT_2_NOT_CLEAN', 'static_guard_findings':['no ingress port validation','no target PodSelector validation'], 'limits':'Static source/evidence audit, not Go execution, not runtime CNI validation, not a new secret scan.', 'sources':manifest}
(root/'audit-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
