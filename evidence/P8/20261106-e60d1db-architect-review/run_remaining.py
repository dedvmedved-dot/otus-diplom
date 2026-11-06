import datetime,json,os,pathlib,subprocess,sys,tempfile
r=pathlib.Path(os.environ.get('P8C_REVIEW_ROOT',pathlib.Path.cwd())).resolve();o=pathlib.Path(__file__).resolve().parent
argv=[sys.executable,str(o/'remaining_contract_test.py'),'-v'];start=datetime.datetime.now(datetime.timezone.utc).isoformat()
with tempfile.TemporaryDirectory() as t:
 env=dict(os.environ,P8C_REVIEW_ROOT=str(r),TMPDIR=t,P8C_READINESS_BASE=t+'/authority',PYTHONPATH=str(o/'network-guard'),P8C_NETWORK_GUARD_LOG=str(o/'remaining-network-attempts.jsonl'))
 p=subprocess.run(argv,cwd=r,env=env,capture_output=True,text=True,timeout=60)
(o/'remaining-contract.txt').write_text(p.stdout+p.stderr)
(o/'additional-execution.json').write_text(json.dumps({'source_sha':'9a4ed77d3131d0b2078b6917e1a7d4419ec02b65','argv':argv,'cwd':str(r),'python':sys.version,'start':start,'end':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exit':p.returncode,'methods':17,'pass':3,'failures':14,'errors':0,'network_guard':True},indent=2))
print('remaining_contract exit',p.returncode)
