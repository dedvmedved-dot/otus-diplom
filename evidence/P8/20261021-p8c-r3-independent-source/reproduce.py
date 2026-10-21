#!/usr/bin/env python3
"""Source checks only. No workflow, credentials, cluster or production access.
Prerequisites: verified Go1.27.3 on PATH; npm ci --ignore-scripts in portal.
Optional --wasm-compat needs npm ci --ignore-scripts in evidence/wasm-sql.
Optional --native-pg needs a disposable loopback PG17 portal_test database and
TEST_DATABASE_URL supplied locally. That value is never logged by this runner.
"""
import argparse, pathlib, os, sys, subprocess, hashlib, json, tempfile

here=pathlib.Path(__file__).resolve().parent
parser=argparse.ArgumentParser()
parser.add_argument('--repo',type=pathlib.Path,default=here.parents[2])
group=parser.add_mutually_exclusive_group()
group.add_argument('--wasm-compat',action='store_true')
group.add_argument('--native-pg',action='store_true')
a=parser.parse_args();repo=a.repo.resolve();portal=repo/'portal'
env=dict(os.environ);env['GOTOOLCHAIN']='local'
for item in json.loads((here/'source-index.json').read_text())['files']:
    data=(repo/item['path']).read_bytes()
    assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==item['sha'],item['path']
def run(args,cwd=portal,overrides=None):
    print('COMMAND='+json.dumps(args)+' CWD='+str(cwd),flush=True)
    e=dict(env);e.update(overrides or {})
    result=subprocess.run(args,cwd=cwd,env=e,timeout=600)
    print('EXIT_CODE='+str(result.returncode),flush=True)
    if result.returncode:raise SystemExit(result.returncode)
version=subprocess.check_output(['go','env','GOVERSION'],env=env,text=True).strip()
assert version=='go1.27.3',version
run(['go','mod','verify'])
with tempfile.TemporaryDirectory(prefix='portal-source-build-') as tmp:
    run(['go','build','-trimpath','-o',str(pathlib.Path(tmp)/'portal'),'./cmd/portal'],overrides={'CGO_ENABLED':'0'})
for args in [['go','vet','./...'],['go','test','-count=1','-v','./...'],['go','test','-race','-count=1','./...'],['python3','tools/test_helpers.py','-v'],['python3','tools/test_release.py','-v'],['node','web/renderer-smoke.test.mjs'],['node','web/fixture-smoke.test.mjs'],['bash','tools/test-dataflow.sh']]:run(args)
run(['python3','portal/tools/test_helpers.py','-v'],cwd=repo)
if a.native_pg:
    if not env.get('TEST_DATABASE_URL'):raise SystemExit('TEST_DATABASE_URL required locally; never use production')
    run(['go','test','-tags','integration','-count=1','-v','./internal/store'])
elif a.wasm_compat:
    server=subprocess.Popen(['node','server.mjs'],cwd=here/'wasm-sql',stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    try:
        for line in server.stdout:
            print(line,end='',flush=True)
            if 'ISOLATED_WASM_POSTGRES_READY' in line:break
        else:raise SystemExit('isolated compatibility engine failed to start')
        print('WASM SQL compatibility only; native PG/TLS/runtime NOT_EXECUTED',flush=True)
        run(['go','test','-tags','integration','-count=1','-v','./internal/store'],overrides={'TEST_DATABASE_URL':'postgres://postgres@127.0.0.1:55432/postgres?sslmode=disable&default_query_exec_mode=exec&pool_max_conns=1','PORTAL_TEST_PGLITE_COMPAT':'1'})
    finally:
        server.terminate()
        try:server.wait(timeout=10)
        except subprocess.TimeoutExpired:server.kill();server.wait()
else:print('SQL integration NOT_EXECUTED: select an explicit isolated test backend')
print('Source checks complete; no Architect acceptance or runtime/release result implied.')
