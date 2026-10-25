import importlib.util,json,pathlib,tempfile,types,unittest.mock as mock,hashlib
root=pathlib.Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('inventory',root/'inventory.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
canary='SYNTHETIC_REVIEW_CANARY_NOT_A_CREDENTIAL'
payload={'metadata':{'name':'fixture'},'spec':{'unneededField':canary,'endpoint':'https://user:'+canary+'@example.invalid/?token='+canary},'status':{'message':canary}}
findings={'sourceBlob':hashlib.sha1(b'blob '+str(len((root/'inventory.py').read_bytes())).encode()+b'\0'+(root/'inventory.py').read_bytes()).hexdigest(),'projection_preserves_unallowlisted_fields':canary in json.dumps(m.project(payload))}
with tempfile.TemporaryDirectory() as tmp:
 output=pathlib.Path(tmp)/'out'
 malformed='not-json '+canary
 def fake(argv,**kw):return types.SimpleNamespace(returncode=0,stdout=malformed if '-o' in argv and 'json' in argv else '',stderr='')
 with mock.patch.object(m.shutil,'which',return_value='/synthetic/kubectl'),mock.patch.object(m.subprocess,'run',side_effect=fake),mock.patch.object(m.sys,'argv',['inventory.py','--context','fixture','--output',str(output)]):code=m.main()
 rows=[json.loads(x) for x in (output/'inventory.jsonl').read_text().splitlines()]
 findings['invalid_json_exit']=code
 findings['invalid_json_raw_preserved']=any(canary in r['output'] and r['category'] is None for r in rows)
 discovery=next(r for r in rows if '/apis/monitoring.coreos.com/v1' in r['argv'])
 findings['actual_command_has_raw']=any('--raw' in c for c in m.COMMANDS)
 findings['logged_discovery_command_has_raw']='--raw' in discovery['argv']
print(json.dumps(findings,indent=2))
