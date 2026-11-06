# P8C Executable Release + Readiness — Runbook & Runtime Manifest (source-only)

Дата: 2026-11-06. PRIMARY HERMES. Source-only runbook; НЕ разрешение выполнить live/CI/push.

## Runtime manifest (исполняемые файлы + зависимости)

| Файл | Роль | Runtime deps |
|---|---|---|
| portal/tools/verify-pins.py | public pin verification | python3 stdlib (urllib) |
| portal/tools/release_qualification.py | template qualification | python3 + PyYAML |
| portal/tools/p8c-portal-release.yml.template | release workflow TEMPLATE | GitHub Actions runner (ubuntu-24.04), Go, buildkit/rootlesskit/syft/trivy/cosign |
| portal/tools/p8c-portal-seed.yml.template | private-seed TEMPLATE | GitHub Actions runner, buildkit |
| portal/tools/Seed.Containerfile | seed artifact recipe (not deployable) | buildctl |
| portal/tools/install-verified-go.sh | verified Go toolchain | curl, sha256sum, tar |
| portal/tools/release-check.py | fail-closed release metadata gates (digest/predicate/first-creation/private/registry/verified) | python3 stdlib |
| portal/tools/readiness/wrapper.py | readiness wrapper (S0→S4 executor) | python3, kubectl (future live gate) |
| portal/tools/readiness/wal.py | WAL observation (scheduler + budgets + clock) | python3 urllib (injected) |
| portal/tools/readiness/readset.json | declarative read-set (frozen) | — |
| portal/tools/readiness/test_architect_residual.py | active working copy of Architect residual (isolated authority) | — |
| portal/tools/run_offline_suite.sh | single full-suite launcher (nonzero on error) | bash, python3 |

## Budget levels (accepted R4 design, enforced)

| Level | Requests | Bytes | Seconds |
|---|---|---|---|
| sample | 5 | 2 MiB | 30 s |
| window | 15 | 6 MiB | 660 s |
| WAL cumulative | 90 | 36 MiB | 3960 s |
| overall | 233 | 179 MiB | 5265 s |

Enforcement points: per-request cap + hard deadline inside transport (no proxy/redirect); sample
body cap + 30s deadline in `run_wal_sample`; window 660s + 6 MiB in `run_wal_window`; WAL-cumulative
and overall checked in `budget_exhausted` + before each WAL sample (`_wal_exhausted`). Remaining
budget is re-checked INSIDE each I/O (attempt charged before the transport call; bytes charged even
on partial/error bodies). Budget is stored at the stable authority (`budget_path(gate)` =
`RESERVATION_BASE/<package_sha256[:32]>/budget.json`), not the state-dir — a new state-dir cannot
reset consumption. Charges are persisted atomically before each I/O (crash-safe). Any NaN/infinite/
non-finite budget field blocks before any read.

## State machine (window authority)

`open_window` at a stable authority location (package_sha256, NOT state/output path). Statuses:
`inflight` (opened/crash) → no retry; `failed` (non-PASS after ≤3 slots) → no retry, no new budget;
`completed` (PASS) → no replay. A changed state-dir cannot bypass authority. Receipts are verified
JSON bound to source+package+issued_at (a receipt from a different gate is not authority). S1–S4
require an operation boundary (`operation_end_utc` ≥ issued_at) that is bound to a verified
`action_receipt` (source_sha + package_sha256 + operation_end_utc) — an arbitrary number is not
authority. The WAL baseline stores the pod UID (observation identity) + observed time and re-checks
the UID on read; a cross-sample pod UID change invalidates the comparison.

## Health windows + freshness at verdict

Health reads (HC-*) use bounded windows: a first observation's FAIL is preserved (failure
precedence — never erased by a later sweep); a transient INCONCLUSIVE is retried after a bounded
interval (10 s, limited by the remaining time budget); and at the verdict every mandatory
observation is re-read fresh and gated on age ≤ 30 s (a stale observation → FAIL, no PASS).
Predicates enforce exact resource kinds (HC-DB must be `Cluster`, PR-6 must be the nine expected
*List kinds and each list's typed items/max_items, PR-5 must carry uid/namespace=envoy-gateway-system
/ownership labels), and return value-free dispositions (no raw value echoed). Malformed/nested items
are recorded as typed dispositions, never an uncaught exception. WAL requires the pod to be
`cnpg.io/instanceRole=primary` on BOTH bracket sides and counts restart by container name `postgres`;
incomplete metrics never overwrite a valid baseline.

