import urllib.request,json,hashlib,pathlib,datetime,subprocess
root=pathlib.Path(__file__).parent;out=root/'source-work/evidence/P8/20261021-p8c-r3-independent-source'
start=datetime.datetime.now(datetime.timezone.utc).isoformat()
u='https://github.com/rootless-containers/rootlesskit/releases/download/v2.3.1/SHA256SUMS'
with urllib.request.urlopen(u,timeout=30) as r:body=r.read().decode()
line=next(x for x in body.splitlines() if x.endswith('rootlesskit-x86_64.tar.gz'))
assert line.split()[0]=='caafdce18e0959f078b4b478d4f352ebf3d556e373265fc7831f1a6d70219ee0'
(out/'rootlesskit-upstream-checksum.json').write_text(json.dumps({'utc':start,'url':u,'checksumLine':line,'verification':'published SHA matches source pin; no GPG signature verification claimed'},indent=2)+'\n')
# Public Docker Library manifest; anonymous bearer stays only in memory.
with urllib.request.urlopen('https://auth.docker.io/token?service=registry.docker.io&scope=repository:library/postgres:pull',timeout=30) as r:token=json.load(r)['token']
u='https://registry-1.docker.io/v2/library/postgres/manifests/17.10-bookworm'
req=urllib.request.Request(u,headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.oci.image.index.v1+json, application/vnd.docker.distribution.manifest.list.v2+json'})
with urllib.request.urlopen(req,timeout=30) as r:data=r.read();header=r.headers['Docker-Content-Digest'];ctype=r.headers['Content-Type']
digest='sha256:'+hashlib.sha256(data).hexdigest()
assert digest==header=='sha256:9b18b78397054fce88a9552e9d5a3ad5bb7fd258c5b3cc1c5028e46373d6ea8f'
(out/'postgres-test-image-proof.json').write_text(json.dumps({'utc':start,'url':u,'digest':digest,'Docker-Content-Digest':header,'Content-Type':ctype,'bytes':len(data),'execution':'NOT_EXECUTED: manifest bytes only; no image run'},indent=2)+'\n')
(out/'postgres-test-image-manifest.json').write_bytes(data)
p=subprocess.run(['npm','ls','--depth=0'],cwd=root/'source-work/portal',stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
(out/'20-additional-proofs.txt').write_text('UTC_START='+start+'\nCOMMAND=python3 extra_proofs.py\nPASS published rootlesskit checksum\nPASS public postgres image manifest bytes/hash/header\nCOMMAND=npm ls --depth=0\n'+p.stdout+'EXIT_CODE='+str(p.returncode)+'\nUTC_END='+datetime.datetime.now(datetime.timezone.utc).isoformat()+'\n')
assert p.returncode==0
print('PASS upstream checksum / public test-image digest / installed locked renderer dependency')
