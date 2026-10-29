import copy,datetime,hashlib,json,pathlib,platform,shutil,subprocess,sys,tempfile
from unittest import mock
root=pathlib.Path(__file__).parent
sys.path.insert(0,str(root))
import followup_test as t
f=t.fw
OBJS={'F-CNP':t.CNP,'F-NP':t.NP,'F-GNP':t.GNP,'F-HEP':t.HEP,'F-TIER':t.TIER}
results={}
def run(overrides=None,ctx=f.CTX):
 defaults={'F-D1':t.R(0,json.dumps(t.CALICO_DISC)),'F-I1':t.R(0,t.podlist([t.POD])),'F-CS':t.R(0,json.dumps(t.CRD)),'F-FELIX':t.R(0,json.dumps(t.FELIX))}
 defaults.update({rid:t.R(0,t.page(rid,[obj])) for rid,obj in OBJS.items()})
 defaults.update(overrides or {}); m=t.RunMock(defaults);rc=None;crash=None
 with tempfile.TemporaryDirectory() as td:
  out=pathlib.Path(td)/'out'
  with mock.patch.object(shutil,'which',return_value='/mock/kubectl'),mock.patch.object(subprocess,'run',side_effect=m),mock.patch.object(f.sys,'argv',['followup.py','--context',ctx,'--output',str(out)]):
   try:rc=f.main()
   except BaseException as e:crash=type(e).__name__
  exists=out.exists();p=out/f.OUTPUT_FILE
  rows=[json.loads(x) for x in p.read_text().splitlines()] if p.exists() else []
 return {'rc':rc,'crash':crash,'directory_exists':exists,'calls':m.calls,'rows':rows}
def case(name,overrides,target,check,ctx=f.CTX):
 v=run(overrides,ctx);row=next((r for r in v['rows'] if r['id']==target),{})
 v['target']=target;v['row']=row
 try:v['expected_safety_assertion_pass']=bool(check(v,row))
 except Exception as e:v['expected_safety_assertion_pass']=False;v['assertion_exception']=type(e).__name__
 # compact evidence: keep target record, all row dispositions, actual synthetic argv
 v['dispositions']=[{k:r.get(k) for k in ('id','category','complete','exit')} for r in v.pop('rows')]
 v['actual_target_argv']=[argv for rid,argv in v.pop('calls') if rid==target]
 if row.get('output'):
  try:
   o=json.loads(row['output'])
   if isinstance(o,list): row['output_count']=len(o);row['output_sample']=o[:1];row.pop('output')
  except Exception:pass
 results[name]=v
def ok(v,r):return v['rc']==0 and v['crash'] is None and r.get('category') is None and r.get('complete') is True
def parse(v,r):return v['rc']==1 and v['crash'] is None and len(v['rows'])==9 and r.get('category')=='PARSE_ERROR' and r.get('output')=='' and r.get('complete') is False
case('baseline',{},'F-NP',ok)
case('wrong_context',{},'F-NP',lambda v,r:v['crash']=='SystemExit' and not v['calls'] and not v['directory_exists'],ctx='another-context')
for rid,obj in OBJS.items():
 for n in (201,501):
  objs=t.objects(obj,n)
  sizes=(200,1) if n==201 else (200,200,101)
  pages=[];off=0
  for i,size in enumerate(sizes):
   pages.append(t.R(0,t.page(rid,objs[off:off+size],None if i==len(sizes)-1 else 'token'+str(i))));off+=size
  case(f'{rid}_distinct_{n}',{rid:pages},rid,lambda v,r,n=n:(ok(v,r) and len(json.loads(r['output']))==201) if n==201 else (v['rc']==1 and r['category']=='PARTIAL' and r['complete'] is False and len(json.loads(r['output']))==500))
 case(rid+'_overlong_first201',{rid:t.R(0,t.page(rid,t.objects(obj,201)))},rid,lambda v,r:v['rc']==1 and r['category']=='PARTIAL' and r['complete'] is False)
 case(rid+'_empty',{rid:t.R(0,t.page(rid,[]))},rid,ok)
 for label,ans,cause,ret in [('forbidden',t.R(7,'','forbidden'),'FORBIDDEN',7),('notserved',t.R(8,'',"the server doesn't have a resource type"),'API_NOT_SERVED',8),('connection',t.R(9,'','connection refused'),'CONNECTION',9),('timeout',subprocess.TimeoutExpired('kubectl',20),'TIMEOUT',None),('oserror',OSError('SYNTHETIC_PRIVATE_ERROR'),'GET_FAILED',None)]:
  for later in (False,True):
   response=[t.R(0,t.page(rid,[obj],'tok')),ans] if later else ans
   def check(v,r,later=later,cause=cause,ret=ret):
    j=r.get('journal',[])
    return v['rc']==1 and v['crash'] is None and r['category']==('PARTIAL' if later else cause) and r['complete'] is False and r['exit']==ret and len(j)==(2 if later else 1) and j[-1]['cause']==cause and j[-1]['returncode']==ret and (len(json.loads(r['output']))==1 if later else r['output']=='')
   case(f'{rid}_{label}_'+('later' if later else 'first'),{rid:response},rid,check)
 for label,bad in [('badjson',t.R(0,'NOT_JSON_SYNTHETIC_CANARY')),('scalar',t.R(0,t.page(rid,[None]))),('badprojector',t.R(0,t.page(rid,[dict(obj,spec='bad')])))]:
  for later in (False,True):
   response=[t.R(0,t.page(rid,[obj],'tok')),bad] if later else bad
   case(f'{rid}_{label}_'+('later' if later else 'first'),{rid:response},rid,lambda v,r,later=later:parse(v,r) and r['exit']==0 and len(r.get('journal',[]))==(2 if later else 1) and r['journal'][-1]['cause']=='PARSE_ERROR')
 p=json.loads(t.page(rid,[obj]));p['metadata']['continue']=None
 case(rid+'_null_continue',{rid:t.R(0,json.dumps(p))},rid,parse)
 o=copy.deepcopy(obj);o['spec']['UNSUPPORTED_SEMANTICS']='SYNTHETIC_CANARY'
 case(rid+'_unsupported_projector',{rid:t.R(0,t.page(rid,[o]))},rid,lambda v,r:v['rc']==1 and r['category']=='UNSUPPORTED' and r['complete'] is False and r['output']=='')
 o=copy.deepcopy(obj);o['metadata']['namespace']=None
 if rid!='F-NP':case(rid+'_null_namespace',{rid:t.R(0,t.page(rid,[o]))},rid,parse)
 # A bounded valid prefix may be preserved; the discarded suffix stays unvalidated/UNKNOWN
 objs=t.objects(obj,501);objs[-1]['spec']='bad'
 case(rid+'_bounded_prefix_invalid_suffix',{rid:t.R(0,t.page(rid,objs))},rid,lambda v,r:v['rc']==1 and r['category']=='PARTIAL' and r['complete'] is False and len(json.loads(r['output']))==500)