## requirement → code → test → evidence matrix

| Requirement | Code | Test (methods) | Evidence |
|---|---|---|---|
| pin verification (10/10) | verify-pins.py + pins.lock.json | launcher → exit 0 | pin-verification.json |
| release template R-01..08 | p8c-portal-release.yml.template | test_release_qualification (3) + test_release (4) + test_release_negative (7) | qualified:true |
| release verified route | release-check.py verified | test_release_negative + architect residual SeedAndRelease | payloadBinding PASS |
| seed REUSE/STOP/CREATE_ALLOWED | p8c-portal-seed.yml.template + release-check.py first-creation/private | test_release_qualification + contract first-creation (expired/future/TEST_ONLY rejected) | qualified:true |
| readiness S0→S4 executor | wrapper.py main + run_wal_window | contract test_positive_s0_through_s4 | receipt stage=S4 |
| window state (no retry) | wrapper.py open_window/fail_window/complete_window | contract + scheduler + residual (isolated) | receipt/failed markers |
| WAL sample/window | wal.py + wrapper.run_wal_sample/run_wal_window | test_readiness TestWAL + scheduler + contract | aggregate journals |
| budget accounting (attempts/bytes/elapsed) | wrapper._TRANSPORT/_WAL_TRANSPORT | contract test_budget_counts/failed_attempts/exhausted/negative | budget.json |
| predicates PR-3/5/6, HC-* | wrapper.py PREDICATES | test_readiness + contract + regression | PASS/FAIL dispositions |
| architect regression (frozen) | evidence regression_test.py | 28 methods | reexecution transcript |
| architect scheduler regression (frozen) | evidence scheduler_regression_test.py | 14 methods | transcript |
| architect contract (active working copy) | portal/tools/readiness/test_contract_authority_working.py | 15 methods | transcript |
| architect completion contract (active working copy) | portal/tools/readiness/test_completion_authority_working.py | 34 methods | transcript |
| architect residual contract (active working copy) | portal/tools/readiness/test_residual_contract_working.py | 20 methods | transcript |
| pin verification (10/10, offline) | verify-pins.py --offline | launcher → exit 0 | pin-verification-offline.json |

Full suite (isolated authority per file): 23 readiness + 25 residual-working + 3 qualification +
4 release + 7 release-negative + 28 regression + 14 scheduler + 15 contract-authority + 34 completion
-authority + 20 residual-contract = **173 methods**.

Note: the frozen historical completion_contract_test.py / residual_contract_test.py are NOT modified;
their positive S0→S4 flows predate the action-receipt binding, so the active working copies add the
typed `action_receipt` to those positive flows (per the single-pass correction directive). The
historical budget-fixture correction (exhausted authority via `write_budget`) is likewise adopted in
the active working copy.

## Runbook (future operator, после отдельного gate)

1. Operator: `python3 portal/tools/readiness/wrapper.py --gate <issued-gate.json> --out <journal> --state-dir <state> --stage S0 --kubectl kubectl`
2. Gate manifest: mode=LIVE, context kubernetes-admin@pak-portal, source_sha, package_sha256 (=sha256(readset+wrapper+wal)), issued_at_utc, expiry_hours≤24, clock_evidence (typed dict: bound≤5, source, provenance_sha256, node, backend, observed_utc, validity_hours, gate_sha256=package_sha256), wal_baseline, operation_end_utc (S1–S4 required). Window authority keyed by package_sha256 at a stable location; receipts are verified JSON bound to source+package; failed/completed/inflight windows issue no new budget.
3. Aggregates: PASS (exit 0) / FAIL, INCONCLUSIVE (exit 1) / gate-reject (exit 2). No-overwrite + window authority block re-run.
4. Full offline suite: `bash portal/tools/run_offline_suite.sh` (nonzero on any mandatory error).
5. CI release: publish template → manual dispatch (separate future authorization). Seed: separate one-shot bootstrap — Owner supplies the typed first-creation gate via workflow input (never materialized from nowhere).

## CI-only / NOT_EXECUTED
```text
CI_RELEASE, WORKFLOW_PUBLICATION_DISPATCH, BOOTSTRAP_PUSH, LIVE_READINESS = NOT_EXECUTED
Runner dependency contract (uidmap/slirp4netns versions), rootless buildctl availability,
registry private visibility, cosign/syft/trivy runtime, live clock evidence = external prerequisites
(source-described and offline-verified, not executed now).
```
