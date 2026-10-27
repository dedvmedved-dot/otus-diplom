# P8C RV-02 — R4/R5 remainder closure

Date: 2026-10-27 UTC. Continues after R2/R3 CLOSED.

## R4 — outgoing API-request version pinning
`READ_CONTRACT` config reads now use version-qualified resource names
(`resource.version.group`, e.g. `networkpolicies.v1.crd.projectcalico.org`,
`objectstores.v1.barmancloud.cnpg.io`, `clusters.v1.postgresql.cnpg.io`,
`pods.v1.`), so the requested API version is pinned rather than a preferred-version
lookup. Projectors still `_require(apiVersion=...)` on the response. Discovery (D1/D2)
validates the served groupVersion before dependent reads. Design doc updated
(`supplemental-design.md`).

## R5 — full evidence matrix
`coverage-matrix.md`: complete requirement→code→test→evidence mapping across the full
G2/SP scope (identity, discovery/request boundary, per-kind policy projection, typed
leaves, ObjectStore/CNPG paths, sidecar identity, Felix mode, Barman/API/DNS flow
limits, no-overwrite/no-kubectl, documentation sync), plus the enumerated live-only
UNKNOWN items.

## Status
```text
RECOVERY_MAIN_SHA: eb2b40ccfb9eac7d188ce2d243541811db6797dd
FINAL_SOURCE_SHA: 2e15ba3f5f6229ce708965fe534546d9f443cf0f
SUPPLEMENTAL_TESTS: 31/31 PASS
R2: CLOSED; R3: CLOSED (prior); R4: version pinning + design complete; R5: matrix complete
PHASE2_LIVE_READS_APPROVED: NO
OWNER_PHASE2_HANDOFF_ALLOWED: NO
NETPOL_APPROVED_FOR_APPLY: NO
BASE_INVENTORY_ARTIFACT_REVIEW: ACCEPTED_WITH_LIMITS; INVENTORY_EXIT_CODE=1 (preserved)
FLOW_MATRIX_COMPLETE: NO
PHASE2_PACKAGE_REVIEW_READY: YES
P8C: NOT_FINAL_ACCEPTED; P8D–P8G/P9: NOT_AUTHORIZED
CI_RELEASE / OWNER_HELPERS / PRODUCTION_MIGRATION_DEPLOYMENT: NOT_EXECUTED
```
