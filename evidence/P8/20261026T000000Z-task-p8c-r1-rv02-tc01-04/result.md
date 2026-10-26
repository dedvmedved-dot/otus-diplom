# P8C RV-02 — TC-01…04 closure (review a532bf7)

Date: 2026-10-26 UTC. Correction of review a532bf7 four remaining groups.

## Fixes (required vs optional, not blanket coercion)

| ID | Fix | Tests |
|---|---|---|
| TC-01 containers | `_list_or_empty` (None→[], non-list false/0/''/{}→error); `_dict_req` for rule/peer/port/listener (null element rejected); `_selector(required=True)` rejects null top-level podSelector while `{}` remains legitimate | test_tc_cases_rejected (6), test_positive_empty_rule_and_selector |
| TC-02 identity | `_nonempty_str` rejects empty name; `_meta(namespaced=True)` requires nonempty namespace for 5 namespaced kinds, GatewayClass `namespaced=False` may omit | test_tc_cases_rejected (2), test_positive_cluster_scoped_identity |
| TC-03 required enums | `_enum(allow_none=False)` for matchExpression.operator and condition.status; protocol stays optional | test_tc_cases_rejected (2) |
| TC-04 range consistency | endPort requires numeric port (`not isinstance(port,int)` → error) + bounds + ≥port; named port without endPort preserved | test_tc_cases_rejected (2), test_positive_named_port_without_range, test_positive_numeric_range |

## Tests (42/42 PASS)
- `test_tc_cases_rejected` — all 12 review cases → PARSE_ERROR + empty output + nonzero exit.
- Positive counterparts: explicit `{}` selector / empty list / cluster-scoped identity / named port without range / numeric range / absent optional status all succeed.
- Real `apiVersion` per kind (networking.k8s.io/v1, gateway.networking.k8s.io/v1, gateway.envoyproxy.io/v1alpha1, postgresql.cnpg.io/v1, barmancloud.cnpg.io/v1) + per-kind projected-fact assertions (endPort 8010, cidr, controllerName, listener port 80, instances 3, storageSize 10Gi, endpointURL origin, s3CredentialsName).
- All previously accepted malformed-leaf/canary/error/no-overwrite/argv/URL tests retained.

## Status fields
```text
RECOVERY_MAIN_SHA: f95f9c23ef1b1292fba4796492074ac18b6eab00  (actual fetched head)
FINAL_SOURCE_SHA: 9a98b385c5a484b0a8f79086b432b8b72289ccee
FINAL_REMOTE_MAIN_SHA: <set after evidence push>
APPLICATION_RUNTIME_SOURCE_UNCHANGED: YES (817f0ece…)
NATIVE_PG17_EVIDENCE: ACCEPTED_PREVIOUSLY_NOT_RERUN
ACCESS_PATH: NONE
NETPOL_LIVE_INVENTORY: NOT_EXECUTED (BLOCKED_EXTERNAL)
OWNER_INVENTORY_SCRIPT_APPROVED: NO
FLOW_MATRIX_COMPLETE: NO (14 FLOW-IDs; 8 live-only UNKNOWN)
OFFLINE_FLOW_TESTS: PASS (python 42/42; go networkpolicy unchanged)
SECRET_SCAN: heuristic; documentation reference patterns only, no values
NETPOL_PACKAGE_REVIEW_READY: YES
NETPOL_APPROVED_FOR_APPLY: NO
CI_RELEASE / OWNER_HELPERS / PRODUCTION_MIGRATION_DEPLOYMENT: NOT_EXECUTED
P8C: NOT_FINAL_ACCEPTED
P8D–P8G/P9: NOT_AUTHORIZED
```

## Script hashes (literal, post-fix)
- inventory.py: git blob `5f0e2450358bfd9b08b542f013be5a914b9195a4`, SHA-256 `7806f494bcee93f31eb2cb0348d2cd8f7cbbf5743261336226a251643d8988a2`
- inventory_test.py: git blob `be985eb78a1b7f437d154a40b3564cab99243d07`, SHA-256 `6354b829de785472ca6ffd633456f3e6289ceff8fc4cdc6abb22c485e94244dd`

## Still BLOCKED_EXTERNAL
Live inventory requires an authorized cluster session; script prepared for
review, NOT handed to an operator yet.
