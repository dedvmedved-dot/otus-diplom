#!/usr/bin/env python3
"""Offline documentary checks only; never imports collectors or executes kubectl."""
import ast,datetime,hashlib,json,re
from pathlib import Path
P=Path(__file__).resolve().parent
base=P/"portal/networkpolicy"
execution=json.loads((P/"reference/execution.json").read_text())
observations=json.loads((P/"reference/observations.json").read_text())
design=(base/"supplemental-design.md").read_text()
matrix=(base/"coverage-matrix.md").read_text()
source=(base/"supplemental.py").read_bytes()
tests=(base/"supplemental_test.py").read_bytes()
def blob(b):return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
assert blob(source)=="ad2edaa92de59f657599190842fa7fe68373b582"
assert blob(tests)=="8157b942d9f4066dfda7448f2c71fe170b24f657"
definitions={n.name for n in ast.walk(ast.parse(tests)) if isinstance(n,ast.FunctionDef)}
ids=sorted(set(re.findall(r"\btest_[a-zA-Z0-9_]+",matrix)))
assert not set(ids)-definitions
assert execution[0]["argv"]==["python3","supplemental_test.py","-v"] and execution[0]["exit"]==0
assert "Ran 33 tests" in execution[0]["stderr"] and execution[0]["stderr"].rstrip().endswith("OK")
for name in ids:assert name+" (" in execution[0]["stderr"],name
keys=["identity_wrong_registry","identity_wrong_version","identity_missing_imageID",
"valid_unsupported_identity","malformed_identity_json","malformed_identity_types",
"literal_main_path","wrong_response_version","bad_discovery","C1_forbidden",
"C1_api_not_served","C1_connection","C1_timeout"]
for key in keys:assert key in observations,key
assert observations["literal_main_path"]["calls"]
for key in ["identity_wrong_registry","identity_wrong_version","identity_missing_imageID","valid_unsupported_identity"]:
 row=next(x for x in observations[key]["rows"] if x["id"]=="I1")
 assert row["category"]=="UNSUPPORTED" and row["output"]
for key in ["malformed_identity_json","malformed_identity_types"]:
 row=next(x for x in observations[key]["rows"] if x["id"]=="I1")
 assert row["category"]=="PARSE_ERROR" and not row["output"]
assert observations["hashes"]["supplemental.py"]["git_blob"]==blob(source)
assert observations["hashes"]["supplemental_test.py"]["git_blob"]==blob(tests)
for rid in ["D1","D2","I1","C1","C2","C3","C4","C5","S1","S2"]:assert "| "+rid+" |" in design
priority="SourcesInDescendingOrder = []Source{InternalOverride, EnvironmentVariable, ConfigFile, DatastorePerHost, DatastorePerSelector, DatastoreGlobal}"
assert priority in (P/"reference/calico-config.go").read_text()
assert blob((P/"reference/calico-config.go").read_bytes())=="72676f76f3bdd5f592e29313c712b159db0bcd2e"
for label in ["HostEndpoint","Tier","node.<nodename>","cannot use nodeSelector","effective per-node mode remains UNKNOWN"]:
 assert label in design,label
for n in ["supplemental-design.md","PLAN.md","collection-map.md","flow-matrix.md","gaps.md"]:
 s=(base/n).read_text()
 assert "PHASE2_LIVE_READS_APPROVED=NO" in s or ("live" in s and ("CLOSED" in s or "NOT approved" in s))
assert "31/31" not in (base/"collection-map.md").read_text()
result={
"checked_at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
"reviewed_main":"79706203c7c6ec46686fa9e36686bf52ce1a4b9c",
"checks":{
"code_byte_identity":"PASS","prior_33_test_evidence":"REUSED_PASS_NOT_RERUN",
"matrix_test_ids_exist_and_were_executed":{"result":"PASS","count":len(ids),"ids":ids},
"matrix_json_case_keys":{"result":"PASS","keys":keys},
"ten_reads_documented":"PASS","exact_felix_source_priority":"PASS",
"nodeSelector_scope_and_host_tier_limits":"PASS",
"gates_preserved":"PASS","collection_map_count":"PASS"},
"files":{n:{"git_blob":blob((base/n).read_bytes()),"sha256":hashlib.sha256((base/n).read_bytes()).hexdigest()}
for n in ["supplemental.py","supplemental_test.py","supplemental-design.md","coverage-matrix.md","PLAN.md","flow-matrix.md","gaps.md","collection-map.md"]},
"sources":{
"calico":{"commit":"eb1cf57823a1dd8d25c48b82fd023ea9e3e17996","path":"felix/config/config_params.go","blob":"72676f76f3bdd5f592e29313c712b159db0bcd2e","repository_crd_blob":"21ea9b4b163305ea479bc7708965104465ffc716","checked_members":["Source","SourcesInDescendingOrder","resolve","FelixConfiguration spec.nodeSelector.description"]},
"barman":{"release_manifest_blob":"4fa292cd8f89808d96f6d90af826afd31afa29ec","objectstore_blob":"07709428317922b7789a7b6c22bf9b88b5dc9a03","cluster_blob":"e60a92353194fda60f34dacb56273ed7048af14c","checked_fields":["Service port9090/TCP/pluginPort","Deployment server-address/TLS arguments","ObjectStore configuration endpointURL","Cluster spec.plugins"],"docs":["https://cloudnative-pg.io/plugin-barman-cloud/docs/0.13.0/concepts/","https://cloudnative-pg.io/plugin-barman-cloud/docs/0.13.0/usage/"]},
"kubernetes":["https://v1-36.docs.kubernetes.io/docs/concepts/services-networking/network-policies/","https://v1-36.docs.kubernetes.io/docs/reference/networking/virtual-ips/"]},
"manual_checks":["Type/helper summary inspected against pinned source, including optional/null normalization.","Barman control service vs sidecar source distinction; no live traffic inference.","Felix config precedence and nodeSelector constraints checked against exact source/schema.","API endpoints distinguished from Pod IPs; effective DNAT unknown.","Remaining historical claims in PLAN explicitly non-authoritative and non-executable."],
"no_live_reads":True,"no_behavioral_tests_rerun":True,"policy_yaml_unchanged":True
}
(P/"doc-check.json").write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps(result["checks"],indent=2))
