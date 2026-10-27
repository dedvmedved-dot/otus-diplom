#!/usr/bin/env python3
"""Review 010ff33; routes fixture responses by independently fixed argv literals."""
import copy,hashlib,json,re,subprocess,tempfile,warnings
from pathlib import Path
from unittest import mock
import supplemental_test as t
warnings.simplefilter("ignore",ResourceWarning)
contract={
"D1":["get","--raw","/apis/crd.projectcalico.org/v1"],
"D2":["get","--raw","/apis/policy.networking.k8s.io/v1alpha2"],
"I1":["get","pods","-n","kube-system","-l","k8s-app=calico-node","-o","json"],
"C1":["get","--raw","/apis/barmancloud.cnpg.io/v1/namespaces/portal/objectstores/portal-db-backup"],
"C2":["get","--raw","/apis/postgresql.cnpg.io/v1/namespaces/portal/clusters/portal-db"],
"C3":["get","--raw","/apis/crd.projectcalico.org/v1/networkpolicies"],
"C4":["get","--raw","/apis/crd.projectcalico.org/v1/globalnetworkpolicies"],
"C5":["get","--raw","/apis/crd.projectcalico.org/v1/felixconfigurations/default"],
"S1":["get","pods","-n","portal","-l","cnpg.io/cluster=portal-db","-o","json"],
"S2":["get","pods","-n","cnpg-system","-l","app=barman-cloud","-o","json"]}
route={tuple(v):k for k,v in contract.items()}
default={"D1":t.CALICO_DISC,"D2":t.POLICY_DISC,"I1":{"items":[t.POD]},"C1":t.OS,"C2":t.CL,"C3":{"items":[t.NP]},"C4":{"items":[t.GNP]},"C5":t.FELIX,"S1":{"items":[t.POD_PORTAL]},"S2":{"items":[t.POD_CNPG]}}
def run(overrides=None):
 calls=[];overrides=overrides or {}
 def fake(argv,**kw):
  assert argv[:4]==["kubectl","--context","review-context","--request-timeout=15s"]
  rid=route[tuple(argv[4:])];calls.append({"id":rid,"argv":argv})
  value=overrides.get(rid,default[rid])
  if isinstance(value,Exception):raise value
  if isinstance(value,t.R):return value
  return t.R(0,json.dumps(value))
 with tempfile.TemporaryDirectory() as tmp:
  target=Path(tmp)/"new"
  with mock.patch.object(t.inv.shutil,"which",return_value="/mock/kubectl"),mock.patch.object(t.inv.subprocess,"run",side_effect=fake),mock.patch.object(t.inv.sys,"argv",["supplemental.py","--context","review-context","--output",str(target)]):
   rc=t.inv.main()
  rows=[json.loads(s) for s in (target/"supplemental.jsonl").read_text().splitlines()]
 return {"exit":rc,"calls":calls,"rows":rows}
obs={"literal_main_path":run()}
assert obs["literal_main_path"]["exit"]==0
assert [c["id"] for c in obs["literal_main_path"]["calls"]]==list(contract)
bad=copy.deepcopy(t.CALICO_DISC);bad["groupVersion"]="wrong/v1"
obs["bad_discovery"]=run({"D1":bad})
assert not any(c["id"] in ("C3","C4","C5") for c in obs["bad_discovery"]["calls"])
bad=copy.deepcopy(t.OS);bad["apiVersion"]="barmancloud.cnpg.io/v999"
obs["wrong_response_version"]=run({"C1":bad})
for name,value in [
("forbidden",t.R(1,"SYNTHETIC_RAW","Forbidden")),
("api_not_served",t.R(1,"SYNTHETIC_RAW","the server could not find the requested resource")),
("connection",t.R(1,"SYNTHETIC_RAW","connection refused")),
("timeout",subprocess.TimeoutExpired("literal",20,output="SYNTHETIC_RAW"))]:
 obs["C1_"+name]=run({"C1":value})
 assert "SYNTHETIC_RAW" not in json.dumps(obs["C1_"+name])
bad=copy.deepcopy(t.POD);bad["status"]["containerStatuses"][0]["imageID"]="containerd://sha256:"+"b"*64
obs["valid_unsupported_identity"]=run({"I1":{"items":[bad]}})
assert not any(c["id"] in ("C3","C4","C5") for c in obs["valid_unsupported_identity"]["calls"])
matrix=Path("coverage-matrix.md").read_text();tests=Path("supplemental_test.py").read_text()
refs=sorted(set(re.findall(r"\btest_[A-Za-z0-9_]+",matrix)))
defs=sorted(set(re.findall(r"def (test_[A-Za-z0-9_]+)",tests)))
obs["matrix_audit"]={"mentioned_test_ids":refs,"missing_test_definitions":sorted(set(refs)-set(defs)),"defined_test_count":len(defs),"stale_31_count":"31/31" in matrix,"stale_version_qualified":"resource.version.group" in matrix,"stale_evidence_root":"20261027T060000Z" in matrix,"literal_api_test_in_matrix":"test_literal_api_paths" in matrix}
obs["hashes"]={}
for f in ("supplemental.py","supplemental_test.py"):
 b=Path(f).read_bytes();obs["hashes"][f]={"sha256":hashlib.sha256(b).hexdigest(),"git_blob":hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()}
Path("observations.json").write_text(json.dumps(obs,indent=2)+"\n")
print(json.dumps({k:{"exit":v["exit"],"categories":{r["id"]:r["category"] for r in v["rows"]},"I1_output":next(r["output"] for r in v["rows"] if r["id"]=="I1") if k=="valid_unsupported_identity" else None} for k,v in obs.items() if "exit" in v},indent=2))
print(json.dumps({"matrix_audit":obs["matrix_audit"],"hashes":obs["hashes"]},indent=2))
