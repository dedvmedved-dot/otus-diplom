# P8C RV-02 — R2/R4/R5 closure (review 5d0e965)

Date: 2026-10-27 UTC.

## Closures
| R | Fix |
|---|---|
| R2 per-kind allowlist | `NP_SPEC_ALLOWED` (NetworkPolicy) excludes GNP-only fields; `GNP_SPEC_ALLOWED` adds applyOnForward/doNotTrack/preDNAT/namespaceSelector. A namespaced NetworkPolicy carrying a GNP-only field → `UnsupportedField` → UNSUPPORTED (no silent loss); GNP fields remain preserved on GlobalNetworkPolicy |
| R4 design | `supplemental-design.md`: per-read apiVersion pinning (projector `_require`), Felix default-only precedence limit (per-node mode UNKNOWN), Calico digest-comparison limit (textual equality vs pinned manifest digest; platform-child digests NOT accepted, live-only UNKNOWN), Barman directed-flow limit (declared ports ≠ observed traffic) |
| R5 docs | collection-map 31/31 + ObjectStore base read = NOT_COLLECTED_AT_CORRECT_PATH (spec.data wrong path); design doc added |

## Tests (31/31 PASS)
Per-kind spec allowlist (namespaced policy rejects namespaceSelector/applyOnForward/doNotTrack/preDNAT; GNP fields preserved), unsupported-field → UNSUPPORTED at 8 levels, identity exact contract, plus all prior accepted cases.

## Status
```text
RECOVERY_MAIN_SHA: eb2b40ccfb9eac7d188ce2d243541811db6797dd
FINAL_SOURCE_SHA: 85dcc0332a70f62f7ab4aacb156fd7014d0b8ca8
SUPPLEMENTAL_TESTS: 31/31 PASS
PHASE2_LIVE_READS_APPROVED: NO
OWNER_PHASE2_HANDOFF_ALLOWED: NO
NETPOL_APPROVED_FOR_APPLY: NO
BASE_INVENTORY_ARTIFACT_REVIEW: ACCEPTED_WITH_LIMITS; INVENTORY_EXIT_CODE=1 (preserved)
FLOW_MATRIX_COMPLETE: NO
PHASE2_PACKAGE_REVIEW_READY: YES
P8C: NOT_FINAL_ACCEPTED; P8D–P8G/P9: NOT_AUTHORIZED
CI_RELEASE / OWNER_HELPERS / PRODUCTION_MIGRATION_DEPLOYMENT: NOT_EXECUTED
```
