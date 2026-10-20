#!/usr/bin/env python3
"""Offline c3cfec6 checks. Python helpers execute with mocked terminal/kubectl;
Go allowlist is inspected as source data (NOT executed Go). Requires PyYAML.
"""
import contextlib, importlib.util, io, json, pathlib, re, subprocess, sys
from unittest import mock
import yaml
root=pathlib.Path(sys.argv[1] if len(sys.argv)>1 else '.')
checks=[]
for name, raw in [('provision-ui-auth.py','A'*43+'\n'+'A'*43),('provision-registry-pull.py','synthetic-user\nsynthetic-token')]:
    spec=importlib.util.spec_from_file_location(name,root/'portal/tools'/name)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    class FakeTTY(io.StringIO):
        def isatty(self): return True
        def fileno(self): return 0
    calls=[]
    def run(args,**kwargs):
        calls.append('create' if 'create' in args else 'get')
        return subprocess.CompletedProcess(args,0,'','')
    # Missing final newline forces EOF mid-input; no real terminal or kubectl.
    with mock.patch.object(sys,'argv',['helper','--context','synthetic']),mock.patch.object(sys,'stdin',FakeTTY(raw)),mock.patch('termios.tcgetattr',return_value=[0]*7),mock.patch('tty.setraw'),mock.patch('termios.tcsetattr'),mock.patch.object(subprocess,'run',run),contextlib.redirect_stderr(io.StringIO()),contextlib.redirect_stdout(io.StringIO()):
        code=mod.main()
    checks.append({'check':name+' EOF before final newline','exit':code,'mock_verbs':calls,'expected':'STOP before create','result':'FAIL' if 'create' in calls else 'PASS'})
gw=list(yaml.safe_load_all((root/'portal/manifests/gateway.yaml').read_text()))
gateway=next(o for o in gw if o and o.get('kind')=='Gateway')
pol=list(yaml.safe_load_all((root/'portal/manifests/networkpolicy.yaml').read_text()))
dataplane=next(o for o in pol if o['metadata']['name']=='p8c-portal-dataplane-flows')
selected=dataplane['spec']['podSelector']['matchLabels']['gateway.envoyproxy.io/owning-gateway-name']
checks.append({'check':'Gateway vs NetworkPolicy cross-file consistency','gateway_name':gateway['metadata']['name'],'policy_gateway_name':selected,'match':selected==gateway['metadata']['name'],'dataplane_egress_ports':sorted({p['port'] for rule in dataplane['spec']['egress'] for p in rule['ports']})})
transport=(root/'portal/internal/collectors/transport.go').read_text()
keys=re.findall(r'"([a-z0-9./-]+)":\s*true',transport)
checks.append({'check':'Go allowlist source inspection (NOT execution)','actual_collector_api':'discovery.k8s.io/v1/endpointslices','actual_api_approved':'discovery.k8s.io/v1/endpointslices' in keys,'incorrect_core_resource_present':'endpointslices' in keys})
wf=yaml.safe_load((root/'portal/tools/p8c-portal-release.yml.template').read_text())
runs='\n'.join(s.get('run','') for j in wf['jobs'].values() for s in j['steps'])
checks.append({'check':'workflow static source','buildkit_version':wf['env']['BUILDKIT_VERSION'],'renderer_smoke_invoked':'renderer-smoke.test.mjs' in runs,'provenance_attestation_present':'cosign attest' in runs,'sbom_attestation_verification_present':'verify-attestation' in runs,'go_checksum_optional':'if [ -f "$dl" ]' in runs})
go=(root/'portal/internal/collectors/collect_methods.go').read_text()
checks.append({'check':'collector source integration','listWithContinue_call_count':go.count('listWithContinue('),'pods_cap_equal_page': 'listWithContinue(ctx, listPage, listPage,' in go})
print(json.dumps({'reviewed_sha':'c3cfec621f87fb496f35099b08bc3feeb00ba309','checks':checks},indent=2))
