#!/usr/bin/env python3
"""Mock-only observations for 3262a9b. Exit0 confirms observations, not acceptance."""
import copy, hashlib, json, pathlib, subprocess, tempfile
from types import SimpleNamespace
from unittest import mock
import supplemental as s
import supplemental_test as f
P=pathlib.Path(__file__).parent
CANARY="SYNTHETIC_REVIEW_CANARY_NOT_A_CREDENTIAL"
def res(body,rc=0,err=""):
    return SimpleNamespace(stdout=body if isinstance(body,str) else json.dumps(body),returncode=rc,stderr=err)
def run(overrides=None):
    overrides=overrides or {}; calls=[]
    defaults={"D1":res(f.CALICO_DISC),"D2":res(f.POLICY_DISC),"I1":res({"items":[f.POD]}),
      "C1":res(f.OS),"C2":res(f.CL),"C3":res({"items":[f.NP]}),"C4":res({"items":[f.GNP]}),
      "C5":res(f.FELIX),"S1":res({"items":[f.POD]}),"S2":res({"items":[f.POD]})}
    ids={tuple(tail):rid for rid,_,tail,_,_,_,_ in s.READ_CONTRACT}
    with tempfile.TemporaryDirectory() as td:
        out=pathlib.Path(td)/"out"
        def fake(argv,**kwargs):
            rid=ids[tuple(argv[4:])];calls.append(rid);ans=overrides.get(rid,defaults[rid])
            if isinstance(ans,BaseException):raise ans
            return ans
        with mock.patch.object(s.shutil,"which",return_value="/mock/kubectl"),mock.patch.object(s.subprocess,"run",side_effect=fake),mock.patch.object(s.sys,"argv",["supplemental.py","--context","fixture","--output",str(out)]):
            rc=s.main()
        rows=[json.loads(line) for line in (out/"supplemental.jsonl").read_text().splitlines()]
    return {"rc":rc,"calls":calls,"categories":{r["id"]:r["category"] for r in rows},
            "outputs":{r["id"]:r["output"] for r in rows},"canary_retained":CANARY in json.dumps(rows)}
def brief(r):return {k:v for k,v in r.items() if k!="outputs"}
obs={}
bad=copy.deepcopy(f.POD);bad["spec"]["containers"][0]["image"]="other.example/unreviewed:v999"
bad["status"]["containerStatuses"][0]["imageID"]="containerd://sha256:"+"b"*64
nostatus=copy.deepcopy(f.POD);nostatus.pop("status")
for key,body in {"empty_identity":{"items":[]},"unreviewed_identity":{"items":[bad]},
                 "missing_image_id":{"items":[nostatus]},"mixed_identity":{"items":[f.POD,bad]}}.items():
    r=run({"I1":res(body)})
    assert r["rc"]==0 and all(x in r["calls"] for x in ("C3","C4","C5"))
    obs[key]=brief(r)
d=copy.deepcopy(f.CALICO_DISC)
for resource in d["resources"]:resource.pop("namespaced")
r=run({"D1":res(d)});assert r["rc"]==0 and "C5" in r["calls"]
obs["missing_discovery_scope"]=brief(r)
d=copy.deepcopy(f.CALICO_DISC);d["resources"][0]["namespaced"]=False
r=run({"D1":res(d)});assert r["rc"]==1 and "C3" not in r["calls"]
obs["closed_explicit_wrong_scope"]=brief(r)
for key,first in {"forbidden":res("",1,"Forbidden "+CANARY),
                  "timeout":subprocess.TimeoutExpired(["kubectl"],20),
                  "non_json":res("not JSON "+CANARY)}.items():
    r=run({"D1":first});assert r["rc"]==1 and "C3" not in r["calls"] and not r["canary_retained"]
    obs["closed_"+key]=brief(r)
