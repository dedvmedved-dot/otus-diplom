# P8C RV-02 — R1..R5 final closure (review e592b57)

Date: 2026-10-27 UTC.

## Closures
| R | Fix |
|---|---|
| R1 identity | runtime imageID must resolve to the pinned manifest digest by textual equality (`containerd://sha256:f4fafd8…`); a syntactically valid but unbound digest is rejected; wrong registry/version/unclassified member blocked; pin (`quay.io/calico/node@sha256:f4fafd8…`) and tag (`:v3.32.0`) are the only accepted references |
| R2 unsupported fields | finite allowlist contract at every nesting level (spec/rule/entity/http/http-path/icmp/serviceAccounts/services); unknown semantic key → `UnsupportedField` → UNSUPPORTED (never silent loss); known non-semantic (`metadata`, `performanceHints`) deliberately dropped |
| R3 | CLOSED (namespace binding, typed leaves, port range, http.paths) |
| R4 request/design | identity read precedes version-specific reads; exact digest pin; design limits documented (Barman direction UNKNOWN, Felix default-only) |
| R5 docs | PLAN.md + flow-matrix.md + collection-map.md + gaps.md all updated (Barman direction reconciled, identity pin, 28/28→29/29) |

## Tests (29/29 PASS)
Identity exact contract (pin accepted; unbound consistent digest, wrong registry/version/digest/wrong-ns/unidentified → 0 dependent calls), unsupported-field rejection at 5 levels → UNSUPPORTED, icmp/notICMP/namespaceSelector, plus all prior accepted cases.

## Status
```text
RECOVERY_MAIN_SHA: 58e6e640d9c12d7c212b1be06e30a32f147ab6d2
FINAL_SOURCE_SHA: 27a012134e37bf3e3dea1aff2dcbf1653ddfc5af
SUPPLEMENTAL_TESTS: 29/29 PASS
PHASE2_LIVE_READS_APPROVED: NO
OWNER_PHASE2_HANDOFF_ALLOWED: NO
NETPOL_APPROVED_FOR_APPLY: NO
BASE_INVENTORY_ARTIFACT_REVIEW: ACCEPTED_WITH_LIMITS; INVENTORY_EXIT_CODE=1 (preserved)
FLOW_MATRIX_COMPLETE: NO
PHASE2_PACKAGE_REVIEW_READY: YES
P8C: NOT_FINAL_ACCEPTED; P8D–P8G/P9: NOT_AUTHORIZED
CI_RELEASE / OWNER_HELPERS / PRODUCTION_MIGRATION_DEPLOYMENT: NOT_EXECUTED
```
