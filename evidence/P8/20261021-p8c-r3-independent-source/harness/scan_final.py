import pathlib,json,re,sys
root=pathlib.Path(__file__).parent
index=json.loads((root/'final-source-index.json').read_text())
patterns={
 'private-key':r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
 'github-token':r'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b',
 'aws-access-key':r'\bAKIA[0-9A-Z]{16}\b',
 'credential-url':r'postgres(?:ql)?://[^\s/:]+:[^\s/@]+@',
}
hits=[];fixtures=[]
for f in index['files']:
 path=f['path'];text=(root/'source-work'/path).read_text()
 for kind,pat in patterns.items():
  for match in re.finditer(pat,text):
   # Only the explicitly synthetic localhost CI service credential is allowed.
   if kind=='credential-url' and match.group()=='postgres://postgres:postgres@' and text[match.end():].startswith('localhost:5432/portal_test'):
    fixtures.append({'path':path,'kind':kind,'classification':'fixed isolated CI service fixture'});continue
   hits.append({'path':path,'kind':kind,'line':text[:match.start()].count('\n')+1})
print(json.dumps({'sourceSHA':index['sourceSHA'],'files':len(index['files']),'rules':list(patterns),'findings':hits,'syntheticAllowlist':fixtures},indent=2))
print('Heuristic source scan only; not a runtime/registry scan. No credentials were read or provisioned.')
sys.exit(bool(hits))