pd=copy.deepcopy(f.POLICY_DISC);pd["resources"]=[{"name":"adminnetworkpolicies","kind":"AdminNetworkPolicy","namespaced":False,"verbs":["get","list"]}]
r=run({"D2":res(pd)});assert r["rc"]==1 and r["categories"]["D2"]=="PARSE_ERROR" and r["outputs"]["D2"]==""
obs["unsupported_discovery_loses_reason"]=brief(r)
base=copy.deepcopy(f.NP)
base["spec"]["ingress"][0]["source"]={"selector":"all()"}
projection=s.project_config("calico_np",json.dumps({"items":[base]}),"list",None)
mutations={
"notProtocol":lambda o:o["spec"]["ingress"][0].update(notProtocol="UDP"),
"ipVersion":lambda o:o["spec"]["ingress"][0].update(ipVersion=6),
"http":lambda o:o["spec"]["ingress"][0].update(http={"methods":["GET"]}),
"serviceAccountSelector":lambda o:o["spec"].update(serviceAccountSelector="role == 'reader'"),
"services":lambda o:o["spec"]["ingress"][0]["source"].update(services={"name":"svc","namespace":"portal"})
}
semantic={}
for key,mutate in mutations.items():
    obj=copy.deepcopy(base);mutate(obj)
    other=s.project_config("calico_np",json.dumps({"items":[obj]}),"list",None)
    r=run({"C3":res({"items":[obj]})})
    assert other==projection and r["categories"]["C3"] is None and r["rc"]==0
    semantic[key]={"identical_output":True,"category":None,"rc":0}
obs["silent_semantic_loss"]=semantic
for rid,fixture,change in [
("C1",f.OS,lambda o:o["metadata"].update(namespace="other")),
("C2",f.CL,lambda o:o["metadata"].update(namespace="other")),
("C5",f.FELIX,lambda o:o["metadata"].update(name="other"))]:
    obj=copy.deepcopy(fixture);change(obj);r=run({rid:res(obj)})
    assert r["rc"]==0 and r["categories"][rid] is None
    obs["wrong_binding_"+rid]=brief(r)
obj=copy.deepcopy(f.POD)
obj["spec"]["containers"][0]["ports"]=[{"containerPort":"not-a-numeric-container-port","name":"port"}]
r=run({"S1":res({"items":[obj]})});assert r["rc"]==0
obs["string_container_port_accepted"]=brief(r)
obj=copy.deepcopy(f.POD);obj["status"]["containerStatuses"]=False
r=run({"I1":res({"items":[obj]})});assert r["rc"]==0 and "C3" in r["calls"]
obs["invalid_status_collapses_to_absence"]=brief(r)
# Preserve verified dataflow/typed-leaf fixes.
obj=copy.deepcopy(f.POD);obj["spec"]["initContainers"]=[{"name":"native-sidecar","image":"fixture:1","restartPolicy":"Always"}]
obj["status"]["initContainerStatuses"]=[{"name":"native-sidecar","imageID":"containerd://sha256:"+"c"*64}]
out=json.loads(s.project_config("identity",json.dumps({"items":[obj]}),"list",None))[0]
assert out["containers"][0]["imageID"]==f.POD["status"]["containerStatuses"][0]["imageID"]
assert out["initContainers"][0]["imageID"].endswith("c"*64)
obs["closed_image_id_joins"]={"regular":True,"init":True}
obj=copy.deepcopy(f.NP);obj["spec"]["ingress"][0]["source"]["serviceAccounts"]={"names":["default"],"extra":{"token":CANARY}}
r=run({"C3":res({"items":[obj]})});assert r["rc"]==0 and not r["canary_retained"]
obs["closed_service_account_canary"]=brief(r)
hashes={}
for name in ("supplemental.py","supplemental_test.py"):
    b=(P/name).read_bytes()
    hashes[name]={"sha256":hashlib.sha256(b).hexdigest(),"git_blob":hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()}
report={"reviewed_head":"3262a9b7733b120a4a06bc2931e6983695524428",
        "source_sha":"20168390748d88840ddb619ec10eb3ee07804628","hashes":hashes,"observations":obs,
        "cluster_calls":0,"result":"PARTIAL_CLOSURE_CONFIRMED; REMAINING_DEFECTS_REPRODUCED"}
(P/"observations.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps({"hashes":hashes,"observations":list(obs),"result":report["result"]},indent=2))
