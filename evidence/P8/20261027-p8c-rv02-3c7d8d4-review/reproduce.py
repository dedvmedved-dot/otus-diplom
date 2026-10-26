#!/usr/bin/env python3
"""Mock-only review observations. Exit0 means assertions about this revision hold."""
import copy, datetime, hashlib, json, pathlib, subprocess, tempfile
from types import SimpleNamespace
from unittest import mock
import supplemental as s
import supplemental_test as f

P=pathlib.Path(__file__).parent
CANARY="SYNTHETIC_SP_REVIEW_CANARY_NOT_A_SECRET"
D=copy.deepcopy(f.CALICO_DISC)
for item in D["resources"]:
    item["kind"]={"networkpolicies":"NetworkPolicy","globalnetworkpolicies":"GlobalNetworkPolicy","felixconfigurations":"FelixConfiguration"}[item["name"]]
PD=copy.deepcopy(f.POLICY_DISC)
PD["resources"][0].update(kind="AdminNetworkPolicy",namespaced=False)
POD=copy.deepcopy(f.POD);POD["kind"]="Pod"
POD["status"]={
    "containerStatuses":[{"name":"postgres","imageID":"containerd://sha256:"+"a"*64}],
    "initContainerStatuses":[{"name":"bootstrap","imageID":"containerd://sha256:"+"b"*64}]}
def res(body, rc=0, err=""):
    return SimpleNamespace(stdout=body if isinstance(body,str) else json.dumps(body),returncode=rc,stderr=err)
def run(overrides=None):
    overrides=overrides or {}
    calls=[]
    defaults={"D1":res(D),"D2":res(PD),"C1":res(f.OS),"C2":res(f.CL),
              "C3":res({"items":[f.NP]}),"C4":res({"items":[f.GNP]}),
              "C5":res(f.FELIX),"S1":res({"items":[POD]}),"S2":res({"items":[POD]})}
    command_id={tuple(tail):rid for rid,_,tail,_,_ in s.READ_CONTRACT}
    with tempfile.TemporaryDirectory() as td:
        out=pathlib.Path(td)/"out"
        def fake(argv,**kwargs):
            rid=command_id[tuple(argv[4:])];calls.append(rid)
            answer=overrides.get(rid,defaults[rid])
            if isinstance(answer,BaseException):raise answer
            return answer
        with mock.patch.object(s.shutil,"which",return_value="/mock/kubectl"),mock.patch.object(s.subprocess,"run",side_effect=fake),mock.patch.object(s.sys,"argv",["supplemental.py","--context","fixture","--output",str(out)]):
            rc=s.main()
        rows=[json.loads(x) for x in (out/"supplemental.jsonl").read_text().splitlines()]
    return {"rc":rc,"calls":calls,"categories":{r["id"]:r["category"] for r in rows},
            "outputs":{r["id"]:r["output"] for r in rows},
            "canary_retained":CANARY in json.dumps(rows)}
def compact(result):
    return {k:v for k,v in result.items() if k!="outputs"}
obs={}
for key,value in {
    "wrong_group":res({"kind":"APIResourceList","groupVersion":"wrong/v9","resources":[]}),
    "forbidden":res("",1,"Forbidden "+CANARY),
    "timeout":subprocess.TimeoutExpired(["kubectl"],20),
    "non_json":res("malformed "+CANARY)
}.items():
    result=run({"D1":value})
    assert result["rc"]==1 and not any(x in result["calls"] for x in ["C3","C4","C5"])
    assert not result["canary_retained"]
    obs["closed_"+key]=compact(result)
for key,change in {
    "wrong_scope":lambda d:d["resources"][0].update(namespaced=False),
    "missing_list_verb":lambda d:d["resources"][0].update(verbs=["get"]),
    "wrong_resource_kind":lambda d:d["resources"][0].update(kind="WrongKind"),
    "missing_felix_resource":lambda d:d.update(resources=d["resources"][:2])
}.items():
    disc=copy.deepcopy(D);change(disc)
    result=run({"D1":res(disc)})
    assert result["rc"]==0 and all(x in result["calls"] for x in ["C3","C4","C5"])
    obs[key]=compact(result)
