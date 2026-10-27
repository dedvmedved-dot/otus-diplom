#!/usr/bin/env python3
"""Offline observations at e592b57. Kubectl subprocess is always mocked."""
import copy,hashlib,json,subprocess,warnings
from pathlib import Path
import supplemental_test as t
warnings.simplefilter("ignore",ResourceWarning)
out={}
PIN="quay.io/calico/node@sha256:f4fafd8ba641d96c5a91b01e5a519117d77d55dee789a3562ba3ad4aa125b36a"
def run(name,overrides,ids):
 rc,calls,rows=t.run(overrides);by={r["id"]:r for r in rows}
 out[name]={"exit":rc,"dependent_calls":[x for x in calls if x in ("C3","C4","C5")],
 "focus":{x:{"category":by[x]["category"],"output":by[x]["output"]} for x in ids}}
def identity(name,image,iid,count=1):
 p=copy.deepcopy(t.POD);p["spec"]["containers"][0]["image"]=image
 p["status"]["containerStatuses"][0]["imageID"]=iid
 pods=[]
 for i in range(count):
  q=copy.deepcopy(p);q["metadata"]["name"]="calico-node-"+str(i);pods.append(q)
 run(name,{"I1":t.R(0,json.dumps({"items":pods}))},["I1","C3","C4","C5"])
# Synthetic digest syntax is not evidence of relation to the repository manifest.
for ref,label in [(PIN,"pin"),("quay.io/calico/node:v3.32.0","tag")]:
 for char in ("a","b"):
  identity(label+"_unbound_consistent_"+char,ref,"containerd://sha256:"+char*64,3)
identity("untrusted_registry_blocked","other.example/calico/node:v3.32.0","containerd://sha256:"+"a"*64)
identity("malformed_digest_blocked",PIN,"not-a-runtime-digest")
identity("source_pin_same_digest_candidate",PIN,"containerd://sha256:"+PIN.split("@sha256:")[1])
# Check the generic unsupported-field boundary using synthetic future keys.
# These are not claimed to exist in the v3.32 schema or in the live cluster.
paths=[("spec",["spec"]),("rule",["spec","ingress",0]),
 ("entity",["spec","ingress",0,"source"]),
 ("http",["spec","ingress",0,"http"]),
 ("http_path",["spec","ingress",0,"http","paths",0]),
 ("icmp",["spec","ingress",0,"icmp"]),
 ("serviceAccounts",["spec","ingress",0,"source","serviceAccounts"]),
 ("services",["spec","ingress",0,"source","services"])]
for label,path in paths:
 b=copy.deepcopy(t.NP);rule=b["spec"]["ingress"][0]
 rule["http"]={"methods":["GET"],"paths":[{"exact":"/health"}]}
 rule["icmp"]={"type":8}
 rule["source"]["serviceAccounts"]={"names":["reader"]}
 rule["source"]["services"]={"name":"service","namespace":"portal"}
 changed=copy.deepcopy(b);node=changed
 for k in path:node=node[k]
 node["futureSemanticRestriction"]="SYNTHETIC_UNSUPPORTED_FIELD_NOT_A_SECRET"
 pa=t.inv.project_config("calico_np",t.enc(b),"list",None)
 pb=t.inv.project_config("calico_np",t.enc(changed),"list",None)
 run("unknown_field_"+label,{"C3":t.R(0,t.enc(changed))},["C3"])
 out["unknown_field_"+label]["same_projection"]=json.loads(pa)==json.loads(pb)
# Preserve accepted examples and boundaries.
for key in ("icmp","notICMP"):
 b=copy.deepcopy(t.NP);b["spec"]["ingress"][0]["protocol"]="ICMP"
 c=copy.deepcopy(b);c["spec"]["ingress"][0][key]={"type":8}
 a=t.inv.project_config("calico_np",t.enc(b),"list",None);z=t.inv.project_config("calico_np",t.enc(c),"list",None)
 run(key+"_preserved",{"C3":t.R(0,t.enc(c))},["C3"])
 out[key+"_preserved"]["same_projection"]=json.loads(a)==json.loads(z)
g=copy.deepcopy(t.GNP);g["spec"]["namespaceSelector"]="team == 'restricted'"
run("gnp_namespace_selector_preserved",{"C4":t.R(0,t.enc(g))},["C4"])
for rid,ns in (("I1","other"),("S1","other"),("S2","other")):
 b=copy.deepcopy(t.POD);b["metadata"]["namespace"]=ns
 run(rid+"_wrong_namespace_blocked",{rid:t.R(0,t.enc(b))},[rid])
for value in (False,0,{},[None]):
 b=copy.deepcopy(t.NP);b["spec"]["ingress"][0]["http"]={"paths":value}
 run("http_paths_"+repr(value),{"C3":t.R(0,t.enc(b))},["C3"])
for port in (-1,65536):
 b=copy.deepcopy(t.POD);b["spec"]["containers"][0]["ports"][0]["containerPort"]=port
 run("port_"+str(port),{"I1":t.R(0,t.enc(b))},["I1"])
for label,value in [
 ("forbidden",t.R(1,"SYNTHETIC_RAW","Forbidden")),
 ("connection",t.R(1,"SYNTHETIC_RAW","connection refused")),
 ("timeout",subprocess.TimeoutExpired("fixed-read",20,output="SYNTHETIC_RAW")),
 ("oserror",OSError("SYNTHETIC_RAW")),
 ("nonjson",t.R(0,"SYNTHETIC_RAW"))]:
 run("D1_"+label,{"D1":value},["D1","C3","C4","C5"])
for v in out.values():
 assert "SYNTHETIC_RAW" not in json.dumps(v)
out["read_contract"]=[{"id":r[0],"argv":r[2],"deps":r[4]} for r in t.inv.READ_CONTRACT]
out["source_hashes"]={}
for f in ("supplemental.py","supplemental_test.py"):
 b=Path(f).read_bytes()
 out["source_hashes"][f]={"sha256":hashlib.sha256(b).hexdigest(),"git_blob":hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()}
Path("observations.json").write_text(json.dumps(out,indent=2)+"\n")
for k,v in out.items():
 if "exit" in v:
  print(json.dumps({"case":k,"exit":v["exit"],"dependent_calls":v["dependent_calls"],
  "categories":{k2:v2["category"] for k2,v2 in v["focus"].items()},
  **({"same_projection":v["same_projection"]} if "same_projection" in v else {})}))
print(json.dumps({"source_hashes":out["source_hashes"]}))
