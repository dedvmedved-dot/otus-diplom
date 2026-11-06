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
and overall checked in `budget_exhausted` + before each WAL sample (`_wal_budget_exhausted`).

## State machine (window authority)

`open_window` at a stable authority location (package_sha256, NOT state/output path). Statuses:
`inflight` (opened/crash) → no retry; `failed` (non-PASS after ≤3 slots) → no retry, no new budget;
`completed` (PASS) → no replay. A changed state-dir cannot bypass authority. Receipts are verified
JSON bound to source+package; only PASS writes the receipt and advances the stage.

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
| architect contract (frozen) | evidence contract_test.py | 15 methods | transcript |

Full suite (isolated authority per file): 23 readiness + 25 residual-working + 3 qualification +
4 release + 7 release-negative + 28 regression + 14 scheduler + 15 contract = **119 methods**.

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
