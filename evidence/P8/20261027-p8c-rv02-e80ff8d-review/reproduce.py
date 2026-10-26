#!/usr/bin/env python3
"""Offline observation harness for exact e80ff8d supplemental.py; never calls kubectl.
Exit 0 means the documented observations were reproduced, not collector acceptance.
"""
import copy, hashlib, json, pathlib, subprocess, sys, tempfile
from unittest import mock
from types import SimpleNamespace
import supplemental as s

HERE=pathlib.Path(__file__).parent
CANARY="SYNTHETIC_PHASE2_CANARY_NOT_A_SECRET"
OS={"apiVersion":"barmancloud.cnpg.io/v1","kind":"ObjectStore",
    "metadata":{"name":"portal-db-backup","namespace":"portal"},
    "spec":{"configuration":{"endpointURL":"https://s3.example.test","destinationPath":"s3://backup/"}}}
CL={"apiVersion":"postgresql.cnpg.io/v1","kind":"Cluster",
    "metadata":{"name":"portal-db","namespace":"portal"},
    "spec":{"plugins":[{"name":"barman-cloud.cloudnative-pg.io","isWALArchiver":True,
    "parameters":{"barmanObjectName":"portal-db-backup"}}]}}
NP={"apiVersion":"crd.projectcalico.org/v1","kind":"NetworkPolicy",
    "metadata":{"name":"n","namespace":"portal"},"spec":{"selector":"all()","ingress":[],"egress":[],"types":["Ingress"]}}
def encoded(item):
    return json.dumps({"items":[item]})
def response(text, rc=0, err=""):
    return SimpleNamespace(stdout=text, returncode=rc, stderr=err)
def main_case(first, second=None, config_item=None):
    calls=[]
    with tempfile.TemporaryDirectory() as td:
        path=pathlib.Path(td)/"out"
        def fake(argv,**kwargs):
            index=len(calls); calls.append(argv)
            if index==0:
                if isinstance(first,BaseException): raise first
                return first
            if index==1:
                return second or response(json.dumps({"kind":"APIResourceList","groupVersion":"policy.networking.k8s.io/v1alpha2","resources":[]}))
            key=s.READ_CONTRACT[index][3]
            if key=="objectstore_configuration": return response(encoded(config_item or OS))
            if key=="cluster_plugins": return response(encoded(CL))
            return response('{"items":[]}')
        with mock.patch.object(s.shutil,"which",return_value="/mock/kubectl"), mock.patch.object(s.subprocess,"run",side_effect=fake), mock.patch.object(s.sys,"argv",["supplemental.py","--context","fixture","--output",str(path)]):
            rc=s.main()
        rows=[json.loads(line) for line in (path/"supplemental.jsonl").read_text().splitlines()]
    return {"rc":rc,"calls":len(calls),"config_calls":sum("get" in a and "--raw" not in a for a in calls),
            "categories":[r["category"] for r in rows],
            "canary_retained":CANARY in json.dumps(rows),"first_output":rows[0]["output"]}

observations={}
observations["wrong_discovery_identity"]=main_case(response(json.dumps({"kind":"APIResourceList","groupVersion":"wrong.invalid/v9","resources":[]})))
assert observations["wrong_discovery_identity"]["rc"]==0
assert observations["wrong_discovery_identity"]["config_calls"]==4
observations["discovery_forbidden"]=main_case(response("",1,"Forbidden "+CANARY))
assert observations["discovery_forbidden"]["rc"]==1 and observations["discovery_forbidden"]["config_calls"]==4
assert not observations["discovery_forbidden"]["canary_retained"]
observations["discovery_timeout"]=main_case(subprocess.TimeoutExpired(["kubectl"],20))
assert observations["discovery_timeout"]["categories"][0]=="TIMEOUT" and observations["discovery_timeout"]["config_calls"]==4
observations["non_json_discovery"]=main_case(response("not JSON "+CANARY))
assert observations["non_json_discovery"]["rc"]==0 and observations["non_json_discovery"]["canary_retained"]
observations["extra_discovery_member"]=main_case(response(json.dumps({"kind":"APIResourceList","groupVersion":"crd.projectcalico.org/v1","resources":[],"unexpected":CANARY})))
assert observations["extra_discovery_member"]["canary_retained"]
policy_results={}
for field,value in {"selector":{"password":CANARY},"order":{"value":CANARY},"ingress":[{"action":"Allow","metadata":{"annotations":{"note":CANARY}}}],"egress":[{"action":"Allow","unexpected":{"token":CANARY}}],"types":[{"value":CANARY}]}.items():
    obj=copy.deepcopy(NP);obj["spec"][field]=value
    result=s.project_list("calico_np",encoded(obj))
    policy_results[field]={"accepted":True,"canary_retained":CANARY in result}
assert all(v["canary_retained"] for v in policy_results.values())
observations["untyped_policy_fields"]=policy_results
gnp=copy.deepcopy(NP);gnp["kind"]="GlobalNetworkPolicy";del gnp["metadata"]["namespace"]
try: s.project_list("calico_gnp",encoded(gnp)); outcome="accepted"
except ValueError as e: outcome=str(e)
assert outcome=="metadata.namespace required"
observations["valid_cluster_scoped_gnp"]=outcome
dropped=s.project_list("calico_np",json.dumps({"items":[None,7,"bad"]}))
assert dropped=="[]"
observations["malformed_items_silently_dropped"]=dropped
wrong=copy.deepcopy(OS);wrong["apiVersion"]="wrong.invalid/v99"
assert json.loads(s.project_list("objectstore_configuration",encoded(wrong)))[0]["kind"]=="ObjectStore"
observations["wrong_object_api_version"]="accepted"
bad=copy.deepcopy(OS);bad["spec"]["configuration"]["s3Credentials"]={"accessKeyId":False}
got=json.loads(s.project_list("objectstore_configuration",encoded(bad)))[0]
assert got["spec"]["configuration"]["s3AccessKeyIdRef"] is None
observations["false_secret_ref"]="accepted_as_null"
missing=copy.deepcopy(OS);del missing["spec"]
assert json.loads(s.project_list("objectstore_configuration",encoded(missing)))[0]["spec"]["configuration"]["endpointURL"] is None
observations["missing_required_spec"]="accepted_as_empty_configuration"
empty_ns=copy.deepcopy(OS);empty_ns["metadata"]["namespace"]=""
assert json.loads(s.project_list("objectstore_configuration",encoded(empty_ns)))[0]["metadata"]["namespace"]==""
observations["empty_namespace"]="accepted"
hashes={}
for name in ("supplemental.py","supplemental_test.py"):
    b=(HERE/name).read_bytes()
    hashes[name]={"sha256":hashlib.sha256(b).hexdigest(),
                 "git_blob":hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()}
out={"reviewed_head":"e80ff8dc17cfbce611322c195278d7c715281b24",
     "source_sha":"2c3114a0f814274c3992b79d7955d21ae0030c98",
     "hashes":hashes,"observations":observations,
     "cluster_calls":0,"result":"DEFECTS_REPRODUCED; NOT_APPROVED_FOR_LIVE"}
(HERE/"observations.json").write_text(json.dumps(out,indent=2)+"\n")
print(json.dumps(out,indent=2))
