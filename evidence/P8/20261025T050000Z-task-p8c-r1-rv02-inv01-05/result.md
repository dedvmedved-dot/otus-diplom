# P8C RV-02 — INV-01…05 closure (targeted correction)

Date: 2026-10-25 UTC. Correction of review ce63489 findings.

## Findings → fixes → tests

| Finding | Fix | Test |
|---|---|---|
| INV-01 allowlist projection | Per-kind projectors (`project_networkpolicy/gatewayclass/gateway/envoyproxy/cnpg_cluster/objectstore`) extract explicit identity/labels/selectors/ports/endpoints/conditions; arbitrary spec/status fields, pod templates, env, inline config excluded; `sanitize_url` keeps scheme/host[:port]/path only | inventory_test.py TestAllowlistProjection (4 tests incl. canary + URL userinfo/query) |
| INV-02 fail-closed parsing | `project_list` raises on JSONDecodeError/wrong shape → `PARSE_ERROR`, empty output, nonzero exit; no raw-body fallback; valid-JSON scalar also fails | TestMain.test_malformed_json_fails_closed, test_invalid_shape_fails |
| INV-03 truthful argv | recorded argv == exact invocation incl. `--raw`; distinct TIMEOUT/FORBIDDEN/API_NOT_SERVED/CONNECTION/PARSE_ERROR/GET_FAILED | test_argv_preserves_raw, TestClassify (7) |
| INV-04 supplemental collection | namespaces, CNPG Cluster, ObjectStore, node CNI annotations, `--raw /apis`, PodMonitor ports + `collection-map.md` obligation→command→field→proof/limit | test_valid_full_object_projection_exit0 |
| INV-05 handoff + evidence | literal git blob + SHA-256 of script; source commit then evidence commit; overclaim removed | (this package: source fdf5bd1… + evidence) |

## Status fields
```text
RECOVERY_MAIN_SHA: c750dd710898962acfd465ca2b3ff92f82ea2f9a
FINAL_SOURCE_SHA: fdf5bd1387b9d54620f28558ff53fb353543cf33
FINAL_REMOTE_MAIN_SHA: <set after evidence push>
APPLICATION_RUNTIME_SOURCE_UNCHANGED: YES (817f0ece…)
NATIVE_PG17_EVIDENCE: ACCEPTED_PREVIOUSLY_NOT_RERUN
ACCESS_PATH: NONE (BLOCKED_EXTERNAL — no authorized kubectl)
NETPOL_LIVE_INVENTORY: NOT_EXECUTED
OWNER_INVENTORY_SCRIPT_APPROVED: NO (not handed to operator; review-only)
FLOW_MATRIX_COMPLETE: NO (14 FLOW-IDs; 8 live-only UNKNOWN, see gaps.md/collection-map.md)
OFFLINE_FLOW_TESTS: PASS (python 16/16; go networkpolicy unchanged PASS)
SECRET_SCAN: heuristic; only documentation reference patterns, no values
NETPOL_PACKAGE_REVIEW_READY: YES (targeted correction reviewable)
NETPOL_APPROVED_FOR_APPLY: NO
CI_RELEASE: NOT_EXECUTED
OWNER_HELPERS: NOT_EXECUTED
PRODUCTION_MIGRATION_DEPLOYMENT: NOT_EXECUTED
P8C: NOT_FINAL_ACCEPTED
P8D–P8G/P9: NOT_AUTHORIZED
```

## Script hashes (literal)
- inventory.py: git blob `d13d3dbce427f4ab88bcbc07e77c2a43611e6e7b`, SHA-256 `b706526718a58ae6c360005c9f06cb2e46dc90ae086077e6e289118aef01abdc`
- inventory_test.py: git blob `1a0ab741008da51cb5b913f7aff6a63f7c2e5075`, SHA-256 `16c0f258cce566136c6465783483d647f2fb1c972f26bb145c894278ab73b1cb`
- operator-handoff.md: git blob `4f5a61cf31d7814be6c89a9ad7348e2584799791`
- collection-map.md: git blob `b5e38531b60432cfd80e50274b6c8fe7c3abd9a1`

## Still BLOCKED_EXTERNAL
Live inventory requires an authorized cluster session (see operator-handoff.md);
the corrected script is prepared for review, not handed to an operator yet.
