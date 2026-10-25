# P8C RV-02 live inventory closure — result

Date: 2026-10-25 UTC.

## Access path
No authorized read-only cluster path is reachable from the Hermes host (see
access-path.md). Live inventory is NOT_EXECUTED; the operator-handoff package is
complete. This is a concrete external blocker, not a work backlog.

## Independent preparation completed
- `portal/networkpolicy/inventory.py` hardened: full-object reads (NetworkPolicy /
  GatewayClass / Gateway / EnvoyProxy) are projected to strip `managedFields` and
  `annotations` (last-applied can carry credentials); errors classified into safe
  categories (TIMEOUT / FORBIDDEN / API_NOT_SERVED / CONNECTION / GET_FAILED);
  kubectl-absence fails closed before creating any output.
- `portal/networkpolicy/inventory_test.py` — 11/11 offline mock tests (projection +
  error categories + JSONL write + exit codes + no-kubectl block).
- `portal/networkpolicy/flow-matrix.md` — 14 FLOW-IDs across replication /
  instance-manager / operator / Barman / monitoring / DNS / API / S3 / Portal
  5432+9187 / migrator 5432 / Envoy xDS+backend+listener, each with proof type and
  policy reference. Live-only facts are UNKNOWN (not hidden).
- `portal/networkpolicy/gaps.md` — 8 precise live-only gaps (Barman direction,
  API DNAT, monitoring identity, DNS, S3 endpoint, Envoy ownership, baseline union,
  CNI semantics).
- `portal/networkpolicy/operator-handoff.md` — exact script + SHA + command +
  return/exclude list for the operator's authorized session.
- Offline flow tests unchanged and green: `go test -count=1 -v ./networkpolicy`
  (18 positive/negative both-side subtests, exit 0).

## Status fields
```text
RECOVERY_MAIN_SHA: c750dd710898962acfd465ca2b3ff92f82ea2f9a
FINAL_SOURCE_SHA: <set after commit; source = portal/networkpolicy/** + manifests/networkpolicy.yaml>
FINAL_REMOTE_MAIN_SHA: <set after push>
APPLICATION_RUNTIME_SOURCE_UNCHANGED: YES (817f0ece… untouched)
NATIVE_PG17_EVIDENCE: ACCEPTED_PREVIOUSLY_NOT_RERUN
ACCESS_PATH: NONE (no local kubectl/kubeconfig; nodes unreachable over SSH)
NETPOL_LIVE_INVENTORY: NOT_EXECUTED (BLOCKED_EXTERNAL)
FLOW_MATRIX_COMPLETE: NO (14 FLOW-IDs, 8 live-only UNKNOWN gaps documented)
OFFLINE_FLOW_TESTS: PASS (go 18 subtests + python 11 tests)
SECRET_SCAN: heuristic; only secretKeyRef reference patterns + docs (no values)
NETPOL_PACKAGE_REVIEW_READY: YES (source/offline preparation complete for review)
NETPOL_APPROVED_FOR_APPLY: NO
CI_RELEASE: NOT_EXECUTED
OWNER_HELPERS: NOT_EXECUTED
PRODUCTION_MIGRATION_DEPLOYMENT: NOT_EXECUTED
P8C: NOT_FINAL_ACCEPTED
P8D–P8G/P9: NOT_AUTHORIZED
```

## Concrete owner action required (single request)
Run the reviewed read-only package in the operator's existing authorized session:
```
python3 portal/networkpolicy/inventory.py --context "<approved-context>" --output "<new-dir>"
```
and return the sanitized `inventory.jsonl` + server version line (see
operator-handoff.md). That unblocks the remaining UNKNOWN flow rows and the
CNPG/monitoring/API/DNS/S3/Envoy reconciliation. No apply, no CI, no helpers, no
production migration/deploy in this task.
