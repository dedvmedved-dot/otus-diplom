#!/usr/bin/env python3
"""Mock-only exhaustive observations for previously requested used-field boundary."""
import copy, json, subprocess, tempfile
from pathlib import Path
from unittest import mock
import inventory as inv
CANARY = "SYNTHETIC_REVIEW_CANARY_NOT_A_CREDENTIAL"
BAD = {"unexpected": CANARY}
RES = {v:k for k,v in inv.KIND_BY_RESOURCE.items()}
SPECS = {
 "NetworkPolicy":{"podSelector":{},"policyTypes":["Ingress"],"ingress":[{"from":[{"ipBlock":{"cidr":"10.0.0.0/24","except":[]}}],"ports":[{"port":8000,"protocol":"TCP","endPort":8010}]}]},
 "GatewayClass":{"controllerName":"gateway.envoyproxy.io/gatewayclass-controller"},
 "Gateway":{"gatewayClassName":"eg","listeners":[{"name":"http","port":80,"protocol":"HTTP"}]},
 "EnvoyProxy":{},
 "Cluster":{"instances":3,"storage":{"size":"10Gi"},"walStorage":{"size":"1Gi"},"monitoring":{"enablePodMonitor":True}},
 "ObjectStore":{"data":{"endpointURL":"https://s3.example.invalid:9000","destinationPath":"s3://bucket","s3Credentials":{"name":"ref"}}},
}
def fixture(kind):
 return {"apiVersion":"fixture/v1","kind":kind,"metadata":{"name":"example","namespace":"portal","labels":{"app":"portal"}},
         "spec":copy.deepcopy(SPECS[kind]),"status":{"phase":"Ready","readyInstances":3,"conditions":[{"type":"Ready","status":"True","reason":"Ready"}]}}
def assign(obj,path,value):
 parts=path.split(".");cur=obj
 for part in parts[:-1]:
  key=int(part) if isinstance(cur,list) else part
  if isinstance(cur,dict) and key not in cur:cur[key]={}
  cur=cur[key]
 cur[int(parts[-1]) if isinstance(cur,list) else parts[-1]]=copy.deepcopy(value)
def run(kind,item,completed=None):
 with tempfile.TemporaryDirectory() as tmp:
  dest=Path(tmp)/"new"
  command=(["get",RES[kind],"-A","-o","json"],RES[kind])
  result=completed or subprocess.CompletedProcess([],0,json.dumps({"items":[item]}),"")
  with mock.patch.object(inv,"COMMANDS",[command]), mock.patch.object(inv.shutil,"which",return_value="/mock/kubectl"), mock.patch.object(inv.subprocess,"run",return_value=result), mock.patch.object(inv.sys,"argv",["inventory.py","--context","mock","--output",str(dest)]):
   code=inv.main()
  rows=[json.loads(s) for s in (dest/"inventory.jsonl").read_text().splitlines()]
  return {"exit":code,"category":rows[0]["category"],"output_empty":rows[0]["output"]=="",
          "canary_retained":CANARY in rows[0]["output"],"output":rows[0]["output"]}
cases=[
 ("NetworkPolicy","metadata.namespace",BAD),("NetworkPolicy","metadata.labels.app",BAD),
 ("NetworkPolicy","spec.podSelector.matchLabels.app",BAD),
 ("NetworkPolicy","spec.podSelector.matchExpressions",[{"key":"app","operator":"In","values":["portal"],"unexpected":CANARY}]),
 ("NetworkPolicy","spec.policyTypes",BAD),
 ("NetworkPolicy","spec.ingress.0.from.0.ipBlock.cidr",BAD),
 ("NetworkPolicy","spec.ingress.0.from.0.ipBlock.except",BAD),
 ("NetworkPolicy","spec.ingress.0.ports.0.port",BAD),
 ("NetworkPolicy","spec.ingress.0.ports.0.protocol",BAD),
 ("NetworkPolicy","spec.ingress.0.ports.0.endPort",-1),
 ("GatewayClass","spec.controllerName",BAD),
 ("Gateway","spec.gatewayClassName",BAD),
 ("Gateway","spec.listeners.0.name",BAD),("Gateway","spec.listeners.0.port",BAD),("Gateway","spec.listeners.0.protocol",BAD),
 ("EnvoyProxy","status.conditions.0.type",BAD),("EnvoyProxy","status.conditions.0.status",BAD),("EnvoyProxy","status.conditions.0.reason",BAD),
 ("Cluster","spec.instances",BAD),("Cluster","spec.storage.size",BAD),("Cluster","spec.monitoring.enablePodMonitor",BAD),
 ("Cluster","status.phase",BAD),("Cluster","status.readyInstances",BAD),
 ("ObjectStore","spec.data.s3Credentials.name",BAD),
]
observed={}
for kind,path,value in cases:
 item=fixture(kind);assign(item,path,value);observed[kind+":"+path]=run(kind,item)
item=fixture("NetworkPolicy");del item["kind"]
observed["missing_kind"]=run("NetworkPolicy",item)
observed["invalid_authority"]={"input":"https://bad host.invalid/path","output":inv.sanitize_url("https://bad host.invalid/path")}
checks={}
for category,stderr in [("FORBIDDEN","Forbidden "+CANARY),("TIMEOUT","context deadline exceeded "+CANARY),("CONNECTION","connection refused "+CANARY)]:
 checks[category]=run("NetworkPolicy",fixture("NetworkPolicy"),subprocess.CompletedProcess([],1,CANARY,stderr))
with tempfile.TemporaryDirectory() as tmp:
 dest=Path(tmp)/"existing";dest.mkdir();file=dest/"inventory.jsonl";file.write_text("KEEP")
 with mock.patch.object(inv.shutil,"which",return_value="/mock/kubectl"), mock.patch.object(inv.subprocess,"run") as execute, mock.patch.object(inv.sys,"argv",["inventory.py","--context","mock","--output",str(dest)]):
  try: inv.main();error=None
  except Exception as exc: error=type(exc).__name__
  checks["no_overwrite"]={"exception":error,"reads":execute.call_count,"unchanged":file.read_text()=="KEEP"}
print(json.dumps({"observations":observed,"working_error_paths":checks},indent=2,sort_keys=True))
