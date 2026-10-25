# P8C RV-02 — revalidation closure (review 24a769d)

Date: 2026-10-25 UTC. Correction of review 24a769d remaining findings.

## Findings → fixes → tests

| Finding | Fix | Test |
|---|---|---|
| Node annotations bypass | nodes command now projects name + `.status.addresses` + `.spec.podCIDRs` only; no `.metadata.annotations`. Direct-stdout routes audited to exclude annotations/template/env | test_no_direct_stdout_collects_annotations_or_secrets |
| URL credentials (malformed port / uppercase scheme / destinationPath) | `sanitize_url` case-insensitive, invalid scheme/port → `None` (omit), never raw; applied to destinationPath + endpointURL | test_sanitize_url_malformed_port_omits, test_sanitize_url_uppercase_scheme, test_destination_path_sanitized |
| Nested bad metadata / empty {} | `_dict` type-validates metadata/status/selectors/rules/conditions; `project_list` requires `items` list (no single-object fallback), empty `items:[]` legitimate | test_nested_bad_metadata_rejected, test_empty_object_rejected, test_empty_items_list_ok, test_nested_bad_metadata_via_main |
| endPort lost | `_port` preserves `endPort` | test_endport_preserved |
| deadline→CONNECTION misclassification | classify: "deadline"/"timed out"/"context deadline exceeded" → TIMEOUT | test_deadline_timeout |
| Supplemental plan incomplete | collection-map.md two-phase discovery→projection map (CNI/proxy, CNI-policy, Barman plugin mapping, monitoring, Gateway/Envoy params) | (doc) |
| Valid-schema fixtures every projector | per-kind valid fixtures | test_valid_fixture_every_projector |

## Status fields
```text
RECOVERY_MAIN_SHA: e4c4626af1ddab9a6ac6d48244084457f170b00a   (actual fetched head for this corrective package)
TASK_BASELINE: c750dd710898962acfd465ca2b3ff92f82ea2f9a         (original RV-02 task)
FINAL_SOURCE_SHA: c80d2352115d48b017b45696c8e6e4d27ba6ac27
FINAL_REMOTE_MAIN_SHA: <set after evidence push>
APPLICATION_RUNTIME_SOURCE_UNCHANGED: YES (817f0ece…)
NATIVE_PG17_EVIDENCE: ACCEPTED_PREVIOUSLY_NOT_RERUN
ACCESS_PATH: NONE
NETPOL_LIVE_INVENTORY: NOT_EXECUTED (BLOCKED_EXTERNAL)
OWNER_INVENTORY_SCRIPT_APPROVED: NO
FLOW_MATRIX_COMPLETE: NO (14 FLOW-IDs; 8 live-only UNKNOWN)
OFFLINE_FLOW_TESTS: PASS (python 27/27; go networkpolicy PASS)
SECRET_SCAN: heuristic; documentation reference patterns only, no values
NETPOL_PACKAGE_REVIEW_READY: YES
NETPOL_APPROVED_FOR_APPLY: NO
CI_RELEASE / OWNER_HELPERS / PRODUCTION_MIGRATION_DEPLOYMENT: NOT_EXECUTED
P8C: NOT_FINAL_ACCEPTED
P8D–P8G/P9: NOT_AUTHORIZED
```

## Script hashes (literal, post-fix)
- inventory.py: git blob `a39aca5c8f7c614cb8990339de1d84430a935800`, SHA-256 `b6f6b1d2d6ea909ce72268fbd3d85d391551da9a3e073e532220c2fb60959fc5`
- inventory_test.py: git blob `1a49577f02d3dab317125b2f624630524d85cec0`, SHA-256 `221daddb10a04d366af843c2109817f0719971ba20a69421694b7e43af25ecf0`
- collection-map.md: git blob `bc0e0657c0a2b1b7f404878a1419992d2542dfdb`

## Still BLOCKED_EXTERNAL
Live inventory requires an authorized cluster session; script is prepared for
review, NOT handed to an operator yet.
