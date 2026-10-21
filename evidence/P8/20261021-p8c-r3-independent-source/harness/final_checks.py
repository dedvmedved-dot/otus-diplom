import os, sys, json, pathlib, subprocess, datetime, hashlib, re, shutil
root=pathlib.Path('/workspace/scratch/14185c8f871f')
repo=root/'source-work'; portal=repo/'portal'
out=repo/'evidence/P8/20261021-p8c-r3-independent-source'
out.mkdir(parents=True,exist_ok=True)
index=json.loads((root/'final-source-index.json').read_text())
for f in index['files']:
    data=(repo/f['path']).read_bytes()
    actual=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
    assert actual==f['sha'],f['path']
shutil.copy(root/'final-source-index.json',out/'source-index.json')
env=dict(os.environ);env['PATH']=str(root/'toolchain-proof/portal-verified-go/bin')+':'+env['PATH'];env['GOTOOLCHAIN']='local'
results=[]
def run(label,args,cwd=portal,extra=None):
    start=datetime.datetime.now(datetime.timezone.utc).isoformat()
    e=dict(env);e.update(extra or {})
    p=subprocess.run(args,cwd=cwd,env=e,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=600)
    end=datetime.datetime.now(datetime.timezone.utc).isoformat()
    (out/(label+'.txt')).write_text('SOURCE_SHA='+index['sourceSHA']+'\nUTC_START='+start+'\nCWD='+str(cwd)+'\nCOMMAND='+json.dumps(args)+'\n'+p.stdout+'\nEXIT_CODE='+str(p.returncode)+'\nUTC_END='+end+'\n')
    results.append({'check':label,'command':args,'cwd':str(cwd),'start':start,'end':end,'exit':p.returncode})
    (out/'commands.json').write_text(json.dumps(results,indent=2)+'\n')
    print(label+': exit '+str(p.returncode),flush=True)
    if p.returncode:print(p.stdout[-4000:],flush=True)
    return p.returncode
run('01-tool-versions',['bash','-c','go version; node --version; npm --version; python3 --version'])
run('02-mod-verify',['go','mod','verify'])
run('03-build',['go','build','-trimpath','-o',str(root/'final-portal-binary'),'./cmd/portal'],extra={'CGO_ENABLED':'0'})
run('04-vet',['go','vet','./...'])
run('05-unit',['go','test','-count=1','-v','./...'])
run('06-race',['go','test','-race','-count=1','./...'])
run('07-integration-vet',['go','vet','-tags','integration','./internal/store'])
run('08-helpers-portal-cwd',['python3','tools/test_helpers.py','-v'])
run('09-helpers-repo-cwd',['python3','portal/tools/test_helpers.py','-v'],cwd=repo)
run('10-release-checks',['python3','tools/test_release.py','-v'])
run('11-renderer',['node','web/renderer-smoke.test.mjs'])
run('12-fixtures',['node','web/fixture-smoke.test.mjs'])
run('13-collector-api-dom',['bash','tools/test-dataflow.sh'])
run('14-wasm-sql',['python3',str(root/'run_wasm_final.py')],cwd=root)
run('15-workflow-static',['python3',str(root/'static_final.py')],cwd=repo)
run('16-secret-scan',['python3',str(root/'scan_final.py')],cwd=repo)
run('17-pinned-cosign-predicate',['go','run','.', 'predicate.json'],cwd=root/'cosign-check')
run('18-cosign-payload-binding',['python3',str(root/'cosign_binding_final.py')],cwd=root)
for f in index['files']:
    data=(repo/f['path']).read_bytes();assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==f['sha'],f['path']
print('ALL_SOURCE_BYTES_MATCH_CONNECTOR_TREE',flush=True)
sys.exit(1 if any(x['exit'] for x in results) else 0)
