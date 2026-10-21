import importlib.util,pathlib,json,base64
root=pathlib.Path(__file__).parent
s=importlib.util.spec_from_file_location('release_check',root/'source-work/portal/tools/release-check.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
statement=json.loads((root/'cosign-check/generated-statement.json').read_text())
source=statement['predicate']['invocation']['configSource']['digest']['sha1']
env={'payload':base64.b64encode(json.dumps(statement).encode()).decode()}
m.check_attestations(json.dumps(env),'sha256:'+'a'*64,source,m.SLSA)
print('PASS actual pinned Cosign GenerateStatement output through strict release payload checker; synthetic image digest/source, NOT cryptographic signature verification')
