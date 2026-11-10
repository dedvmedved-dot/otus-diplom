import datetime,json,pathlib,subprocess,os,sys,tempfile
r=pathlib.Path(os.environ.get('P8C_REVIEW_ROOT',pathlib.Path.cwd())).resolve();out=pathlib.Path(__file__).resolve().parent
cmds=[]
for name,module,cwd in [('readiness','test_readiness','portal/tools/readiness'),('residual-working','test_architect_residual','portal/tools/readiness'),('qualification','test_release_qualification','portal/tools'),('release','test_release','portal/tools'),('release-negative','test_release_negative','portal/tools'),('route-e2e','test_route_e2e','portal/tools')]:
 cmds.append((name,[sys.executable,'-m','unittest','-v',module],r/cwd))
cmds.append(('qualification-cli',[sys.executable,'release_qualification.py'],r/'portal/tools'))
for name,p in [('regression','evidence/P8/20261105-f783e1e-architect-review/regression_test.py'),('scheduler-working','portal/tools/readiness/test_scheduler_authority_working.py'),('contract-working','portal/tools/readiness/test_contract_authority_working.py'),('completion-working','portal/tools/readiness/test_completion_authority_working.py'),('residual-contract-working','portal/tools/readiness/test_residual_contract_working.py')]:
 cmds.append((name,[sys.executable,p,'-v'],r))
cmds.append(('remaining-17',[sys.executable,'evidence/P8/20261106-e60d1db-architect-review/remaining_contract_test.py','-v'],r))
cmds.append(('residual-12',[sys.executable,'evidence/P8/20261110-c98fea1-architect-review/residual_contract_test.py','-v'],r))
rows=[]
for name,argv,cwd in cmds:
 start=datetime.datetime.now(datetime.timezone.utc).isoformat()
 with tempfile.TemporaryDirectory() as t:
  env={**os.environ,'TMPDIR':t,'P8C_READINESS_BASE':t+'/authority','P8C_REVIEW_ROOT':str(r),'PYTHONPATH':str(out/'network-guard'),'P8C_NETWORK_GUARD_LOG':str(out/'network-attempts.jsonl')}
  p=subprocess.run(argv,cwd=cwd,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=240)
 (out/(name+'.txt')).write_text(p.stdout)
 rows.append({'name':name,'argv':argv,'cwd':str(cwd),'start':start,'end':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exit':p.returncode})
 print(name,p.returncode,flush=True)
(out/'reexecution.json').write_text(json.dumps({'source_sha':'3422e31e97742dd32ad5044451eb062ee5dacf1d','review_head':'935feb3de24116d52fd8c4da7ac963242a82fc07','python':sys.version,'offline_network_guard':True,'commands':rows},indent=2))
(out/'reexecution-raw.txt').write_text('\n'.join('COMMAND '+json.dumps(c)+'\n'+(out/(c['name']+'.txt')).read_text() for c in rows))
