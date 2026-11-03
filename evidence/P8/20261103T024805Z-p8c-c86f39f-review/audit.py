"""Offline audit of files extracted from Connector-pinned c86f39f. No cluster/Go execution."""
import hashlib,json,pathlib,re,sys,datetime
root=pathlib.Path(sys.argv[1])
ev=root/"evidence/P8/20261102T213000Z-p8c-candidate-and-gates-r2"
m=json.loads((ev/"source-manifest.json").read_text())
results=[]
for f in m["files"]:
    b=(root/f["path"]).read_bytes()
    blob=hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
    sha=hashlib.sha256(b).hexdigest()
    results.append({"path":f["path"],"blob":blob,"sha256":sha,"match":blob==f["blob"] and sha==f["sha256"]})
assert all(x["match"] for x in results)
txt=(ev/"raw-transcript.txt").read_text()
runs=len(re.findall(r"^=== RUN   TestCandidatePolicyUnionBothSides/",txt,re.M))
passes=len(re.findall(r"^    --- PASS:",txt,re.M))
assert runs==passes==63
code=(root/"portal/networkpolicy/flows_test.go").read_text()
structure=code.split("func TestCandidatePolicyStructure",1)[1]
assert "policyTypes spot checks" in structure
assert "Ports" not in structure and "Protocol" not in structure and "PodSelector" not in structure
runtime=(root/"docs/architecture/P8C_RUNTIME_READINESS_GATE_DRAFT_20261102.md").read_text()
release=(root/"docs/architecture/P8C_RELEASE_GATE_DRAFT_20261102.md").read_text()
deployment=(root/"docs/architecture/P8C_DEPLOYMENT_GATE_DRAFT_20261102.md").read_text()
assert "≤N GET, window W, interval I" in runtime
assert "не задан здесь, определяется execute-gate" in release
assert "SA + verb/resource/scope matrix" in deployment and "portal-reader" not in deployment
print(json.dumps({"reviewed_sha":"c86f39fe6f5eb6edf17b010fdf3a32e16f669469","audit_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"files":results,"reported_go_subtest_runs":runs,"reported_go_subtest_passes":passes,"go_functions":2,"go_independently_executed":False,"unfilled_required_draft_fields_confirmed":True,"structure_guard_missing_ports_protocol_peer_selector_checks":True,"scope":"source/evidence verification; not runtime acceptance"},ensure_ascii=False,indent=2))
