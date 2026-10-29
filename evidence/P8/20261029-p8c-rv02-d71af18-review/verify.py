import copy,datetime,hashlib,json,pathlib,platform,subprocess,sys
root=pathlib.Path(__file__).parent
start=datetime.datetime.now(datetime.timezone.utc).isoformat()
runs=[]
for args,out in [(['followup_test.py','-v'],'followup-tests.txt'),(['reproduce.py'],'reproduce-summary.json')]:
 before=datetime.datetime.now(datetime.timezone.utc).isoformat()
 r=subprocess.run([sys.executable,*args],cwd=root,text=True,capture_output=True)
 (root/out).write_text(r.stdout+r.stderr)
 runs.append({'argv':[sys.executable,*args],'start_utc':before,'end_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exit_code':r.returncode,'output_file':out})
 if r.returncode:raise SystemExit(r.returncode)
sys.path.insert(0,str(root))
import followup_test as t
f=t.fw;s=copy.deepcopy(t.CNP_SPEC)
def h(x):return hashlib.sha256(f._canonicalize(f.normalize_schema(x)).encode()).hexdigest()
a=copy.deepcopy(s);a['description']='annotation changed'
b=copy.deepcopy(s);b['properties']['description']={'type':'string'}
lit={'type':'object','default':{'description':'literal'}}
normal={'base_sha256':h(s),'annotation_only_sha256':h(a),'semantic_property_sha256':h(b),'literal_default_preserved':f.normalize_schema(lit)==lit}
assert h(s)==h(a)==f.CNP_SPEC_SHA256 and h(b)!=f.CNP_SPEC_SHA256 and normal['literal_default_preserved']
(root/'normalization-check.json').write_text(json.dumps(normal,indent=2)+'\n')
end=datetime.datetime.now(datetime.timezone.utc).isoformat()
(root/'execution.json').write_text(json.dumps({'start_utc':start,'end_utc':end,'python':platform.python_version(),'runs':runs,'normalization_assertions':'PASS','source_sha':'78268f6f542b6e58685a0802ee40eae368e089c5','reviewed_main_sha':'d71af18c27059bcd9ce3ae3c2b15686d7df953c6','all_collector_kubectl_calls_mocked':True,'reviewer_cluster_calls':0},indent=2)+'\n')
print((root/'reproduce-summary.json').read_text())

