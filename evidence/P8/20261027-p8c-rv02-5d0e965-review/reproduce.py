#!/usr/bin/env python3
"""Offline targeted review of 5d0e965. No real kubectl calls."""
import copy,json,hashlib,warnings
from pathlib import Path
import supplemental_test as t
warnings.simplefilter("ignore",ResourceWarning)
obs={}
def check(name,overrides,focus):
 rc,calls,rows=t.run(overrides);r={v["id"]:v for v in rows}
 obs[name]={"exit":rc,"dependent_calls":[v for v in calls if v in ("C3","C4","C5")],
 "rows":{k:{"category":r[k]["category"],"output":r[k]["output"]} for k in focus}}
def iid(name,value):
 p=copy.deepcopy(t.POD);p["spec"]["containers"][0]["image"]="quay.io/calico/node@sha256:"+t.PINNED_HEX
 p["status"]["containerStatuses"][0]["imageID"]=value
 check(name,{"I1":t.R(0,json.dumps({"items":[p,copy.deepcopy(p)]}))},["I1","C3","C4","C5"])
iid("equal_digest_fixture","containerd://sha256:"+t.PINNED_HEX)
iid("unbound_digest_blocked","containerd://sha256:"+"b"*64)
# Representation probes, not claims about the actual runtime format or child digest.
iid("repository_qualified_same_digest","docker-pullable://quay.io/calico/node@sha256:"+t.PINNED_HEX)
iid("bare_repository_same_digest","quay.io/calico/node@sha256:"+t.PINNED_HEX)
paths=[("spec",["spec"]),("rule",["spec","ingress",0]),("entity",["spec","ingress",0,"source"]),
 ("http",["spec","ingress",0,"http"]),("http_path",["spec","ingress",0,"http","paths",0]),
 ("icmp",["spec","ingress",0,"icmp"]),("serviceAccounts",["spec","ingress",0,"source","serviceAccounts"]),
 ("services",["spec","ingress",0,"source","services"])]
for name,path in paths:
 p=copy.deepcopy(t.NP);r=p["spec"]["ingress"][0]
 r["http"]={"methods":["GET"],"paths":[{"exact":"/health"}]};r["icmp"]={"type":8}
 r["source"]["serviceAccounts"]={"names":["reader"]};r["source"]["services"]={"name":"svc","namespace":"portal"}
 v=p
 for k in path:v=v[k]
 v["futureSemanticRestriction"]="SYNTHETIC_UNKNOWN_VALUE_NOT_A_SECRET"
 check("unsupported_"+name,{"C3":t.R(0,t.enc(p))},["C3"])
for key,value in [("namespaceSelector","team == 'restricted'"),("applyOnForward",True),("doNotTrack",True),("preDNAT",True)]:
 p=copy.deepcopy(t.NP);p["spec"][key]=value
 check("namespaced_policy_global_only_"+key,{"C3":t.R(0,t.enc(p))},["C3"])
 a=t.inv.project_config("calico_np",t.enc(t.NP),"list",None)
 b=t.inv.project_config("calico_np",t.enc(p),"list",None)
 obs["namespaced_policy_global_only_"+key]["same_projection"]=json.loads(a)==json.loads(b)
# Ensure legitimate GlobalNetworkPolicy fields remain preserved.
g=copy.deepcopy(t.GNP);g["spec"].update(namespaceSelector="team == 'restricted'",applyOnForward=True,doNotTrack=True,preDNAT=True)
check("global_policy_fields_preserved",{"C4":t.R(0,t.enc(g))},["C4"])
# Deliberate non-semantic removal still works.
p=copy.deepcopy(t.NP);p["spec"]["performanceHints"]=["AssumeNeededOnEveryNode"]
p["spec"]["ingress"][0]["metadata"]={"annotations":{"synthetic":"SYNTHETIC_DROP_NOT_A_SECRET"}}
check("nonsemantic_drop",{"C3":t.R(0,t.enc(p))},["C3"])
assert "SYNTHETIC_DROP_NOT_A_SECRET" not in json.dumps(obs["nonsemantic_drop"])
obs["request_contract"]=[{"id":r[0],"argv":r[2],"deps":r[4]} for r in t.inv.READ_CONTRACT]
obs["hashes"]={}
for f in ("supplemental.py","supplemental_test.py"):
 b=Path(f).read_bytes();obs["hashes"][f]={"sha256":hashlib.sha256(b).hexdigest(),"git_blob":hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()}
Path("observations.json").write_text(json.dumps(obs,indent=2)+"\n")
for k,v in obs.items():
 if "exit" in v:
  print(json.dumps({"case":k,"exit":v["exit"],"dependent_calls":v["dependent_calls"],"categories":{n:r["category"] for n,r in v["rows"].items()},**({"same_projection":v["same_projection"]} if "same_projection" in v else {})}))
print(json.dumps({"hashes":obs["hashes"]}))
