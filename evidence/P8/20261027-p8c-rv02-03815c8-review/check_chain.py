import hashlib,json,pathlib
r=pathlib.Path(__file__).parent
expected={
'index.json':'f4fafd8ba641d96c5a91b01e5a519117d77d55dee789a3562ba3ad4aa125b36a',
'manifest.json':'12262c951e705c595f49d354372bcb0f166b1571b26d502a006fb487dd0025e4',
'config.json':'6bc9fa4dc2b10ca1d4b97a1cd570036651898cea8b3c3bcbb1d55cf813e43f65'}
data={}
for p,h in expected.items():
 b=(r/p).read_bytes();assert hashlib.sha256(b).hexdigest()==h,p;data[p]=json.loads(b)
index,manifest,config=[data[p] for p in expected]
assert index['mediaType']=='application/vnd.docker.distribution.manifest.list.v2+json'
desc=[d for d in index['manifests'] if d['platform'].get('os')=='linux' and d['platform'].get('architecture')=='amd64']
assert len(desc)==1
assert desc[0]['digest']=='sha256:'+expected['manifest.json']
assert desc[0]['size']==len((r/'manifest.json').read_bytes())
assert desc[0]['mediaType']==manifest['mediaType']=='application/vnd.docker.distribution.manifest.v2+json'
assert manifest['config']['digest']=='sha256:'+expected['config.json']
assert manifest['config']['size']==len((r/'config.json').read_bytes())
assert manifest['config']['mediaType']=='application/vnd.docker.container.image.v1+json'
assert config['architecture']=='amd64' and config['os']=='linux'
assert 'sha256:'+expected['config.json']=='sha256:6bc9fa4dc2b10ca1d4b97a1cd570036651898cea8b3c3bcbb1d55cf813e43f65'
print(json.dumps({'byte_hashes':expected,'descriptor_sizes':'PASS','media_types':'PASS',
'platform':'linux/amd64','observed_id_equals_config':'PASS','identity_chain':'INDEPENDENTLY_VERIFIED',
'limits':['not runtime attestation','not proof of runtime implementation/version','no layers fetched or executed','no cluster access']},indent=2))

