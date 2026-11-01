"""Offline review: run with Connector-fetched files; no cluster/network calls."""
import datetime, hashlib, json, platform
from pathlib import Path
import yaml
import followup as f
import followup_test as t

start = datetime.datetime.now(datetime.timezone.utc).isoformat()
digest = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
expected = {}
for line in Path('SHA256SUMS.result').read_text().splitlines():
    h, p = line.split()
    expected[Path(p).name] = h
hashes = {p: {'expected': h, 'actual': digest(p), 'match': digest(p) == h}
          for p, h in expected.items()}
assert all(v['match'] for v in hashes.values())
rows = [json.loads(x) for x in Path('followup.jsonl').read_text().splitlines()]
assert len(rows) == 9
categories = {}
for r in rows:
    cat = r['category'] or 'OK'
    categories[cat] = categories.get(cat, 0) + 1
assert categories == {'OK': 1, 'PARSE_ERROR': 1, 'UNSUPPORTED': 1, 'BLOCKED_NOT_EXECUTED': 6}
assert sum(r['argv'] is not None for r in rows) == 3
live = json.loads(next(r for r in rows if r['id'] == 'F-CS')['output'])
crd = next(d for d in yaml.safe_load_all(Path('calico-v3.32.0.yaml').read_text())
           if d and d.get('metadata', {}).get('name') == 'clusternetworkpolicies.policy.networking.k8s.io')
projected = f.project_crd_schema(json.dumps(crd))
assert projected['spec_schema_sha256'] == live['spec_schema_sha256']
assert not projected['compatible']
subtree = next(v for v in crd['spec']['versions'] if v['name'] == 'v1alpha2')['schema']['openAPIV3Schema']['properties']['spec']
changes = []
def diff(a, b, p=''):
    if type(a) is not type(b):
        changes.append({'path': p, 'before': a, 'after': b})
    elif isinstance(a, dict):
        for k in sorted(a.keys() | b.keys()):
            if k not in a or k not in b:
                changes.append({'path': p+'/'+k, 'before': a.get(k), 'after': b.get(k)})
            else:
                diff(a[k], b[k], p+'/'+k)
    elif a != b:
        changes.append({'path': p, 'before': a, 'after': b})
diff(f.normalize_schema(t.CNP_SPEC), f.normalize_schema(subtree))
assert len(changes) == 3
identity = []
for kind, rv in [('PodList', 'rv1'), ('List', 'rv1'), ('PodList', ''), ('List', '')]:
    raw = json.loads(t.podlist([t.POD_CFG]))
    raw['kind'] = kind
    raw['metadata']['resourceVersion'] = rv
    rc, calls, result = t.run({'F-I1': t.R(0, json.dumps(raw))})
    row = t.by_id(result)['F-I1']
    dependents = sum(rid in ('F-NP','F-GNP','F-FELIX','F-HEP','F-TIER') for rid, _ in calls)
    good = kind == 'PodList' and rv != ''
    assert row['category'] == (None if good else 'PARSE_ERROR')
    assert dependents == (5 if good else 0)
    identity.append({'fixture': 'SYNTHETIC_KUBECTL_ENVELOPE_VARIANT', 'kind': kind,
                     'resourceVersion': rv, 'category': row['category'],
                     'dependent_calls': dependents})
report = {'review_head': '3a0afb45b07daa8ac5e5ceb41563fc518db87dc9',
          'start_utc': start, 'end_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'python': platform.python_version(), 'pyyaml': yaml.__version__,
          'hashes': hashes, 'records': len(rows), 'categories': categories,
          'recorded_collector_invocations': 3, 'identity_reproduction': identity,
          'manifest_schema_projection': projected, 'schema_differences': changes,
          'kubectl_source_sha256': digest('kubectl-get.go'),
          'calico_manifest_sha256': digest('calico-v3.32.0.yaml'),
          'all_assertions_passed': True, 'cluster_calls': 0,
          'limits': ['Synthetic identity envelope reproduction, not recovered live stdout',
                     'Runtime/preflight statements outside JSONL are operator-reported',
                     'Matching schema subtree hash does not prove whole-CRD equality or mutation history']}
Path('verification.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report, indent=2))
