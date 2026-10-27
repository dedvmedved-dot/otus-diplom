import ast,copy,hashlib,importlib.util,json,pathlib,sys
r=pathlib.Path(__file__).parent
sp=importlib.util.spec_from_file_location('t',r/'supplemental_test.py')
t=importlib.util.module_from_spec(sp);sp.loader.exec_module(t);m=t.inv
rows=[json.loads(l) for l in (r/'live.jsonl').read_text().splitlines()]
pods=json.loads(next(x for x in rows if x['id']=='I1')['output'])
assert m.verify_calico_identity(pods)==3
index=m.PINNED_DIGEST;config=m.AMD64_CONFIG_DIGEST
positive=[config]+[s+'://'+index for s in ['containerd','docker-pullable','docker']]
negative=[index,'sha256:'+'b'*64]+[s+'://'+config for s in ['containerd','docker-pullable','docker']]
negative += [config+'\n','x'+config,config+'x','containerd://'+index+'\n','xcontainerd://'+index]
results=[]
for ref in sorted(m.CALICO_IMAGE_REFS):
 for iid in positive+negative:
  p=copy.deepcopy(t.POD);p['spec']['containers'][0]['image']=ref
  p['status']['containerStatuses'][0]['imageID']=iid
  rc,calls,out=t.run({'I1':t.R(0,t.enc(p))})
  allowed=iid in positive
  assert (rc==0)==allowed
  assert all((x in calls)==allowed for x in ['C3','C4','C5'])
  results.append({'ref':ref,'imageID':iid,'accepted':allowed})
# Lift only existing safe projected identities into mock API shape.
raw=[]
for p in pods:
 cs=p['containers'];raw.append({'apiVersion':'v1','kind':'Pod','metadata':p['metadata'],
 'spec':{'containers':[{'name':c['name'],'image':c['image']} for c in cs]},
 'status':{'containerStatuses':[{'name':c['name'],'imageID':c['imageID']} for c in cs]}})
rc,calls,_=t.run({'I1':t.R(0,json.dumps({'items':raw}))})
assert rc==0 and all(x in calls for x in ['C3','C4','C5'])
bad=copy.deepcopy(raw);bad[1]['status']['containerStatuses'][0]['imageID']='sha256:'+'b'*64
rc,calls,_=t.run({'I1':t.R(0,json.dumps({'items':bad}))})
assert rc!=0 and not any(x in calls for x in ['C3','C4','C5'])
old=ast.parse((r/'old.py').read_text());new=ast.parse((r/'supplemental.py').read_text())
def defs(tree):return {n.name:ast.dump(n,include_attributes=False) for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
a,b=defs(old),defs(new)
changed=sorted(k for k in a if a[k]!=b.get(k))
assert changed==['verify_calico_identity']
assert sorted(set(b)-set(a))==['_image_id_ok']
def contract(tree):
 return next(ast.dump(n.value,include_attributes=False) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='READ_CONTRACT' for t in n.targets))
assert contract(old)==contract(new)
hashes={}
for f in ['supplemental.py','supplemental_test.py']:
 data=(r/f).read_bytes();hashes[f]={'sha256':hashlib.sha256(data).hexdigest(),'git_blob':hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()}
print(json.dumps({'source_sha':'3139e08e4243868d5de2aa9f52d054e424e0a653','reviewed_sha':'bcda2f78e20a5f83a05f021c5bb4726202f6ca0e','hashes':hashes,'stored_three_pod_pure_validation':'PASS','three_pod_mock_main':'PASS','mixed_mock_zero_dependents':'PASS','finite_cases':results,'existing_changed_functions':changed,'new_functions':['_image_id_ok'],'read_contract_and_other_definitions':'UNCHANGED','cluster_operations':0},indent=2))
