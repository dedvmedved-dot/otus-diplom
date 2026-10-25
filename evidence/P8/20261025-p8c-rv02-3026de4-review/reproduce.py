#!/usr/bin/env python3
"""Independent offline observations; exit 0 records findings, not acceptance."""
import copy, json, tempfile, subprocess
from pathlib import Path
from unittest import mock
import inventory as inv

CANARY = "SYNTHETIC_REVIEW_CANARY_NOT_A_CREDENTIAL"
NP = "networkpolicies.networking.k8s.io"
OS = "objectstores.barmancloud.cnpg.io"
def run_case(resource, item=None, failure=None):
    with tempfile.TemporaryDirectory() as tmp:
        dest = Path(tmp) / "output"
        stdout = json.dumps({"items": [item]})
        command = (["get", resource, "-A", "-o", "json"], resource)
        result = subprocess.CompletedProcess([], 0, stdout, "")
        with mock.patch.object(inv, "COMMANDS", [command]), \
             mock.patch.object(inv.shutil, "which", return_value="/mock/kubectl"), \
             mock.patch.object(inv.subprocess, "run", side_effect=failure, return_value=result), \
             mock.patch.object(inv.sys, "argv", ["inventory.py", "--context", "mock", "--output", str(dest)]):
            code, exception = None, None
            try:
                code = inv.main()
            except Exception as exc:
                exception = type(exc).__name__
        rows = [json.loads(line) for line in (dest / "inventory.jsonl").read_text().splitlines()]
        return {"exit": code, "exception": exception, "rows": rows}

def brief(result):
    rows = result["rows"]
    return {"exit": result["exit"], "exception": result["exception"],
            "categories": [r["category"] for r in rows],
            "canaryInOutput": CANARY in json.dumps(rows),
            "outputs": [r["output"] for r in rows]}

obs = {}
base = {"apiVersion":"networking.k8s.io/v1", "kind":"NetworkPolicy",
        "metadata":{"name":"example", "namespace":"portal"},
        "spec":{"podSelector":{}, "policyTypes":["Ingress"]}}
for name, val in {
    "unsupported_scheme": "ftp://user:" + CANARY + "@host.invalid/?token=" + CANARY,
    "wrong_type": {"credential": CANARY},
    "unvalidated_path": "https://host.invalid/" + CANARY,
}.items():
    obj = {"kind":"ObjectStore","metadata":{"name":"example","namespace":"portal"},
           "spec":{"data":{"endpointURL": val}}}
    obs[name] = brief(run_case(OS, obj))
obs["ipv6"] = {"input":"https://[2001:db8::1]:9000/", "output":inv.sanitize_url("https://[2001:db8::1]:9000/")}
for name, change in {
    "bad_spec": {"spec": "bad"},
    "wrong_kind": {"kind":"Secret"},
    "missing_identity": {"metadata":{}},
    "null_selector": {"spec":{"podSelector":None}},
    "bad_match_expressions": {"spec":{"podSelector":{"matchExpressions":{"credential":CANARY}}}},
    "bad_endport": {"spec":{"podSelector":{}, "ingress":[{"ports":[{"port":8000,"endPort":{"credential":CANARY}}]}]}},
}.items():
    obj = copy.deepcopy(base)
    obj.update(change)
    obs[name] = brief(run_case(NP, obj))
for name, failure in {
    "subprocess_timeout": subprocess.TimeoutExpired(["mock"],20, output=CANARY, stderr=CANARY),
    "subprocess_oserror": OSError(CANARY),
}.items():
    obs[name] = brief(run_case(NP, base, failure))
print(json.dumps(obs, indent=2, sort_keys=True))
