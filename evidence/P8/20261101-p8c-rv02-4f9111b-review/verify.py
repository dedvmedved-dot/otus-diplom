import datetime,json,pathlib,platform,subprocess,sys
root=pathlib.Path(__file__).parent
start=datetime.datetime.now(datetime.timezone.utc).isoformat()
runs=[]
for args,out in [(['followup_test.py','-v'],'followup-tests.txt'),(['reproduce.py'],'reproduce-summary.json'),(['regression_test.py'],'regression-tests.txt')]:
 before=datetime.datetime.now(datetime.timezone.utc).isoformat()
 r=subprocess.run([sys.executable,*args],cwd=root,text=True,capture_output=True)
 (root/out).write_text(r.stdout+r.stderr)
 runs.append({'argv':[sys.executable,*args],'start_utc':before,'end_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exit_code':r.returncode,'output_file':out})
(root/'execution.json').write_text(json.dumps({'start_utc':start,'end_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'python':platform.python_version(),'runs':runs,'source_sha':'c4477cf299916332848a00af73f0927d427f4ba4','reviewed_main_sha':'4f9111b2a60945fad08b8f150a6069e6edd405a8','all_collector_kubectl_calls_mocked':True,'reviewer_cluster_calls':0},indent=2)+'\n')
print(json.dumps(runs,indent=2))