# I1 must retain safe diagnostic on unsupported, no dependencies execute
p=copy.deepcopy(t.POD);p['status']['containerStatuses'][0]['imageID']='sha256:'+'0'*64
case('identity_unsupported_diagnostic',{'F-I1':t.R(0,t.podlist([p]))},'F-I1',lambda v,r:r['category']=='UNSUPPORTED' and bool(r['output']) and not any(x[0] in ('F-NP','F-GNP','F-FELIX','F-HEP','F-TIER') for x in v['calls']))
for field,val in [('resourceVersion',None),('continue',None)]:
 p=json.loads(t.podlist([t.POD]));p['metadata'][field]=val
 case('identity_null_'+field,{'F-I1':t.R(0,json.dumps(p))},'F-I1',parse)
for bad in ({},{'name':None},{'name':42},{'name':'v2','served':'bad'}):
 o=copy.deepcopy(t.CRD);o['spec']['versions'].append(bad)
 case('crd_malformed_version_'+str(len(results)),{'F-CS':t.R(0,json.dumps(o))},'F-CS',lambda v,r:v['rc']==1 and r['category']=='PARSE_ERROR' and r['output']=='' and not any(x[0]=='F-CNP' for x in v['calls']))
for rid,obj in [('F-CNP',t.CNP),('F-GNP',t.GNP)]:
 o=copy.deepcopy(obj);o['spec']['order' if rid=='F-GNP' else 'priority']=float('nan')
 case(rid+'_nonfinite',{rid:t.R(0,t.page(rid,[o]))},rid,parse)
for resource in f.D1_EXPECT:
 for mutation in ('missing','kind','scope','verbs'):
  d=copy.deepcopy(t.CALICO_DISC)
  for x in d['resources']:
   if x['name']==resource:
    if mutation=='kind':x['kind']='WrongKind'
    if mutation=='scope':x['namespaced']=not x['namespaced']
    if mutation=='verbs':x['verbs']=[]
  if mutation=='missing':d['resources']=[x for x in d['resources'] if x['name']!=resource]
  dep={'networkpolicies':'F-NP','globalnetworkpolicies':'F-GNP','felixconfigurations':'F-FELIX','hostendpoints':'F-HEP','tiers':'F-TIER'}[resource]
  case('discovery_'+resource+'_'+mutation,{'F-D1':t.R(0,json.dumps(d))},dep,lambda v,r,dep=dep:r['category']=='BLOCKED_NOT_EXECUTED' and not any(x[0]==dep for x in v['calls']) and len(v['calls'])==8)
case('journal_encoded_token',{'F-NP':[t.R(0,t.page('F-NP',[t.NP],'SYNTHETIC/token?=1')),t.R(0,t.page('F-NP',[]))]},'F-NP',lambda v,r:ok(v,r) and any(x[1][-1].endswith('&continue=SYNTHETIC%2Ftoken%3F%3D1') for x in v['calls']) and len(r['journal'])==2 and (all('argv' in x or 'path' in x for x in r['journal']) or r.get('argv_scope')=='initial_request_only'))
hashes={}
for p in ('followup.py','followup_test.py','supplemental.py','followup-typed-contract.json'):
 b=(root/p).read_bytes();hashes[p]={'sha256':hashlib.sha256(b).hexdigest(),'blob':hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()}
report={'reviewed_sha':'d71af18c27059bcd9ce3ae3c2b15686d7df953c6','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'python':platform.python_version(),'hashes':hashes,'cluster_calls':0,'cases':results}
(root/'observations.json').write_text(json.dumps(report,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n')
failed=[n for n,v in results.items() if not v['expected_safety_assertion_pass']]
print(json.dumps({'executed':len(results),'passed':len(results)-len(failed),'failed':len(failed),'failed_cases':failed},indent=2))

