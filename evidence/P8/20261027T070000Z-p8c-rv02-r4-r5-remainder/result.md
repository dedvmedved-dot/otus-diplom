# P8C RV-02 — R4/R5 closure (review f080cc3)

Date: 2026-10-27 UTC.

## R4-A — outbound API-request version pinning
C1-C5 now use fixed `--raw` API paths (no `-o json`, no preferred-version lookup):
C1 `/apis/barmancloud.cnpg.io/v1/namespaces/portal/objectstores/portal-db-backup`;
C2 `/apis/postgresql.cnpg.io/v1/namespaces/portal/clusters/portal-db`;
C3 `/apis/crd.projectcalico.org/v1/networkpolicies`;
C4 `/apis/crd.projectcalico.org/v1/globalnetworkpolicies`;
C5 `/apis/crd.projectcalico.org/v1/felixconfigurations/default`.
Projector `_require(apiVersion=...)` remains a second boundary. `test_literal_api_paths`
asserts the literal argv independent of READ_CONTRACT routing.

## R4-B — bounded design completed
`supplemental-design.md` rewritten with six sections: (1) full per-read contract
(ID/argv/scope/deps/shape/typed output/FLOW-ID), (2) digest identity comparison mode +
supported/unsupported representations, (3) Felix default-only precedence limit, (4)
Barman controller/instance-manager/native-sidecar roles + declared-port direction limit,
(5) API/DNS interpretation under Calico CNI, (6) monitoring not-found / unsupported
policy kinds / Gateway PLANNED.

## R5 — traceability
`coverage-matrix.md`: full requirement→code→test→evidence mapping. Design/request
description corrected from "version-qualified names" to actual fixed `--raw` requests +
separate response validation. collection-map ObjectStore = NOT_COLLECTED_AT_CORRECT_PATH.

## Status
```text
RECOVERY_MAIN_SHA: eb2b40ccfb9eac7d188ce2d243541811db6797dd
FINAL_SOURCE_SHA: cdc249deb3213274fbead006203fbd159371651e
SUPPLEMENTAL_TESTS: 32/32 PASS
R2: CLOSED; R3: CLOSED; R4-A/B: complete; R5: matrix complete
PHASE2_LIVE_READS_APPROVED: NO
OWNER_PHASE2_HANDOFF_ALLOWED: NO
NETPOL_APPROVED_FOR_APPLY: NO
BASE_INVENTORY_ARTIFACT_REVIEW: ACCEPTED_WITH_LIMITS; INVENTORY_EXIT_CODE=1 (preserved)
FLOW_MATRIX_COMPLETE: NO
PHASE2_PACKAGE_REVIEW_READY: YES
P8C: NOT_FINAL_ACCEPTED; P8D–P8G/P9: NOT_AUTHORIZED
CI_RELEASE / OWNER_HELPERS / PRODUCTION_MIGRATION_DEPLOYMENT: NOT_EXECUTED
```
