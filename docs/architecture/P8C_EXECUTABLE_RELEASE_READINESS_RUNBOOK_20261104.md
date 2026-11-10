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
on partial/error bodies; the read cap is lowered to the remaining body so a read can never exceed
the limit and then be truncated). Budget is stored at the stable authority (`budget_path(gate)` =
`RESERVATION_BASE/<package_sha256[:32]>/budget.json`), not the state-dir — a new state-dir cannot
reset consumption. Persistence is concurrency-safe and crash-durable: each charge is an atomic
`_charge` under a `fcntl.flock` sidecar lock that reads the current value, checks `current+delta
≤ cap`, and adds the delta (ADDITIVE, not MAX) before fsyncing the file and its directory and
doing the atomic `os.replace`. Independent concurrent charges therefore sum correctly and a single
remaining slot cannot be spent twice. `write_budget` remains the "set absolute" entry used by the
fixture/authority seeding. Overrun semantics split by field kind: continuous consumption
(bytes/seconds) is RECORDED even when it crosses the cap (`_charge(..., commit=True)`) so a failure
never turns into "nothing was consumed"; discrete reservations (requests/wal_requests) are not
recorded on overrun (`commit=False`) so a slot is not spent twice. Actual transport elapsed time
(`_io_call` around every kubectl/HTTP call) is charged to overall seconds alongside explicit sleeps,
so I/O time is not lost from the budget; `default_http_get` counts a late chunk and charges any
partial body (overall AND WAL subset) it already received before a deadline/transport error.
Exhaustion is a TERMINAL authority: `_overall_exhausted`/`_wal_exhausted` consult the on-disk
authority (recorded overruns count), so after the overall time budget is spent no further I/O is
issued; and every transport call's `timeout` is bounded up-front by the minimum of the remaining
enclosing deadlines — overall seconds, WAL seconds and the sample deadline (`run_read` and both WAL
metadata/HTTP reads use the CURRENT authority remainder, not a stale process-local base). Any
NaN/infinite/non-finite budget field blocks before any read.

## State machine (window authority)

`open_window` at a stable authority location (package_sha256, NOT state/output path). Statuses:
`inflight` (opened/crash) → no retry; `failed` (non-PASS after ≤3 slots) → no retry, no new budget;
`completed` (PASS) → no replay. A changed state-dir cannot bypass authority. Receipts are verified
JSON bound to source+package+issued_at (a receipt from a different gate is not authority). S1–S4
require an operation boundary (`operation_end_utc` ≥ issued_at) bound to a verified `action_receipt`
that confirms the specific gate (`gate_sha256` = `gate_identity_sha256`), the previous `stage`, a
successful `outcome=PASS` and the operation time — three equal fields are insufficient. The WAL
baseline stores the pod UID (observation identity) + observed time and re-checks the UID on read;
a cross-sample pod UID change invalidates the comparison.

## Health windows + freshness at verdict

