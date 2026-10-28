import copy,hashlib,json,pathlib
root=pathlib.Path(__file__).parent
def normalize_schema(s):
 if isinstance(s,bool):return s
 if not isinstance(s,dict):raise ValueError('schema must be object/boolean')
 maps={'properties','patternProperties','definitions','$defs','dependentSchemas'}
 arrays={'allOf','anyOf','oneOf','prefixItems'}
 singles={'items','additionalItems','additionalProperties','unevaluatedItems','unevaluatedProperties','not','contains','propertyNames','if','then','else'}
 out={}
 for k,v in s.items():
  if k=='description':continue
  if k in maps:
   if not isinstance(v,dict):raise ValueError('schema map')
   out[k]={name:normalize_schema(sub) for name,sub in v.items()}
  elif k in arrays:
   if not isinstance(v,list):raise ValueError('schema array')
   out[k]=[normalize_schema(sub) for sub in v]
  elif k in singles:
   out[k]=[normalize_schema(sub) for sub in v] if k=='items' and isinstance(v,list) else normalize_schema(v)
  else:out[k]=copy.deepcopy(v)
 return out
def h(x):return hashlib.sha256(json.dumps(normalize_schema(x),sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
spec=json.loads((root/'followup-typed-contract.json').read_text())['cnp']['spec_schema']
expected='770130a412fd6fab2f02d953edf35f8cc68bf4379db8307e2185937c1e699568'
assert h(spec)==expected
annotation=copy.deepcopy(spec);annotation['description']='wording only'
assert h(annotation)==expected
semantic=copy.deepcopy(spec);semantic['properties']['description']={'type':'string'}
assert h(semantic)!=expected
literal={'type':'object','default':{'description':'literal semantic default'}}
assert normalize_schema(literal)['default']['description']=='literal semantic default'
print(json.dumps({'reference_only_not_collector':True,'pinned_hash_unchanged':h(spec),'annotation_only_unchanged':h(annotation),'semantic_property_changed':h(semantic),'literal_default_preserved':True},indent=2))
