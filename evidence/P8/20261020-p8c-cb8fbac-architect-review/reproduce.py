#!/usr/bin/env python3
"""Offline Architect review: synthetic input/subprocesses, no Kubernetes access.
Run: python3 reproduce.py CHECKOUT_ROOT (requires PyYAML and Node for UI check).
"""
import contextlib, getpass, importlib.util, io, json, pathlib, subprocess, sys, warnings
from unittest import mock
import yaml

root = pathlib.Path(sys.argv[1])
results = {"reviewed_sha": "cb8fbacd4cf036a4f7ec43fcb734f7dd751fd7ed", "kind": "offline mock/static manifest checks; NOT runtime evidence", "checks": []}
for filename, inputs in [("provision-ui-auth.py", ["A" * 43] * 2), ("provision-registry-pull.py", ["synthetic-owner", "synthetic-token"])]:
    spec = importlib.util.spec_from_file_location(filename, root / "portal/tools" / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    class FakeTTY(io.StringIO):
        def isatty(self): return True
    stream = FakeTTY("\n".join(inputs) + "\n")
    calls = []
    def fake_run(args, **kw):
        calls.append("create" if "create" in args else "get")
        return subprocess.CompletedProcess(args, 0, "", "")
    with mock.patch.object(sys, "argv", [filename, "--context", "synthetic-context"]), mock.patch.object(sys, "stdin", stream), mock.patch.object(getpass, "getpass", getpass.fallback_getpass), mock.patch.object(subprocess, "run", fake_run), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()), warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        code = mod.main()
    results["checks"].append({"check": filename + ": actual stdlib fallback_getpass", "exit": code, "GetPassWarning_count": sum(issubclass(w.category, getpass.GetPassWarning) for w in caught), "mock_kubectl_verbs": calls, "required": "STOP before fallback input/write", "disposition": "FAIL" if "create" in calls else "PASS"})

policies = list(yaml.safe_load_all((root / "portal/manifests/networkpolicy.yaml").read_text()))
objects = list(yaml.safe_load_all((root / "portal/manifests/deployment.yaml").read_text()))
job = next(x for x in objects if x and x.get("kind") == "Job")
labels = job["spec"]["template"].get("metadata", {}).get("labels", {})
def matches(sel, labels):
    assert not sel.get("matchExpressions"), "extend evaluator for expressions"
    return all(labels.get(k) == v for k, v in sel.get("matchLabels", {}).items())
def ingress_allows(policy, labels, namespace, port):
    for rule in policy["spec"].get("ingress", []):
        if not any(p["port"] == port for p in rule.get("ports", [])): continue
        for peer in rule.get("from", []):
            ns = peer.get("namespaceSelector")
            if ns is None and namespace != policy["metadata"]["namespace"]: continue
            if ns is not None and not matches(ns, {"kubernetes.io/metadata.name": namespace}): continue
            if matches(peer.get("podSelector", {}), labels): return True
    return False
cnpg = next(p for p in policies if p["metadata"]["name"] == "p8c-cnpg-existing-flows")
portal = next(p for p in policies if p["metadata"]["name"] == "p8c-portal-flows")
migrator = next(p for p in policies if p["metadata"]["name"] == "p8c-migrator-flows")
results["checks"].append({"check": "static NetworkPolicy selectors/ports", "actual_job_labels": labels, "migrator_policy_selects_job": matches(migrator["spec"]["podSelector"], labels), "cnpg_allows_migrator_5432": ingress_allows(cnpg, labels, "portal", 5432), "cnpg_allows_portal_metrics_9187": ingress_allows(cnpg, {"app.kubernetes.io/name": "pak-portal"}, "portal", 9187), "portal_allows_unrelated_namespace_pod_8080": ingress_allows(portal, {"app": "unrelated"}, "unrelated", 8080), "dataplane_policy_present": any(p["metadata"]["name"] == "p8c-portal-dataplane-flows" for p in policies), "disposition": "FAIL"})
workflow = yaml.safe_load((root / "portal/tools/p8c-portal-release.yml.template").read_text())
steps = workflow["jobs"]["release"]["steps"]
run = "\n".join(s.get("run", "") for s in steps)
results["checks"].append({"check": "static release workflow", "push_before_login": next(i for i,s in enumerate(steps) if "push=true" in s.get("run", "")) < next(i for i,s in enumerate(steps) if "docker/login-action@" in s.get("uses", "")), "rootful_daemon": "sudo buildkitd" in run, "integration_command_present": "go test -tags integration" in run, "race_command_present": "go test -race" in run, "browser_test_command_present": "jsdom" in run or "playwright" in run, "explicit_Containerfile_option": "filename=Containerfile" in run, "cosign_input": next(s for s in steps if "sigstore/cosign-installer@" in s.get("uses", ""))["with"]["cosign-release"], "disposition": "FAIL"})
js = r'''
const fs=require('fs'),vm=require('vm');
const els={}; const el=id=>els[id]??=( {innerHTML:'',textContent:'',className:'',classList:{toggle(){}}} );
let mode='failed';
const ctx={document:{getElementById:el,querySelectorAll:()=>[],querySelector:()=>null},setInterval:()=>0,fetch:async()=>{if(mode==='failed')throw Error('synthetic offline');return {status:200,ok:true,json:async()=>({freshness:'unavailable',data:{overall:'healthy',counts:{nodesReady:3,nodesExpected:3,nodesObserved:3},alerts:[]}})}}};
vm.createContext(ctx);vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),ctx);
(async()=>{await vm.runInContext('renderKubernetes()',ctx);const failedPods=el('table-pods').innerHTML;mode='stale';await vm.runInContext('renderOverview()',ctx);process.stdout.write(JSON.stringify({failedPodsRender:failedPods,staleOverallClass:el('overall-status').className,staleAlerts:el('alerts').innerHTML}));})();
'''
out = subprocess.run(["node", "-e", js, str(root / "portal/web/app.js")], capture_output=True, text=True)
if out.returncode:
    print(out.stderr, file=sys.stderr)
    sys.exit(out.returncode)
results["checks"].append({"check": "actual app.js renderers in Node VM; synthetic DOM/fetch (not browser)", **json.loads(out.stdout), "disposition": "FAIL"})
print(json.dumps(results, ensure_ascii=False, indent=2))
