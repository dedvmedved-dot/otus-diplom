#!/usr/bin/env python3
"""Prepared fixed read-only inventory. No production invocation by source tests."""
import argparse
import datetime
import json
from pathlib import Path
import shutil
import subprocess

PODS = '{range .items[*]}{.metadata.namespace}{"\t"}{.metadata.name}{"\t"}{.metadata.labels}{"\t"}{range .spec.containers[*]}{.name}{":"}{.ports}{";"}{end}{"\n"}{end}'
SERVICES = '{range .items[*]}{.metadata.namespace}{"\t"}{.metadata.name}{"\t"}{.spec.clusterIP}{"\t"}{.spec.selector}{"\t"}{.spec.ports}{"\n"}{end}'
ENDPOINTS = '{range .items[*]}{.metadata.namespace}{"\t"}{.metadata.name}{"\t"}{.metadata.labels}{"\t"}{.ports}{"\t"}{range .endpoints[*]}{.addresses}{":"}{.conditions}{":"}{.targetRef.kind}{"/"}{.targetRef.name}{";"}{end}{"\n"}{end}'
COMMANDS = [
 ['get','pods','-A','-o','jsonpath='+PODS],
 ['get','services','-A','-o','jsonpath='+SERVICES],
 ['get','endpointslices.discovery.k8s.io','-A','-o','jsonpath='+ENDPOINTS],
 ['get','networkpolicies.networking.k8s.io','-A','-o','json'],
 ['get','gatewayclasses.gateway.networking.k8s.io','-o','json'],
 ['get','gateways.gateway.networking.k8s.io','-A','-o','json'],
 ['get','envoyproxies.gateway.envoyproxy.io','-A','-o','json'],
 ['get','servicemonitors.monitoring.coreos.com','-A','-o','jsonpath={range .items[*]}{.metadata.namespace}{"\t"}{.metadata.name}{"\t"}{.spec.selector}{"\t"}{.spec.namespaceSelector}{"\t"}{range .spec.endpoints[*]}{.port}{";"}{end}{"\n"}{end}'],
 ['get','podmonitors.monitoring.coreos.com','-A','-o','jsonpath={range .items[*]}{.metadata.namespace}{"\t"}{.metadata.name}{"\t"}{.spec.selector}{"\t"}{.spec.namespaceSelector}{"\n"}{end}'],
 ['get','--raw','/apis/monitoring.coreos.com/v1'],
 ['get','nodes','-o','jsonpath={range .items[*]}{.metadata.name}{"\t"}{.status.addresses}{"\t"}{.spec.podCIDRs}{"\n"}{end}'],
]
def main():
    p=argparse.ArgumentParser();p.add_argument('--context',required=True);p.add_argument('--output',required=True);args=p.parse_args()
    directory=Path(args.output);directory.mkdir(parents=True,exist_ok=False)
    if not shutil.which('kubectl'): raise SystemExit('BLOCKED: kubectl unavailable; no platform reads executed')
    failures=0
    with (directory/'inventory.jsonl').open('x') as log:
        for command in COMMANDS:
            argv=['kubectl','--context',args.context,'--request-timeout=15s']+command
            start=datetime.datetime.now(datetime.timezone.utc).isoformat()
            try:
                result=subprocess.run(argv,capture_output=True,text=True,timeout=20)
                record={'start':start,'argv':argv,'exit':result.returncode,'output':result.stdout if result.returncode==0 else '', 'error':'GET_FAILED' if result.returncode else None}
                failures+=result.returncode!=0
            except (OSError,subprocess.TimeoutExpired):
                record={'start':start,'argv':argv,'exit':None,'error':'READ_UNAVAILABLE'};failures+=1
            record['end']=datetime.datetime.now(datetime.timezone.utc).isoformat();log.write(json.dumps(record)+'\n')
    return 1 if failures else 0
if __name__=='__main__': raise SystemExit(main())
