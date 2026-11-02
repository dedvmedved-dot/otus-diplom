# Replay — 980cee5 independent review

All runs offline, no SSH/cluster/registry. Reviewed source fdfc776 at main 980cee5.
Source bytes checked against Connector Git blob IDs before recorded execution.
Only targeted new regression was run; accepted full suites not rerun.

Prepare a new scratch directory from repo sources at 980cee55e32bf87451919d37c898d40ae33d4557:
- portal/networkpolicy/{followup.py,supplemental.py,followup_test.py,derived-i1-fixture.json,followup-typed-contract.json}
- this evidence's podlist_boundary_regression_test.py, verify.py, source-blobs.json
- into live/: followup.jsonl, run-meta.txt, SHA256SUMS.result from
  evidence/P8/20261102T023500Z-p8c-rv02-followup-compat-onerun/.

Python needs the existing test harness dependency PyYAML. Run python3 verify.py.
It checks exact hashes, records expected regression failure against unchanged source,
and runs an in-memory candidate adapter; no production source file is modified.
The candidate is explanatory review code, not an accepted runtime implementation.
6 methods: explicit positive control, 3 absence positives, 10 invalid-presence subcases,
1 unbound digest. Before: 2 methods PASS/4 FAIL, exit1 expected.
Review-only adapter: 6 methods PASS; verify.py exit0. Exact UTC/Python in verification.json.
No claim that missing TypeMeta was recovered from this run's suppressed live stdout.

Primary source URLs (read through Connector at v1.36.2):
https://github.com/kubernetes/kubernetes/blob/v1.36.2/staging/src/k8s.io/api/core/v1/types.go
https://github.com/kubernetes/kubernetes/blob/v1.36.2/staging/src/k8s.io/apimachinery/pkg/apis/meta/v1/types.go
https://github.com/kubernetes/kubernetes/blob/v1.36.2/staging/src/k8s.io/apimachinery/pkg/runtime/serializer/json/json.go
https://github.com/kubernetes/kubernetes/blob/v1.36.2/staging/src/k8s.io/apimachinery/pkg/runtime/serializer/json/collections.go
https://github.com/kubernetes/kubernetes/blob/v1.36.2/staging/src/k8s.io/apimachinery/pkg/runtime/serializer/json/collections_test.go
Exact blobs in Architect review. Typed list serialization does not require nested TypeMeta.
The supplied fixture's wrappers were explicitly SYNTHETIC; removing them is a new derived
wire-boundary case, not a newly captured live Pod.

Evidence limit: preflight and remote SHA checks operator-attested in result.md; no separate
raw sanitized transcript committed. Do not refill that gap with a new live run.
