# P8C RV-02 — R1..R5 closure (review 8598f73)

Date: 2026-10-27 UTC.

## Closures
| R | Fix |
|---|---|
| R1 identity contract | exact finite pin: `quay.io/calico/node@sha256:f4fafd8...` (or same-image tag `v3.32.0`); imageID must be a valid containerd/docker digest (`://sha256:<64hex>`); every selected calico-node pod must be compatible AND use a single consistent runtime digest; wrong registry/version/digest/unclassified-member → C3/C4/C5 blocked |
| R2 finite semantic contract | `icmp{type,code}`, `notICMP{type,code}`, GNP `namespaceSelector` typed + preserved (in addition to notProtocol/ipVersion/http/serviceAccountSelector/services) |
| R3 scoped lists + typed | I1=kube-system / S1=portal / S2=cnpg-system namespace binding; `http.paths` no truthiness coercion (False/0/{}/[None] → reject); containerPort range 1..65535 |
| R4 request/design | identity read I1 precedes C3/C4/C5; discovery validates exact kind/scope/verbs; named reads bound to namespace+name; design limits documented (Felix default-only, Barman direction UNKNOWN) |
| R5 docs | PLAN/flow-matrix/collection-map/gaps synced (28/28, I1 dependency, Felix fields, S1/S2 sidecar path) |

## Tests (28/28 PASS)
Identity exact contract (pin accepted; wrong registry/version/digest/mixed/wrong-ns/unidentified → 0 dependent calls), icmp/notICMP/namespaceSelector preserved, scoped pod-list namespace, http.paths malformed, containerPort range, plus all prior accepted cases.

## Status
```text
RECOVERY_MAIN_SHA: 5f314b28b338a765ab6e012eca5656724c7bc665
FINAL_SOURCE_SHA: 212e31c946bef3ee0a5ff2ce0a5481eb7c838fb8
SUPPLEMENTAL_TESTS: 28/28 PASS
PHASE2_LIVE_READS_APPROVED: NO
OWNER_PHASE2_HANDOFF_ALLOWED: NO
NETPOL_APPROVED_FOR_APPLY: NO
BASE_INVENTORY_ARTIFACT_REVIEW: ACCEPTED_WITH_LIMITS; INVENTORY_EXIT_CODE=1 (preserved)
FLOW_MATRIX_COMPLETE: NO
PHASE2_PACKAGE_REVIEW_READY: YES
P8C: NOT_FINAL_ACCEPTED; P8D–P8G/P9: NOT_AUTHORIZED
CI_RELEASE / OWNER_HELPERS / PRODUCTION_MIGRATION_DEPLOYMENT: NOT_EXECUTED
```
