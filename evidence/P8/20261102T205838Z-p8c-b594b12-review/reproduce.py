import copy, hashlib, ipaddress, json, pathlib, platform, shutil
import yaml
base=pathlib.Path(__file__).parent
raw=(base/"networkpolicy.yaml").read_bytes()
assert hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()=="6212a016c783419d2e81c9a2325fdaeef9279bc7"
ps=[x for x in yaml.safe_load_all(raw) if x]
assert len(ps)==6
def peer(ns="",labels=None,ip=""):
    return {"ns":ns,"labels":labels or {},"ip":ip}
def match(sel,values):
    assert not sel.get("matchExpressions"), "outside this review's finite model"
    return all(values.get(k)==v for k,v in sel.get("matchLabels",{}).items())
def pm(r,p,ns):
    if "ipBlock" in r:
        return bool(p["ip"]) and ipaddress.ip_address(p["ip"]) in ipaddress.ip_network(r["ipBlock"]["cidr"])
    if "namespaceSelector" in r:
        if not match(r["namespaceSelector"],{"kubernetes.io/metadata.name":p["ns"]}): return False
    elif ns!=p["ns"]: return False
    return "podSelector" not in r or match(r["podSelector"],p["labels"])
def allow(policies,src,dst,port,proto="TCP"):
    for direction,target,other in [("Egress",src,dst),("Ingress",dst,src)]:
        selected=[p for p in policies if p["metadata"]["namespace"]==target["ns"] and match(p["spec"]["podSelector"],target["labels"]) and direction in p["spec"]["policyTypes"]]
        if not selected: continue
        permit=False
        for p in selected:
            for r in p["spec"].get(direction.lower(),[]):
                ports=r.get("ports",[])
                if ports and not any(x.get("protocol","TCP")==proto and x.get("port",port)==port for x in ports): continue
                peers=r.get("to" if direction=="Egress" else "from",[])
                if not peers or any(pm(x,other,p["metadata"]["namespace"]) for x in peers): permit=True
        if not permit: return False
    return True
portal=peer("portal",{"app.kubernetes.io/name":"pak-portal"})
db=peer("portal",{"cnpg.io/cluster":"portal-db","cnpg.io/podRole":"instance"})
mig=peer("portal",{"app.kubernetes.io/name":"pak-portal-migrator"})
dns=peer("kube-system",{"k8s-app":"kube-dns"})
labels={"app.kubernetes.io/component":"proxy","app.kubernetes.io/managed-by":"envoy-gateway","app.kubernetes.io/name":"envoy","gateway.envoyproxy.io/owning-gateway-name":"portal-gateway","gateway.envoyproxy.io/owning-gateway-namespace":"portal"}
envoy=peer("envoy-gateway-system",labels)
count=0
def check(got,want):
    global count
    count+=1
    assert got==want,(count,got,want)
tuples={("10.96.0.1",443),("172.30.140.101",6443),("172.30.140.102",6443),("172.30.140.103",6443)}
for src in [db,portal,mig]:
    for ip in ["10.96.0.1"]+["172.30.140."+str(i) for i in range(256)]:
        for port in [443,6443]:
            for proto in ["TCP","UDP"]:
                check(allow(ps,src,peer(ip=ip),port,proto),src!=mig and proto=="TCP" and (ip,port) in tuples)
for src in [db,portal,mig,envoy]:
    for proto in ["TCP","UDP"]:
        check(allow(ps,src,dns,53,proto),True)
        for bad in [peer("kube-system",{"k8s-app":"other"}),peer("other",{"k8s-app":"kube-dns"})]:
            check(allow(ps,src,bad,53,proto),False)
for key in labels:
    for missing in [False,True]:
        ls=dict(labels)
        if missing: del ls[key]
        else: ls[key]="other"
        check(allow(ps,peer(envoy["ns"],ls),portal,8080),False)
check(allow(ps,envoy,portal,8080),True)
check(allow(ps,envoy,portal,8081),False)
check(allow(ps,peer("cnpg-system",{"app":"barman-cloud"}),db,5432),False)
for src in [db,portal,mig]:
    check(allow(ps,src,peer(ip="172.30.143.10"),443),src==db)
# Demonstrate the reversed negative DNS tests miss a real broadening.
mutant=copy.deepcopy(ps)
for p in mutant:
    for r in p["spec"].get("egress",[]):
        for dest in r.get("to",[]):
            if dest.get("namespaceSelector",{}).get("matchLabels",{}).get("kubernetes.io/metadata.name")=="kube-system":
                dest.pop("podSelector",None)
bad=peer("kube-system",{"k8s-app":"other"})
assert not allow(ps,bad,portal,53,"UDP") and not allow(mutant,bad,portal,53,"UDP")
assert not allow(ps,portal,bad,53,"UDP") and allow(mutant,portal,bad,53,"UDP")
print(json.dumps({"reviewed_sha":"b594b12debd574baa614496b090068982a79da21","yaml_blob":"6212a016c783419d2e81c9a2325fdaeef9279bc7","python":platform.python_version(),"yaml":yaml.__version__,"candidate_checks_passed":count,"dns_reversed_test_false_negative":"REPRODUCED","correct_direction_detects_mutation":True,"go_available":bool(shutil.which("go")),"scope":"offline finite NetworkPolicy model; no runtime enforcement proof"},indent=2))
