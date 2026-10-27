# P8C RV-02 — SP-01..05 final closure (review 3262a9b)

Date: 2026-10-27 UTC.

## Remaining SP closures
| SP | Fix |
|---|---|
| SP-01/SP-04 identity gate | `verify_calico_identity` — requires ≥1 calico-node container, image matching `calico/node:.*v3.32` (source pin calico-v3.32.0.yaml), and a present imageID; empty/unreviewed/missing-imageID/mixed → C3/C4/C5 blocked (0 calls) |
| SP-01 discovery scope | `namespaced`/`kind` required (null → PARSE_ERROR, not bypass); exact scope compared |
| SP-01 unsupported vs malformed | D2 policy kinds classified; unsupported → **UNSUPPORTED** category + sanitized discovery preserved (not PARSE_ERROR); malformed JSON stays PARSE_ERROR |
| SP-02 policy semantics | notProtocol (int\|str), ipVersion (4\|6), http{methods,paths}, spec.serviceAccountSelector, entity.services{name,namespace} — all typed + preserved |
| SP-03 named binding | ObjectStore/Cluster bound to namespace `portal` + exact name; Felix bound to `default` |
| SP-03 typed | containerPort = Kubernetes int (not string); status containerStatuses/initContainerStatuses validated as lists (malformed → PARSE_ERROR, not silent absence) |

## Tests (23/23 PASS)
Identity gate (empty/unreviewed/missing-imageID/mixed → 0 dependent calls), missing discovery scope, unsupported discovery, semantic-field preservation (notProtocol/ipVersion/http/serviceAccountSelector/services), wrong namespace/name binding, string containerPort reject, invalid status reject, plus all prior accepted cases.

## Status
```text
RECOVERY_MAIN_SHA: b92320d16814d8c8e23863fb2de05809be2aa755
SP-01..05: CLOSED (source + tests)
SUPPLEMENTAL_TESTS: 23/23 PASS
PHASE2_LIVE_READS_APPROVED: NO
OWNER_PHASE2_HANDOFF_ALLOWED: NO
NETPOL_APPROVED_FOR_APPLY: NO
BASE_INVENTORY_ARTIFACT_REVIEW: ACCEPTED_WITH_LIMITS; INVENTORY_EXIT_CODE=1 (preserved)
FLOW_MATRIX_COMPLETE: NO
PHASE2_PACKAGE_REVIEW_READY: YES
P8C: NOT_FINAL_ACCEPTED; P8D–P8G/P9: NOT_AUTHORIZED
CI_RELEASE / OWNER_HELPERS / PRODUCTION_MIGRATION_DEPLOYMENT: NOT_EXECUTED
```
