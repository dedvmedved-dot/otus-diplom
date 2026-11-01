import datetime,json,pathlib,platform,subprocess,sys
root=pathlib.Path(__file__).parent
start=datetime.datetime.now(datetime.timezone.utc).isoformat()
runs=[]
for args,out in [(['followup_test.py','-v'],'followup-tests.txt'),(['reproduce.py'],'reproduce-summary.json'),(['regression_test.py'],'regression-tests.txt'),(['bounded_projection_test.py'],'bounded-projection-tests.txt')]:
 before=datetime.datetime.now(datetime.timezone.utc).isoformat()
 r=subprocess.run([sys.executable,*args],cwd=root,text=True,capture_output=True)
 (root/out).write_text(r.stdout+r.stderr)
 runs.append({'argv':[sys.executable,*args],'start_utc':before,'end_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exit_code':r.returncode,'output_file':out})
(root/'execution.json').write_text(json.dumps({'start_utc':start,'end_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'python':platform.python_version(),'runs':runs,'source_sha':'164b29760c1ef8227de4230083ae9a11d5598e92','reviewed_main_sha':'85ae7794c106cccfd5a01f46632ab1865558f07a','all_collector_kubectl_calls_mocked':True,'reviewer_cluster_calls':0},indent=2)+'\n')
print(json.dumps(runs,indent=2))

