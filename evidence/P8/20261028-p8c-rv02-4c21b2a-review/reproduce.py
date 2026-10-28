import copy,hashlib,json,pathlib,sys,tempfile,contextlib,io,subprocess,shutil,platform
from unittest import mock
root=pathlib.Path(__file__).parent
sys.path.insert(0,str(root))
import followup_test as t
f=t.fw
K={'F-CNP':('ClusterNetworkPolicyList','policy.networking.k8s.io/v1alpha2'),
'F-NP':('NetworkPolicyList','crd.projectcalico.org/v1'),'F-GNP':('GlobalNetworkPolicyList','crd.projectcalico.org/v1'),
'F-HEP':('HostEndpointList','crd.projectcalico.org/v1'),'F-TIER':('TierList','crd.projectcalico.org/v1')}
def page(rid,items,token=None,rv='rv1'):
 k,a=K[rid];m={'resourceVersion':rv}
 if token is not None:m['continue']=token
 return json.dumps({'apiVersion':a,'kind':k,'metadata':m,'items':items})
def run(overrides=None,ctx=f.CTX):
 defaults={'F-D1':t.R(0,json.dumps(t.CALICO_DISC)),'F-I1':t.R(0,t.podlist([t.POD])),
 'F-CS':t.R(0,json.dumps(t.CRD)),'F-FELIX':t.R(0,json.dumps(t.FELIX))}
 for rid,obj in [('F-CNP',t.CNP),('F-NP',t.NP),('F-GNP',t.GNP),('F-HEP',t.HEP),('F-TIER',t.TIER)]:
  defaults[rid]=[t.R(0,page(rid,[obj]))]
 defaults.update(overrides or {});calls=[];indices={};rc=None;crash=None
 with tempfile.TemporaryDirectory() as td:
  out=pathlib.Path(td)/'out'
  def fake(argv,**kw):
   rid=t.CMDS[t.route(tuple(argv[4:]))];calls.append((rid,list(argv)))
   ans=defaults[rid]
   if isinstance(ans,list):
    i=indices.get(rid,0);indices[rid]=i+1;ans=ans[min(i,len(ans)-1)]
   if isinstance(ans,BaseException):raise ans
   return ans
  with mock.patch.object(shutil,'which',return_value='/mock/kubectl'),mock.patch.object(subprocess,'run',side_effect=fake),mock.patch.object(f.sys,'argv',['followup.py','--context',ctx,'--output',str(out)]):
   try:rc=f.main()
   except BaseException as e:crash=type(e).__name__
  p=out/f.OUTPUT_FILE
  rows=[json.loads(l) for l in p.read_text().splitlines()] if p.exists() else []
 return rc,calls,rows,crash
def case(label,overrides=None,target='F-CNP',ctx=f.CTX):
 rc,calls,rows,crash=run(overrides,ctx)
 row=next((x for x in rows if x['id']==target),None)
 out={'rc':rc,'crash':crash,'row_count':len(rows),'calls':len(calls)}
 if row:
  out.update({k:row.get(k) for k in ['category','exit','complete','reason']})
  s=row.get('output','')
  try:d=json.loads(s) if s else None
  except Exception:d='NOT_JSON'
  out['output_count']=len(d) if isinstance(d,list) else None
  out['output_sample']=d[:1] if isinstance(d,list) else d
 results[label]=out
 return rc,calls,rows,crash
results={}
case('valid_baseline')
rc,calls,rows,crash=case('context_mismatch',ctx='another-context',target='F-NP')
results['context_mismatch']['actual_contexts']=sorted(set(c[1][2] for c in calls))
results['context_mismatch']['logged_context']=next(x for x in rows if x['id']=='F-NP')['argv'][2]
def objects(obj,n):
 out=[]
 for i in range(n):
  x=copy.deepcopy(obj);x['metadata']['name']='x-'+str(i);out.append(x)
 return out
for rid,obj in [('F-CNP',t.CNP),('F-NP',t.NP),('F-GNP',t.GNP),('F-HEP',t.HEP),('F-TIER',t.TIER)]:
 case('oversized_'+rid,{rid:t.R(0,page(rid,objects(obj,501)))},rid)
case('three_pages_600_last_without_continue',{'F-NP':[t.R(0,page('F-NP',objects(t.NP,200),tok)) for tok in ['a','b',None]]},'F-NP')
for label,body in [
 ('wrong_list_kind',{'apiVersion':'v1','kind':'SecretList','metadata':{'resourceVersion':'r'},'items':[]}),
 ('missing_list_metadata',{'apiVersion':'crd.projectcalico.org/v1','kind':'NetworkPolicyList','items':[]}),
 ('false_metadata',{'apiVersion':'crd.projectcalico.org/v1','kind':'NetworkPolicyList','metadata':False,'items':[]}),
 ('false_continue',{'metadata':{'continue':False,'resourceVersion':'r'},'items':[]}),
 ('null_rv',{'metadata':{'resourceVersion':None},'items':[]}),
 ('scalar_item',{'metadata':{'resourceVersion':'r'},'items':[None]})
]:
 case(label,{'F-NP':t.R(0,json.dumps(body))},'F-NP')
for label,stderr in [('forbidden','forbidden'),('not_served',"the server doesn't have a resource type"),('connection','connection refused')]:
 case('first_page_'+label,{'F-NP':t.R(1,'',stderr)},'F-NP')