result=run()
assert result["rc"]==0
obs["policy_api_served_no_projection_or_unsupported_stop"]=compact(result)
bad=copy.deepcopy(f.NP)
bad["spec"]["ingress"][0]["source"]["serviceAccounts"]={"names":["default"],"extra":{"token":CANARY}}
result=run({"C3":res({"items":[bad]})})
assert result["rc"]==0 and result["canary_retained"]
obs["service_accounts_raw_member_leak"]=compact(result)
bad=copy.deepcopy(POD)
bad["spec"]["containers"][0]["ports"]=[{"containerPort":{"token":CANARY},"name":{"password":CANARY}}]
result=run({"S1":res({"items":[bad]})})
assert result["rc"]==0 and result["canary_retained"]
obs["pod_port_leaf_leak"]=compact(result)
base=copy.deepcopy(f.NP)
base["spec"]["ingress"][0]["source"]={"selector":"all()"}
restrict=copy.deepcopy(base)
restrict["spec"]["tier"]="security"
restrict["spec"]["ingress"][0]["source"]["notSelector"]="app == 'excluded'"
a=s.project_config("calico_np",json.dumps({"items":[base]}))
b=s.project_config("calico_np",json.dumps({"items":[restrict]}))
assert a==b
result=run({"C3":res({"items":[restrict]})})
assert result["rc"]==0 and result["categories"]["C3"] is None
obs["tier_and_notSelector_silent_loss"]={"identical_outputs":True,"rc":result["rc"],"category":result["categories"]["C3"]}
number=copy.deepcopy(base);number["spec"]["ingress"][0]["protocol"]=17
try:s.project_config("calico_np",json.dumps({"items":[number]}));o="accepted"
except ValueError as e:o=str(e)
assert o=="ingress.protocol not a string"
obs["schema_valid_numeric_protocol_rejected"]=o
result=run()
pod_out=json.loads(result["outputs"]["S1"])[0]
assert pod_out["containers"][0]["imageID"] is None and pod_out["initContainers"][0]["imageID"] is None
obs["status_image_ids_lost"]={"regular":pod_out["containers"][0]["imageID"],"init":pod_out["initContainers"][0]["imageID"]}
bad=copy.deepcopy(POD);bad["spec"]["containers"]=[None,7]
result=run({"S1":res({"items":[bad]})})
assert result["rc"]==0 and json.loads(result["outputs"]["S1"])[0]["containers"]==[]
obs["malformed_containers_silently_dropped"]=compact(result)
bad=copy.deepcopy(POD);bad["kind"]="Service";bad["metadata"]["namespace"]=""
result=run({"S1":res({"items":[bad]})})
assert result["rc"]==0
obs["pod_wrong_kind_empty_namespace_accepted"]=compact(result)
bad=copy.deepcopy(f.OS);bad["metadata"]["name"]="different-object"
result=run({"C1":res(bad)})
assert result["rc"]==0
obs["named_get_identity_not_bound"]=compact(result)
result=run({"D1":res(D),"C3":res({"items":[]}),"C4":res({"items":[]})})
assert result["rc"]==0
obs["no_runtime_version_dependency"]={"reads":[x[0] for x in s.READ_CONTRACT],
    "calico_identity_read":False,"software_identity_gate":False}
hashes={}
for n in ["supplemental.py","supplemental_test.py"]:
    v=(P/n).read_bytes()
    hashes[n]={"sha256":hashlib.sha256(v).hexdigest(),"git_blob":hashlib.sha1(b"blob "+str(len(v)).encode()+b"\0"+v).hexdigest()}
report={"review_head":"3c7d8d44dff9e4cb4397ec85eed76d6b7148fa79",
    "source_sha":"1b50e4da8e48f4fbae45f2fddd4763910cf8a33c",
    "hashes":hashes,"observations":obs,
    "result":"PARTIAL_FIXES_CONFIRMED_AND_REMAINING_DEFECTS_REPRODUCED","cluster_calls":0}
(P/"observations.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report,indent=2))
