#!/usr/bin/env python3
"""Focused offline review at f080cc3. All kubectl subprocesses mocked."""
import copy,hashlib,json,warnings
from pathlib import Path
import supplemental_test as t
warnings.simplefilter("ignore",ResourceWarning)
obs={}
def run(name,rid,obj):
 rc,calls,rows=t.run({rid:t.R(0,json.dumps(obj))})
 r=next(x for x in rows if x["id"]==rid)
 obs[name]={"exit":rc,"category":r["category"],"output":r["output"],"dependent_calls":[x for x in calls if x in ("C3","C4","C5")]}
for key,value in (("namespaceSelector","team == 'restricted'"),("applyOnForward",True),("doNotTrack",True),("preDNAT",True)):
 p=copy.deepcopy(t.NP);p["spec"][key]=value
 run("np_reject_"+key,"C3",{"items":[p]})
 assert obs["np_reject_"+key]["category"]=="UNSUPPORTED"
 g=copy.deepcopy(t.GNP);g["spec"][key]=value
 run("gnp_preserve_"+key,"C4",{"items":[g]})
 assert json.loads(obs["gnp_preserve_"+key]["output"])[0]["spec"][key]==value
paths=[("spec",["spec"]),("rule",["spec","ingress",0]),("entity",["spec","ingress",0,"source"]),
("http",["spec","ingress",0,"http"]),("http_path",["spec","ingress",0,"http","paths",0]),
("icmp",["spec","ingress",0,"icmp"]),("sa",["spec","ingress",0,"source","serviceAccounts"]),("services",["spec","ingress",0,"source","services"])]
for name,path in paths:
 p=copy.deepcopy(t.NP);r=p["spec"]["ingress"][0]
 r["http"]={"methods":["GET"],"paths":[{"exact":"/health"}]};r["icmp"]={"type":8}
 r["source"]["serviceAccounts"]={"names":["reader"]};r["source"]["services"]={"name":"svc","namespace":"portal"}
 v=p
 for k in path:v=v[k]
 v["futureSemanticRestriction"]="SYNTHETIC_NOT_SECRET"
 run("unsupported_"+name,"C3",{"items":[p]})
 assert obs["unsupported_"+name]["category"]=="UNSUPPORTED"
 assert "SYNTHETIC_NOT_SECRET" not in obs["unsupported_"+name]["output"]
p=copy.deepcopy(t.OS);p["apiVersion"]="barmancloud.cnpg.io/v999"
run("wrong_response_version_rejected","C1",p)
assert obs["wrong_response_version_rejected"]["category"]=="PARSE_ERROR"
p=copy.deepcopy(t.POD);p["status"]["containerStatuses"][0]["imageID"]="containerd://sha256:"+"b"*64
run("valid_but_unbound_identity","I1",{"items":[p]})
expected={
"C1":"/apis/barmancloud.cnpg.io/v1/namespaces/portal/objectstores/portal-db-backup",
"C2":"/apis/postgresql.cnpg.io/v1/namespaces/portal/clusters/portal-db",
"C3":"/apis/crd.projectcalico.org/v1/networkpolicies",
"C4":"/apis/crd.projectcalico.org/v1/globalnetworkpolicies",
"C5":"/apis/crd.projectcalico.org/v1/felixconfigurations/default"}
obs["requests"]=[{"id":r[0],"actual_argv":r[2],"expected_fixed_raw_path":expected[r[0]],
"uses_expected_raw_path":r[2]==["get","--raw",expected[r[0]]]} for r in t.inv.READ_CONTRACT if r[0] in expected]
obs["hashes"]={}
for f in ("supplemental.py","supplemental_test.py"):
 b=Path(f).read_bytes();obs["hashes"][f]={"sha256":hashlib.sha256(b).hexdigest(),"git_blob":hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()}
Path("observations.json").write_text(json.dumps(obs,indent=2)+"\n")
print(json.dumps({"cases":{k:{"exit":v["exit"],"category":v["category"]} for k,v in obs.items() if "exit" in v},"requests":obs["requests"],"hashes":obs["hashes"]},indent=2))
