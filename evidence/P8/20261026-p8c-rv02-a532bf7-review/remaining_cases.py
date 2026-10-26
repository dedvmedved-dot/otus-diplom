#!/usr/bin/env python3
"""Remaining required/container/range cases from the existing contract. Mock only."""
import contextlib, io, json, runpy
with contextlib.redirect_stdout(io.StringIO()):
    helper=runpy.run_path("prior_reproduce.py")
fixture,assign,run=helper["fixture"],helper["assign"],helper["run"]
cases=[
 ("NetworkPolicy","spec.ingress",False),
 ("NetworkPolicy","spec.egress",{}),
 ("Gateway","spec.listeners",""),
 ("NetworkPolicy","spec.ingress",[None]),
 ("NetworkPolicy","spec.ingress",[{"from":[None]}]),
 ("NetworkPolicy","spec.podSelector",None),
 ("NetworkPolicy","metadata.name",""),
 ("NetworkPolicy","metadata.namespace",None),
 ("NetworkPolicy","spec.podSelector.matchExpressions",[{"key":"app","values":["portal"]}]),
 ("EnvoyProxy","status.conditions",[{"type":"Ready"}]),
 ("NetworkPolicy","spec.ingress.0.ports",[{"port":"http","endPort":8080}]),
 ("NetworkPolicy","spec.ingress.0.ports",[{"endPort":8080}]),
]
results={}
for kind,path,value in cases:
    item=fixture(kind);assign(item,path,value)
    results[kind+":"+path+":"+json.dumps(value)]=run(kind,item)
print(json.dumps(results,indent=2,sort_keys=True))
