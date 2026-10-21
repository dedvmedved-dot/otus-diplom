import subprocess,os,pathlib,sys
root=pathlib.Path(__file__).parent
server=subprocess.Popen(['node',str(root/'pg-wasm-check/server.mjs')],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
try:
    for line in server.stdout:
        print(line,end='',flush=True)
        if 'ISOLATED_WASM_POSTGRES_READY' in line:break
    else:raise RuntimeError('isolated SQL engine did not start')
    env=dict(os.environ);env['TEST_DATABASE_URL']='postgres://postgres@127.0.0.1:55432/postgres?sslmode=disable&default_query_exec_mode=exec&pool_max_conns=1';env['PORTAL_TEST_PGLITE_COMPAT']='1'
    print('COMPATIBILITY_ONLY: WASM PostgreSQL; exec query mode; loopback no TLS; native PG/TLS qualification NOT_EXECUTED',flush=True)
    p=subprocess.run(['go','test','-tags','integration','-count=1','-v','./internal/store'],cwd=root/'source-work/portal',env=env,timeout=240)
    code=p.returncode
finally:
    server.terminate()
    try:server.wait(timeout=10)
    except subprocess.TimeoutExpired:server.kill();server.wait()
sys.exit(code)
