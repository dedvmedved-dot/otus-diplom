#!/usr/bin/env python3
"""Offline review of exact 8598f73 connector bytes. All subprocess calls mocked."""
import copy, hashlib, json, warnings
from pathlib import Path
import supplemental_test as t
warnings.simplefilter("ignore", ResourceWarning)
obs={}
def run_case(name, overrides, focus):
    rc,calls,rows=t.run(overrides)
    by={r["id"]:r for r in rows}
    obs[name]={"exit":rc,"dependent_calls":[x for x in calls if x in ("C3","C4","C5")],
               "focus":{x:{"category":by[x]["category"],"output":by[x]["output"]} for x in focus}}
    return by
def pod(image=None,image_id=None,ns=None):
    p=copy.deepcopy(t.POD)
    if image is not None:p["spec"]["containers"][0]["image"]=image
    if image_id is not None:p["status"]["containerStatuses"][0]["imageID"]=image_id
    if ns is not None:p["metadata"]["namespace"]=ns
    return p
def identity(name,items):
    return run_case(name,{"I1":t.R(0,json.dumps({"items":items}))},["I1","C3","C4","C5"])
pin="quay.io/calico/node@sha256:f4fafd8ba641d96c5a91b01e5a519117d77d55dee789a3562ba3ad4aa125b36a"
identity("repository_pinned_image_rejected",[pod(pin,pin)])
identity("untrusted_registry_accepted",[pod("unreviewed.example/calico/node:v3.32.0")])
identity("unreviewed_version_prefix_accepted",[pod("calico/node:v3.320.999")])
identity("arbitrary_image_id_accepted",[pod(image_id="not-a-runtime-digest")])
identity("mixed_runtime_ids_accepted",[pod(),pod(image_id="containerd://sha256:"+"b"*64)])
identity("identity_wrong_namespace_accepted",[pod(ns="other")])
other=pod();other["spec"]["containers"]=[{"name":"other","image":"unreviewed.example/other:v1"}];other.pop("status")
identity("unidentified_pod_in_identity_set_accepted",[pod(),other])
identity("empty_identity_blocked",[])
identity("missing_image_id_blocked",[dict((k,v) for k,v in pod().items() if k!="status")])
for key in ("icmp","notICMP"):
    base=copy.deepcopy(t.NP);base["spec"]["ingress"][0]["protocol"]="ICMP"
    changed=copy.deepcopy(base);changed["spec"]["ingress"][0][key]={"type":8}
    a=t.inv.project_config("calico_np",t.enc(base),"list",None)
    b=t.inv.project_config("calico_np",t.enc(changed),"list",None)
    row=run_case(key+"_silently_dropped",{"C3":t.R(0,t.enc(changed))},["C3"])
    obs[key+"_silently_dropped"]["same_projection_without_condition"]=json.loads(a)==json.loads(b)
base=copy.deepcopy(t.GNP);changed=copy.deepcopy(base);changed["spec"]["namespaceSelector"]="team == 'restricted'"
a=t.inv.project_config("calico_gnp",t.enc(base),"list",None)
b=t.inv.project_config("calico_gnp",t.enc(changed),"list",None)
run_case("gnp_namespace_selector_silently_dropped",{"C4":t.R(0,t.enc(changed))},["C4"])
obs["gnp_namespace_selector_silently_dropped"]["same_projection_without_condition"]=json.loads(a)==json.loads(b)
for rid in ("S1","S2"):
    run_case(rid+"_wrong_namespace_accepted",{rid:t.R(0,t.enc(pod(ns="other")))},[rid])
for value in (False,0,{},[None]):
    bad=copy.deepcopy(t.NP);bad["spec"]["ingress"][0]["http"]={"paths":value}
    run_case("http_paths_"+repr(value),{"C3":t.R(0,t.enc(bad))},["C3"])
for val in (-1,65536):
    bad=pod();bad["spec"]["containers"][0]["ports"][0]["containerPort"]=val
    identity("container_port_"+str(val),[bad])
d=copy.deepcopy(t.CALICO_DISC)
for r in d["resources"]:r.pop("namespaced")
run_case("missing_scope_blocked",{"D1":t.R(0,json.dumps(d))},["D1","C3","C4","C5"])
pd={"kind":"APIResourceList","groupVersion":"policy.networking.k8s.io/v1alpha2",
"resources":[{"name":"adminnetworkpolicies","kind":"AdminNetworkPolicy","namespaced":False,"verbs":["get","list"]}]}
run_case("unsupported_discovery_preserved",{"D2":t.R(0,json.dumps(pd))},["D2"])
for rid,value in [("D1",t.R(1,"SYNTHETIC_NOT_A_SECRET","forbidden")),
                  ("D2",t.R(0,"not-json"))]:
    run_case("safe_failure_"+rid,{rid:value},[rid,"C3","C4","C5"])
for rid,obj in (("C1",t.OS),("C2",t.CL),("C5",t.FELIX)):
    bad=copy.deepcopy(obj)
    if rid=="C5":bad["metadata"]["name"]="other"
    else:bad["metadata"]["namespace"]="other"
    run_case("named_binding_"+rid,{rid:t.R(0,json.dumps(bad))},[rid])
obs["request_contract"]=[{"id":r[0],"argv_tail":r[2],"deps":r[4]} for r in t.inv.READ_CONTRACT]
obs["source_hashes"]={f:{"sha256":hashlib.sha256(Path(f).read_bytes()).hexdigest(),
"git_blob":hashlib.sha1(b"blob "+str(len(Path(f).read_bytes())).encode()+b"\0"+Path(f).read_bytes()).hexdigest()}
for f in ("supplemental.py","supplemental_test.py")}
Path("observations.json").write_text(json.dumps(obs,indent=2)+"\n")
for name,o in obs.items():
    if "exit" in o:
        print(json.dumps({"case":name,"exit":o["exit"],"dependent_calls":o["dependent_calls"],
        "categories":{k:v["category"] for k,v in o["focus"].items()},
        **({"equivalent":o["same_projection_without_condition"]} if "same_projection_without_condition" in o else {})}))
print(json.dumps({"source_hashes":obs["source_hashes"]}))
