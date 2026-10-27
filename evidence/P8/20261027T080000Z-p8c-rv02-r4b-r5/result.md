# P8C RV-02 — R4-B/R5 closure (review 010ff33)

Date: 2026-10-27 UTC. R4-A CLOSED (fixed API paths preserved).

## R4-B.1 — unsupported identity diagnostic
`verify_calico_identity` now raises `UnsupportedIdentity` (distinct from malformed
input): a valid-but-unbound/unsupported image, version, digest representation or
relation yields **UNSUPPORTED** with the safe projected identity retained, nonzero
aggregate result, and C3/C4/C5 BLOCKED_NOT_EXECUTED (zero calls). Malformed JSON/types
stay PARSE_ERROR with empty output. `test_unsupported_identity_diagnostic` covers both.

## R4-B.2 — Barman four-role directed-flow
`supplemental-design.md` §4 now distinguishes CNPG controller, plugin controller/service
(cnpg-system 9090 — the plugin's own control surface, not a data path), per-instance
Barman sidecar (inside PostgreSQL pods, backup/WAL via CNPG 0.13.0 sidecars), and CNPG
instance manager (in-pod 8000). Pod-local vs inter-Pod flows separated; direction stays
UNKNOWN (declared ports ≠ traffic). Felix precedence (§3) + API/DNS (§5) + monitoring (§6).

## R5 — traceability corrected
`coverage-matrix.md`: 33/33, exact test IDs, fixed `--raw` request paths (not
resource.version.group), evidence root 070000Z, no stale `test_felix`, includes
`test_literal_api_paths` + `test_unsupported_identity_diagnostic`.

## Status
```text
RECOVERY_MAIN_SHA: e8fa08226e1cbc27796117adb52a98cd850582cb
FINAL_SOURCE_SHA: b623afb2fa9fd624e3e1ff418adeb9c71b1074df
SUPPLEMENTAL_TESTS: 33/33 PASS
R2: CLOSED; R3: CLOSED; R4-A: CLOSED; R4-B.1/B.2: complete; R5: matrix complete
PHASE2_LIVE_READS_APPROVED: NO
OWNER_PHASE2_HANDOFF_ALLOWED: NO
NETPOL_APPROVED_FOR_APPLY: NO
BASE_INVENTORY_ARTIFACT_REVIEW: ACCEPTED_WITH_LIMITS; INVENTORY_EXIT_CODE=1 (preserved)
FLOW_MATRIX_COMPLETE: NO
PHASE2_PACKAGE_REVIEW_READY: YES
P8C: NOT_FINAL_ACCEPTED; P8D–P8G/P9: NOT_AUTHORIZED
CI_RELEASE / OWNER_HELPERS / PRODUCTION_MIGRATION_DEPLOYMENT: NOT_EXECUTED
```
