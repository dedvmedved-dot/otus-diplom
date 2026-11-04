# P8C-R1-EXECUTABLE-RELEASE-AND-READINESS-R1 — result

Дата: 2026-11-04 (UTC). PRIMARY HERMES. Source-only package. Live/SSH/CI/registry-private/apply/production НЕ выполнялись.

## G1 — public pin verification (VERIFIED, per item)
6 binaries + 3 action SHAs + postgres digest — все VERIFIED (точные bytes/sha256 сверены по официальным
upstream HTTPS/CDN; action SHAs как существующие commits; postgres digest через anonymous public bearer).
Result: evidence/P8/20261104T085300Z-…/pin-verification.json.

## G2/G3 — release + seed templates (source-qualified)
- release template: + timeout-minutes 20/30; immutable checkout SHA + persist-credentials:false;
  permissions contents:read / +packages:write +id-token:write; no deploy/SSH/kubectl/production step.
- seed template (p8c-portal-seed.yml.template): exact target ghcr.io/dedvmedved-dot/otus-diplom-portal,
  bootstrap-seed not-deployable, private precondition via release-check.py private, packages:write.
- `release_qualification.py` + `test_release_qualification.py` (3 tests PASS; YAML 1.2 `on` handling).

## G4/G5 — readiness wrapper (source-qualified)
- `portal/tools/readiness/` — declarative readset.json (PR-3/5/6, HC-DB/ARCH-STATE/OP/DNS/PORTAL/GW,
  WAL), wrapper.py (argv kubectl get --raw, no shell=True, path validation, envelope+continue checks,
  fail-closed, no-overwrite, bounded, value-free journal), test_readiness.py (14 tests PASS: gate
  validation/expiry/TEST_ONLY/budget/context, envelope continue/malformed, path rejection, no-overwrite,
  fail-closed zero-request on rejected gate).

## Offline tests (all PASS)
```text
readiness: python3 -m unittest test_readiness → 14 tests OK
qualification: python3 -m unittest test_release_qualification → 3 tests OK
qualification check: release_qualification.py → {"errors": [], "qualified": true}
shell syntax: bash -n install-verified-go.sh → OK
go networkpolicy suite (unchanged, prior run): 4 func / 107 subtests (не перезапускался)
```

## Итог
```text
TASK_ID=P8C-R1-EXECUTABLE-RELEASE-AND-READINESS-R1
RECOVERY_MAIN_SHA=5d71dfc345cfacfe98bff42381b7aa36984a7bed
RELEASE_TEMPLATE_SOURCE_QUALIFIED=YES · PRIVATE_SEED_TEMPLATE_SOURCE_QUALIFIED=YES
PUBLIC_PINS_VERIFICATION=ALL_VERIFIED (10/10)
READINESS_WRAPPER_SOURCE_QUALIFIED=YES
READINESS_OFFLINE_TESTS=PASS (14) · RELEASE_OFFLINE_TESTS=PASS (3)
CLOCK_EVIDENCE_METHOD=UNRESOLVED (не найден источник в repo; future read proposal required)
REMAINING_EXTERNAL_PREREQUISITES: clock skew evidence; runner dependency contract; CI/registry private verification.
CI_RELEASE=NOT_EXECUTED · WORKFLOW_PUBLICATION_DISPATCH=NOT_EXECUTED · BOOTSTRAP_PUSH=NOT_EXECUTED
LIVE_READINESS=NOT_EXECUTED · NETPOL_APPROVED_FOR_APPLY=NO · OWNER_HELPERS=NOT_EXECUTED
PRODUCTION_MIGRATION_DEPLOYMENT=NOT_EXECUTED · P8C=NOT_FINAL_ACCEPTED · P8D–P8G/P9=NOT_AUTHORIZED
```
STOP для Architect review.
