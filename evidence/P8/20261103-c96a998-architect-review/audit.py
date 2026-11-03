import hashlib,json,pathlib,re,subprocess,datetime
p=pathlib.Path(__file__).parent
entries=json.loads((p/'connector-input.json').read_text())
by={e['path']:e for e in entries}
for e in entries:
 b=e['content'].encode(); got=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
 assert got==e['sha'],e['path']
base='evidence/P8/20261103T033300Z-p8c-candidate-and-gates-r3-correction/'
m=json.loads(by[base+'source-manifest.json']['content'])
scan_hashes=dict(line.rsplit(' ',1) for line in by[base+'scan-input-hashes.txt']['content'].splitlines())
paths=[]
for f in m['files']:
 e=by[f['path']]; b=e['content'].encode(); digest=hashlib.sha256(b).hexdigest()
 assert e['sha']==f['blob'] and digest==f['sha256']==scan_hashes[f['path']]
 dst=p/'frozen'/f['path'];dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(b);paths.append(str(dst))
pattern=r'AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{36}|gho_[A-Za-z0-9]{36}|-----BEGIN (RSA|OPENSSH|EC) PRIVATE KEY'
cmd=['grep','-rnE',pattern,*paths]
r=subprocess.run(cmd,capture_output=True,text=True)
assert r.returncode==1 and r.stdout=='' and r.stderr==''
passes=re.findall(r'^\s*--- PASS: (.+?) ',by[base+'raw-transcript.txt']['content'],re.M)
top=sum('/' not in s for s in passes);sub=sum('/' in s for s in passes)
assert (top,sub)==(3,97)
result={'reviewed_sha':'c96a9988ef68be5ecfd7e8e65f39e40b14193ba9','audit_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'connector_blob_checks':len(entries),'source_manifest_and_frozen_hashes':'MATCH','author_go_transcript':{'functions':top,'subtests':sub,'independently_run':False},'independent_scan':{'command_argv':cmd,'version':subprocess.run(['grep','--version'],capture_output=True,text=True).stdout.splitlines()[0],'exit':r.returncode,'stdout_bytes':0,'stderr_bytes':0,'limit':'Four listed files, exact supplied heuristic only; does not scan all evidence or prove absence of every secret.'},'go_regression':'SUPPLIED_SOURCE_NOT_EXECUTED_GO_UNAVAILABLE'}
(p/'audit-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
