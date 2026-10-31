"""Build a test-only PodList from accepted SANITIZED I1, not from live Pods."""
import copy,hashlib,json,pathlib
root=pathlib.Path(__file__).parent
raw=(root/'accepted-supplemental.jsonl').read_bytes()
assert hashlib.sha256(raw).hexdigest()=='02e872e7b82918380c89e8f3a2bf74dc039bd48ea6ee167c0f64d477debe642c'
rows=[json.loads(line) for line in raw.decode().splitlines()]
projected=json.loads(next(r for r in rows if r['id']=='I1')['output'])
assert len(projected)==3
pods=[]
for src in projected:
 p={'apiVersion':'v1','kind':'Pod','metadata':copy.deepcopy(src['metadata']),'spec':{},'status':{}}
 for key,statuskey in [('initContainers','initContainerStatuses'),('containers','containerStatuses')]:
  p['spec'][key]=[{k:v for k,v in c.items() if k!='imageID' and v is not None} for c in src[key]]
  p['status'][statuskey]=[{'name':c['name'],'imageID':c['imageID']} for c in src[key]]
 pods.append(p)
fixture={'provenance':{'classification':'DERIVED_FROM_ACCEPTED_EVIDENCE','source_commit':'832591b8735dd8dfef0523cf8e0432d840125468','path':'evidence/P8/20261027T140000Z-p8c-rv02-phase2-live/result/supplemental.jsonl','source_blob':'7c6151b490c02a79ecfe2337e6f262addd36519a','sha256':hashlib.sha256(raw).hexdigest(),'record':'I1','mapping':'metadata copied; projected initContainers/containers fields except imageID/null mapped to spec; imageID joined by name in status; wrappers apiVersion/kind and metadata.resourceVersion are SYNTHETIC, not collected live','synthetic_list_resourceVersion':'fixture-only-rv'},'podlist':{'kind':'PodList','apiVersion':'v1','metadata':{'resourceVersion':'fixture-only-rv'},'items':pods},'expected_projection':projected}
(root/'derived-i1-fixture.json').write_text(json.dumps(fixture,indent=2)+'\n')