case('first_page_timeout',{'F-NP':subprocess.TimeoutExpired('kubectl',20)},'F-NP')
case('later_page_timeout',{'F-NP':[t.R(0,page('F-NP',[t.NP],'a')),subprocess.TimeoutExpired('kubectl',20)]},'F-NP')
case('later_page_forbidden',{'F-NP':[t.R(0,page('F-NP',[t.NP],'a')),t.R(1,'','forbidden')]},'F-NP')
for label,mut in [
 ('subject_null_to_match_all',lambda o:o['spec'].update(subject={'namespaces':None})),
 ('peer_null_to_match_all',lambda o:o['spec']['ingress'][0].update({'from':[{'namespaces':None}]})),
 ('protocols_null',lambda o:o['spec']['ingress'][0].update(protocols=None)),
 ('namespace_selector_null',lambda o:o['spec'].update(subject={'pods':{'podSelector':{},'namespaceSelector':None}})),
 ('ingress_wrong_direction_silently_dropped',lambda o:o['spec']['ingress'][0].update(to=[{'networks':['0.0.0.0/0']}])),
 ('egress_wrong_direction_silently_dropped',lambda o:o['spec']['egress'][0].update({'from':[{'namespaces':{}}]})),
 ('duplicate_networks',lambda o:o['spec']['egress'][0].update(to=[{'networks':['10.0.0.0/8','10.0.0.0/8']}]))
]:
 o=copy.deepcopy(t.CNP);mut(o);case(label,{'F-CNP':t.R(0,page('F-CNP',[o]))})
for label,mut in [
 ('hep_null_profiles',lambda o:o['spec'].update(profiles=None)),
 ('hep_null_expectedips',lambda o:o['spec'].update(expectedIPs=None)),
 ('hep_duplicate_profiles',lambda o:o['spec'].update(profiles=['a','a']))
]:
 o=copy.deepcopy(t.HEP);mut(o);case(label,{'F-HEP':t.R(0,page('F-HEP',[o]))},'F-HEP')
for rid,obj in [('F-CNP',t.CNP),('F-GNP',t.GNP),('F-HEP',t.HEP),('F-TIER',t.TIER)]:
 o=copy.deepcopy(obj);o['metadata']['namespace']='wrong';case('cluster_namespace_'+rid,{rid:t.R(0,page(rid,[o]))},rid)
o=copy.deepcopy(t.TIER);o['metadata']['labels']={'purpose':'preserve'}
case('tier_labels_dropped',{'F-TIER':t.R(0,page('F-TIER',[o]))},'F-TIER')
for label,v in [('nan',float('nan')),('inf',float('inf'))]:
 o=copy.deepcopy(t.TIER);o['spec']['order']=v;case('tier_'+label,{'F-TIER':t.R(0,page('F-TIER',[o]))},'F-TIER')
o=copy.deepcopy(t.CRD);o['spec']['versions'][0]['served']='false'
case('served_string_false_unlocks',{'F-CS':t.R(0,json.dumps(o))},'F-CS')
o=copy.deepcopy(t.CRD);o['spec']['versions'].append(None)
case('malformed_version_entry_ignored',{'F-CS':t.R(0,json.dumps(o))},'F-CS')
for label,body in [('podlist_scalar','null'),('pod_metadata_scalar',json.dumps({'metadata':'bad','items':[t.POD]})),
 ('pod_wrong_list_kind',json.dumps({'kind':'SecretList','apiVersion':'wrong/v2','metadata':{},'items':[t.POD]}))]:
 case(label,{'F-I1':t.R(0,body)},'F-I1')
d=copy.deepcopy(t.CALICO_DISC);d['resources']=[x for x in d['resources'] if x['name']!='tiers']
rc,calls,rows,crash=case('discovery_missing_tier_blocks_unrelated',{'F-D1':t.R(0,json.dumps(d))},'F-NP')
results['discovery_missing_tier_blocks_unrelated']['executed_reads']=[c[0] for c in calls]
rc,calls,rows,crash=case('continuation_calls_not_journaled',{'F-NP':[t.R(0,page('F-NP',[t.NP],'a/b?x=1')),t.R(0,page('F-NP',[]))]},'F-NP')
results['continuation_calls_not_journaled']['actual_paths']=[a[-1] for rid,a in calls if rid=='F-NP']
results['continuation_calls_not_journaled']['logged_path']=next(x for x in rows if x['id']=='F-NP')['argv'][-1]
o=copy.deepcopy(t.CRD);o['spec']['versions'][0]['schema']['openAPIV3Schema']['properties']['spec']['properties']['description']={'type':'string'}
case('schema_semantic_description_property_erased',{'F-CS':t.R(0,json.dumps(o))},'F-CS')
o=copy.deepcopy(t.CNP);o['spec']['subject']={'namespaces':{'matchExpressions':[{'key':'x','operator':'Exists','values':None}]}}
case('selector_explicit_null_values_dropped',{'F-CNP':t.R(0,page('F-CNP',[o]))})
o=copy.deepcopy(t.HEP);o['spec']['ports'][0]['name']=''
case('schema_valid_empty_hep_port_name_rejected',{'F-HEP':t.R(0,page('F-HEP',[o]))},'F-HEP')
hashes={}
for name in ['followup.py','followup_test.py','supplemental.py','followup-typed-contract.json']:
 data=(root/name).read_bytes();hashes[name]={'sha256':hashlib.sha256(data).hexdigest(),'git_blob':hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()}
def safe(x):
 if isinstance(x,float) and not __import__('math').isfinite(x): return {'nonfinite_observed':str(x)}
 if isinstance(x,dict): return {k:safe(v) for k,v in x.items()}
 if isinstance(x,list): return [safe(v) for v in x]
 return x
(root/'observations.json').write_text(json.dumps(safe({'reviewed_sha':'4c21b2a388dfd3d91415335a028f322886d7372e','python':platform.python_version(),'hashes':hashes,'cluster_calls':0,'cases':results}),indent=2,allow_nan=False)+'\n')
print(json.dumps({k:{a:v.get(a) for a in ['rc','crash','category','exit','complete','output_count']} for k,v in results.items()},indent=2))
