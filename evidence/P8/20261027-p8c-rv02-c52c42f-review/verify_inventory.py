import hashlib, json, pathlib, datetime, re
p=pathlib.Path(__file__).parent
raw=(p/"inventory.jsonl").read_bytes()
script=(p/"inventory.py").read_bytes()
rows=[json.loads(x) for x in raw.splitlines()]
assert len(raw)==49675 and len(rows)==15
assert hashlib.sha256(raw).hexdigest()=="bc692fc80634fc7eeda6f5d5cc564101ca4b391974a37b5185e1baeef4044f41"
assert hashlib.sha256(script).hexdigest()=="7806f494bcee93f31eb2cb0348d2cd8f7cbbf5743261336226a251643d8988a2"
assert hashlib.sha1(b"blob "+str(len(script)).encode()+b"\0"+script).hexdigest()=="5f0e2450358bfd9b08b542f013be5a914b9195a4"
prev=None
for i,r in enumerate(rows):
    a=r["argv"]
    assert a[:6]==["kubectl","--context","kubernetes-admin@pak-portal","--request-timeout=15s","get",a[5]]
    st=datetime.datetime.fromisoformat(r["start"]); en=datetime.datetime.fromisoformat(r["end"])
    assert st<=en and (prev is None or prev<=st)
    prev=en
    if i in (10,11,12):
        assert (r["exit"],r["category"],r["output"])==(1,"API_NOT_SERVED","")
    else:
        assert (r["exit"],r["category"])==(0,None)
for n in (4,6,7): assert json.loads(rows[n]["output"])==[]
groups=[g["name"] for g in json.loads(rows[13]["output"])["groups"]]
assert "monitoring.coreos.com" not in groups
assert "crd.projectcalico.org" in groups
assert "policy.networking.k8s.io" in groups
api=[s for s in rows[2]["output"].splitlines() if s.startswith("default\tkubernetes\t")][0]
for addr in ("172.30.140.101","172.30.140.102","172.30.140.103"): assert addr in api
assert '"port":6443' in api
dns=[s for s in rows[2]["output"].splitlines() if s.startswith("kube-system\tkube-dns-")][0]
for addr in ("10.244.254.65","10.244.254.66"): assert addr in dns
findings={}
for name,pattern in {
    "private_key":r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY",
    "bearer":r"(?i)bearer\s+[a-z0-9._~+/-]{10,}",
    "aws_key":r"AKIA[0-9A-Z]{16}",
    "url_userinfo":r"[a-zA-Z][a-zA-Z0-9+.-]*://[^\s/]+@",
    "credential_assignment":r"(?i)(?:password|access_token|secret_access_key)\s*[=:]\s*[^\s,;]{4,}"
}.items(): findings[name]=len(re.findall(pattern,raw.decode()))
assert not any(findings.values())
result={"reviewed_head":"c52c42f661748a7aa55ee19d096aecc03f7944ed",
"inventory_sha256":hashlib.sha256(raw).hexdigest(),"bytes":len(raw),"records":len(rows),
"ok":12,"api_not_served":3,"other_errors":0,
"start":rows[0]["start"],"end":rows[-1]["end"],"inventory_exit_preserved":1,
"script_sha256":hashlib.sha256(script).hexdigest(),
"api_endpoints_already_observed":["172.30.140.101:6443","172.30.140.102:6443","172.30.140.103:6443"],
"dns_endpoints_already_observed":["10.244.254.65","10.244.254.66"],
"additional_policy_group_served":"policy.networking.k8s.io",
"heuristic_secret_scan":findings,"scan_limit":"Pattern checks plus bounded content review; not proof of universal secret absence.",
"runtime_executed_by_reviewer":False,
"version_and_host_hash_execution":"Operator-attested in result.md; standalone raw version/hash transcript not present in this package.",
"result":"PASS_FOR_LISTED_OFFLINE_ARTIFACT_CHECKS"}
(p/"execution.json").write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps(result,indent=2))
