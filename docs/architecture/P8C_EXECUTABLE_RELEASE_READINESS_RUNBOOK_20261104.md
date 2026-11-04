# P8C Executable Release + Readiness — Runbook & Runtime Manifest (source-only)

Дата: 2026-11-04. PRIMARY HERMES. Source-only runbook; НЕ разрешение выполнить live/CI/push.

## Runtime manifest (исполняемые файлы + зависимости)

| Файл | Роль | Runtime deps |
|---|---|---|
| portal/tools/verify-pins.py | public pin verification | python3 stdlib (urllib) |
| portal/tools/release_qualification.py | template qualification | python3 + PyYAML |
| portal/tools/p8c-portal-release.yml.template | release workflow TEMPLATE | GitHub Actions runner (ubuntu-24.04), Go, buildkit/rootlesskit/syft/trivy/cosign |
| portal/tools/p8c-portal-seed.yml.template | private-seed TEMPLATE | GitHub Actions runner, buildkit |
| portal/tools/Seed.Containerfile | seed artifact recipe | buildctl |
| portal/tools/install-verified-go.sh | verified Go toolchain | curl, sha256sum, tar |
| portal/tools/release-check.py | fail-closed release metadata gates | python3 stdlib |
| portal/tools/readiness/wrapper.py | readiness wrapper | python3, kubectl (node-01, future gate) |
| portal/tools/readiness/wal.py | WAL observation | python3 urllib (injected) |
| portal/tools/readiness/readset.json | declarative read-set | — |

## requirement → code → test → evidence matrix

| Requirement | Code | Test | Evidence |
|---|---|---|---|
| G1 pin verification | verify-pins.py + pins.lock.json | exit 0 (10/10 VERIFIED) | pin-verification.json |
| G2 release template R-01..08 | p8c-portal-release.yml.template (+timeout-minutes) | release_qualification + test_release_qualification (3 PASS) | qualified:true |
| G3 seed bootstrap | p8c-portal-seed.yml.template + Seed.Containerfile | qualification (GITHUB_TOKEN env, noop, packages:write) | qualified:true |
| G4 readiness predicates | wrapper.py PREDICATES | test_readiness TestPredicates (HC-DB/ARCH/GW/PR3/PR5) | 20 PASS |
| G4 gate/state | wrapper.py validate_gate + atomic_reserve | TestGate + TestReservation | 20 PASS |
| G4 WAL | wrapper.py run_wal_sample + wal.py | TestWAL (clock/identity/failure/missing) | 20 PASS |

## Runbook (future operator, после отдельного gate)

1. Node-01 operator: `python3 portal/tools/readiness/wrapper.py --gate <issued-gate.json> --out <journal> --state-dir <state> --stage S0 --kubectl kubectl`
2. Gate manifest: mode=LIVE, context kubernetes-admin@pak-portal, source_sha, package_sha256 (=sha256(readset+wrapper+wal)), issued_at_utc, expiry_hours≤24, clock_skew_bound, wal_baseline, operation_end_utc.
3. Aggregates: PASS (exit 0) / FAIL, INCONCLUSIVE (exit 1) / gate-reject (exit 2). No-overwrite + atomic reservation block re-run.
4. CI release: publish template → manual dispatch (separate future authorization). Seed: separate one-shot bootstrap (Owner first-creation basis).

## CI-only / NOT_EXECUTED
```text
CI_RELEASE, WORKFLOW_PUBLICATION_DISPATCH, BOOTSTRAP_PUSH, LIVE_READINESS = NOT_EXECUTED
Runner dependency contract (uidmap/slirp4netns versions), rootless buildctl availability,
registry private visibility, cosign/syft/trivy runtime = CI-only prerequisites (source-described, not run).
```
