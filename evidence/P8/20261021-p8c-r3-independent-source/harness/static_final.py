import pathlib,re,subprocess,yaml,json
p=pathlib.Path('portal/tools/p8c-portal-release.yml.template')
d=yaml.safe_load(p.read_text());n=0
assert d['permissions']=={'contents':'read'}
assert d['jobs']['release']['permissions']=={'contents':'read','packages':'write','id-token':'write'}
assert 'permissions' not in d['jobs']['test']
for name,job in d['jobs'].items():
    for step in job['steps']:
        if 'uses' in step:assert re.fullmatch(r'[^@]+@[0-9a-f]{40}',step['uses'])
        if 'run' in step:
            script=re.sub(r'\$\{\{.*?\}\}','synthetic-check-value',step['run'])
            p=subprocess.run(['bash','-n'],input=script,text=True,capture_output=True)
            assert p.returncode==0,(name,step.get('name'),p.stderr);n+=1
assert re.search(r'@sha256:[0-9a-f]{64}$',d['jobs']['test']['services']['postgres']['image'])
print('PASS YAML load; '+str(n)+' shell blocks bash -n; immutable action refs; job-scoped permissions; pinned test image')
print('NOT_EXECUTED: GitHub expression evaluation, runner BuildKit, push/sign/attest/private verification')