Health reads (HC-*) use a per-check W/I/N scheduler driven by a single table (W = absolute window,
I = retry interval, N = TOTAL observations INCLUDING the first GET and the final freshness re-read;
retries = N−2): DB/ARCH (shared), OP, Portal = W60/I10/N6; DNS = W30/I5/N6; Gateway = W120/I10/N12.
A first observation's FAIL is preserved (failure precedence — never erased by a later sweep); a
transient INCONCLUSIVE is retried after the per-check interval inside the absolute window; and the
final freshness re-read (reverse order so the shared DB/ARCH observation is the freshest) is gated
on per-check age (≤30 s for normal checks, ≤60 s for Gateway). The window end is anchored to each
check's FIRST observation (not a shared clock); it is checked before the sleep, after the sleep,
and at GET completion, and the transport timeout is bounded by the remaining window — so a late
healthy response (retry or final freshness re-read) never closes a check that never passed inside
its allowed window.
Predicates enforce the exact GVR binding per read (`kind` AND `apiVersion`, not just the broad
`ALLOWED_API` or a name ending in `List`): HC-DB/ARCH-STATE must be `Cluster`@`postgresql.cnpg.io/v1`,
PR-6 must be the nine expected (kind, apiVersion) pairs with typed items/max_items, PR-5 must be
`ServiceList`@`v1` with uid/namespace=envoy-gateway-system/ownership labels. Diagnostics are
value-free (no raw condition value, field name, or unknown key is echoed). Malformed/nested items
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
| architect scheduler regression (active working copy) | portal/tools/readiness/test_scheduler_authority_working.py | 14 methods | transcript |
| architect contract (active working copy) | portal/tools/readiness/test_contract_authority_working.py | 15 methods | transcript |
| architect completion contract (active working copy) | portal/tools/readiness/test_completion_authority_working.py | 34 methods | transcript |
| architect residual contract (active working copy) | portal/tools/readiness/test_residual_contract_working.py | 20 methods | transcript |
| pin verification (10/10, offline) | verify-pins.py --offline | launcher → exit 0 | pin-verification-offline.json |

Full suite (isolated authority per file): 23 readiness + 25 residual-working + 3 qualification +
4 release + 7 release-negative + 5 route E2E + 28 regression + 14 scheduler + 15 contract-authority
+ 34 completion-authority + 20 residual-contract + 17 remaining-contract (active) + 12
residual-contract (c98fea1) + 7 final-contract (935feb3) + 12 remaining-execution (a5e58bd) =
**226 methods**, plus qualification CLI (`qualified:true`) and offline pin verification.

Release-gate binding (R3): the `release-gate` and `first-creation` validators require the actual
run attempt (`argv run_attempt` / `GITHUB_RUN_ATTEMPT` = 1) AND a typed integer `attempt=1` in the
document (missing/null/bool/2 all rejected — no permissive bypass), `workflow_sha` equal to the
runtime `GITHUB_WORKFLOW_SHA` (a missing runtime binding is NOT authorization), and an
already-elapsed `issued_at_utc` (no future grace). Route E2E (R4) executes the full seed
CREATE_ALLOWED and release routes with only the network-only modes (private/registry) and external
tool binaries faked; the gate/digest/predicate/`verified` validators run for real,
`GITHUB_ENV`/`GITHUB_OUTPUT`/`if:`/`always()` cleanup are emulated, and the exit code of every
mandatory step is asserted (a digest mismatch is caught). A single shared route runner handles
positive and negative routes: a nonzero non-always step marks failure and skips subsequent protected
steps, `if: always()` cleanup still runs, and a nonzero cleanup is itself recorded as a route
failure (always determines execution, not whether the return code counts).

Note: the frozen historical completion_contract_test.py / residual_contract_test.py are NOT modified;
their positive S0→S4 flows predate the action-receipt binding, so the active working copies add the
typed `action_receipt` to those positive flows (per the single-pass correction directive). The
historical budget-fixture correction (exhausted authority via `write_budget`) is likewise adopted in
the active working copy.

## Runbook (future operator, после отдельного gate)

1. Operator: `python3 portal/tools/readiness/wrapper.py --gate <issued-gate.json> --out <journal> --state-dir <state> --stage S0 --kubectl kubectl`
2. Gate manifest: mode=LIVE, context kubernetes-admin@pak-portal, source_sha, package_sha256 (=sha256(readset+wrapper+wal)), issued_at_utc, expiry_hours≤24, clock_evidence (typed dict: bound≤5, source, provenance_sha256, node, backend, observed_utc, validity_hours, gate_sha256=gate_identity_sha256(gate) — bound to THIS gate, not the package hash), wal_baseline, operation_end_utc + action_receipt (S1–S4 required). Window authority keyed by package_sha256 at a stable location; receipts are verified JSON bound to source+package; failed/completed/inflight windows issue no new budget.
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
