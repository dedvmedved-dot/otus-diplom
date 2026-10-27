import hashlib,json,pathlib,yaml
r=pathlib.Path(__file__).parent
def strip(d):
 if isinstance(d,dict):return {k:strip(v) for k,v in d.items() if k!='description'}
 if isinstance(d,list):return [strip(v) for v in d]
 return d
def canon(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')
cnp=yaml.safe_load((r/'cnp.yaml').read_text())
def schema(crd,version):
 v=next(v for v in crd['spec']['versions'] if v['name']==version)
 return strip(v['schema']['openAPIV3Schema']['properties']['spec'])
out={}
s=schema(cnp,'v1alpha2')
out['cnp']={'source_repository':'kubernetes-sigs/network-policy-api','source_commit':'730bd5474d82a2cf82be8b0c6c2a5515598cc44e','source_blob':'eca1eca97c14f56836aaf8f2394fa03479e01b5f','group':'policy.networking.k8s.io','version':'v1alpha2','kind':'ClusterNetworkPolicy','scope':'Cluster','spec_schema':s,'canonical_spec_schema_sha256':hashlib.sha256(canon(s)).hexdigest()}
for d in yaml.safe_load_all((r/'calico.yaml').read_text()):
 if not d or d.get('kind')!='CustomResourceDefinition':continue
 key={'hostendpoints.crd.projectcalico.org':'hep','tiers.crd.projectcalico.org':'tier'}.get(d['metadata']['name'])
 if key:
  s=schema(d,'v1')
  out[key]={'source_repository':'dedvmedved-dot/otus-diplom','source_commit':'bcda2f78e20a5f83a05f021c5bb4726202f6ca0e','source_path':'ansible/playbooks/files/calico-v3.32.0.yaml','source_blob':'21ea9b4b163305ea479bc7708965104465ffc716','group':d['spec']['group'],'version':'v1','kind':d['spec']['names']['kind'],'scope':d['spec']['scope'],'spec_schema':s,'canonical_spec_schema_sha256':hashlib.sha256(canon(s)).hexdigest()}
assert out['hep']['scope']=='Cluster'
assert out['tier']['spec_schema']['properties']['defaultAction']['default']=='Deny'
assert out['tier']['spec_schema']['properties']['defaultAction']['allOf'][1]['enum']==['Pass','Deny']
assert 'ports' in out['hep']['spec_schema']['properties']
cnps=out['cnp']['spec_schema']
assert cnps['properties']['ingress']['items']['properties']['from']['items']['properties'].keys()=={'namespaces','pods'}
assert cnps['properties']['egress']['items']['properties']['to']['items']['properties'].keys()=={'namespaces','pods','networks'}
(r/'typed-contract.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:{'kind':v['kind'],'scope':v['scope'],'canonical_spec_schema_sha256':v['canonical_spec_schema_sha256']} for k,v in out.items()},indent=2))
