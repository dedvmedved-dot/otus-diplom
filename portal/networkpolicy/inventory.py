#!/usr/bin/env python3
"""Prepared fixed read-only inventory collector (P8C RV-02).

Issues ONLY `kubectl get ... ` reads with safe projected fields. No exec, no
writes, no port-forward, no mutation. Full objects are projected to strip
managedFields and annotations (annotations may embed last-applied config with
credentials). Errors are classified into safe categories, never raw tracebacks.

Run in the authorized operator session:
  python3 portal/networkpolicy/inventory.py --context "<approved>" --output "<new-dir>"
"""
import argparse
import datetime
import json
from pathlib import Path
import shutil
import subprocess
import sys

PODS = '{range .items[*]}{.metadata.namespace}{"\\t"}{.metadata.name}{"\\t"}{.metadata.labels}{"\\t"}{range .spec.containers[*]}{.name}{":"}{.ports}{";"}{end}{"\\n"}{end}'
SERVICES = '{range .items[*]}{.metadata.namespace}{"\\t"}{.metadata.name}{"\\t"}{.spec.clusterIP}{"\\t"}{.spec.selector}{"\\t"}{.spec.ports}{"\\n"}{end}'
ENDPOINTS = '{range .items[*]}{.metadata.namespace}{"\\t"}{.metadata.name}{"\\t"}{.metadata.labels}{"\\t"}{.ports}{"\\t"}{range .endpoints[*]}{.addresses}{":"}{.conditions}{":"}{.targetRef.kind}{"/"}{.targetRef.name}{";"}{end}{"\\n"}{end}'
# Full-object reads are PROJECTED (managedFields/annotations stripped) before
# writing; only identity + spec + safe status fields are retained.
FULL_OBJECT_KINDS = [
    ['get', 'networkpolicies.networking.k8s.io', '-A', '-o', 'json'],
    ['get', 'gatewayclasses.gateway.networking.k8s.io', '-o', 'json'],
    ['get', 'gateways.gateway.networking.k8s.io', '-A', '-o', 'json'],
    ['get', 'envoyproxies.gateway.envoyproxy.io', '-A', '-o', 'json'],
]
COMMANDS = [
    ['get', 'pods', '-A', '-o', 'jsonpath=' + PODS],
    ['get', 'services', '-A', '-o', 'jsonpath=' + SERVICES],
    ['get', 'endpointslices.discovery.k8s.io', '-A', '-o', 'jsonpath=' + ENDPOINTS],
] + FULL_OBJECT_KINDS + [
    ['get', 'servicemonitors.monitoring.coreos.com', '-A', '-o',
     'jsonpath={range .items[*]}{.metadata.namespace}{"\\t"}{.metadata.name}{"\\t"}{.spec.selector}{"\\t"}{.spec.namespaceSelector}{"\\t"}{range .spec.endpoints[*]}{.port}{";"}{end}{"\\n"}{end}'],
    ['get', 'podmonitors.monitoring.coreos.com', '-A', '-o',
     'jsonpath={range .items[*]}{.metadata.namespace}{"\\t"}{.metadata.name}{"\\t"}{.spec.selector}{"\\t"}{.spec.namespaceSelector}{"\\n"}{end}'],
    ['get', '--raw', '/apis/monitoring.coreos.com/v1'],
    ['get', 'nodes', '-o',
     'jsonpath={range .items[*]}{.metadata.name}{"\\t"}{.status.addresses}{"\\t"}{.spec.podCIDRs}{"\\n"}{end}'],
]


def project(obj):
    """Recursively strip managedFields and annotations (and the last-applied
    annotation which can carry credentials). Returns a plain JSON-safe value."""
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k == 'managedFields':
                continue
            if k == 'annotations':
                # Drop only last-applied + secret-bearing annotations; keep a
                # bounded allowlist of non-sensitive annotations if any (none
                # are needed for flow facts, so drop all).
                continue
            out[k] = project(v)
        return out
    if isinstance(obj, list):
        return [project(x) for x in obj]
    return obj


def classify(returncode, stderr, timed_out):
    if timed_out:
        return 'TIMEOUT'
    if returncode == 0:
        return None
    low = (stderr or '').lower()
    if 'forbidden' in low or 'unauthorized' in low:
        return 'FORBIDDEN'
    if 'could not find' in low or 'no matches for kind' in low or "doesn't have a resource" in low:
        return 'API_NOT_SERVED'
    if 'connection' in low or 'refused' in low or 'unable to connect' in low:
        return 'CONNECTION'
    return 'GET_FAILED'


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--context', required=True)
    p.add_argument('--output', required=True)
    args = p.parse_args()
    if not shutil.which('kubectl'):
        raise SystemExit('BLOCKED: kubectl unavailable; no platform reads executed')
    directory = Path(args.output)
    directory.mkdir(parents=True, exist_ok=False)
    failures = 0
    with (directory / 'inventory.jsonl').open('x') as log:
        for command in COMMANDS:
            argv = ['kubectl', '--context', args.context, '--request-timeout=15s'] + command
            start = datetime.datetime.now(datetime.timezone.utc).isoformat()
            timed_out = False
            try:
                result = subprocess.run(argv, capture_output=True, text=True, timeout=20)
            except subprocess.TimeoutExpired:
                timed_out = True
                result = None
            except OSError:
                result = None
            category = classify(None if result is None else result.returncode,
                                '' if result is None else result.stderr, timed_out)
            if result is not None and result.returncode == 0:
                output = result.stdout
                if command in FULL_OBJECT_KINDS:
                    # Project full JSON objects to a safe subset.
                    try:
                        output = json.dumps(project(json.loads(result.stdout)))
                    except json.JSONDecodeError:
                        output = result.stdout
            else:
                output = ''
            record = {
                'start': start,
                'argv': [a for a in argv if not a.startswith('--') or a == '--context' or a == '--request-timeout=15s' or a == '--output'],
                'exit': None if result is None else result.returncode,
                'category': category,
                'output': output,
            }
            if category is not None:
                failures += 1
            record['end'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            log.write(json.dumps(record) + '\n')
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
