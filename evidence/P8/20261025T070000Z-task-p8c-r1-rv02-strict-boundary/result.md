# P8C RV-02 — strict boundary closure (review 3026de4)

Date: 2026-10-25 UTC. Correction of review 3026de4 remaining findings.

## Findings → fixes → tests

| Finding | Fix | Test |
|---|---|---|
| Unsupported URL scheme / non-string pass through; IPv6 corrupted; arbitrary path retained | `sanitize_url` strict: origin-only (scheme://host[:port]), IPv6 brackets preserved, unsupported scheme / non-string / bad authority / bad port → None (omit); path always dropped; applied to endpointURL + destinationPath | test_sanitize_url_unsupported_scheme_omits, _wrong_type_omits, _path_dropped, _ipv6, _uppercase_scheme, _malformed_port_omits, test_destination_path_sanitized |
| spec="bad" → AttributeError | `_dict` + all projectors use `_dict(obj.get('spec'/'status'))`, never `or {}` | test_bad_spec_rejected, test_bad_spec_via_main |
| wrong kind / missing identity accepted | `_require_kind` (resource↔kind) + `_require_name` (name required) | test_wrong_kind_rejected, test_missing_identity_rejected |
| matchExpressions / endPort objects exported verbatim | `_selector` validates matchExpressions list; `_port` validates endPort integer | test_bad_match_expressions_rejected, test_bad_endport_rejected |
| main-path error behavior not asserted | main-path TimeoutExpired→TIMEOUT + OSError→GET_FAILED, empty output, nonzero exit, no leak | test_subprocess_timeout_via_main, test_subprocess_oserror_via_main |
| collection-map/handoff inaccurate | node annotations claim removed; kube-proxy name/labels identity-only; CNI-policy NOT_DEFINED; monitoring "not found in surveyed sources"; Gateway/Envoy refs conditional | (docs: collection-map.md, operator-handoff.md) |

## Status fields
```text
RECOVERY_MAIN_SHA: e076ad9d9cdfcaa7348b562c56ce415bdadb7ddd  (actual fetched head)
FINAL_SOURCE_SHA: a56585092e9f30e69a71b2ceba154b7fdc4a46a2
FINAL_REMOTE_MAIN_SHA: <set after evidence push>
APPLICATION_RUNTIME_SOURCE_UNCHANGED: YES (817f0ece…)
NATIVE_PG17_EVIDENCE: ACCEPTED_PREVIOUSLY_NOT_RERUN
ACCESS_PATH: NONE
NETPOL_LIVE_INVENTORY: NOT_EXECUTED (BLOCKED_EXTERNAL)
OWNER_INVENTORY_SCRIPT_APPROVED: NO
FLOW_MATRIX_COMPLETE: NO (14 FLOW-IDs; 8 live-only UNKNOWN)
OFFLINE_FLOW_TESTS: PASS (python 39/39; go networkpolicy PASS)
SECRET_SCAN: heuristic; documentation reference patterns only, no values
NETPOL_PACKAGE_REVIEW_READY: YES
NETPOL_APPROVED_FOR_APPLY: NO
CI_RELEASE / OWNER_HELPERS / PRODUCTION_MIGRATION_DEPLOYMENT: NOT_EXECUTED
P8C: NOT_FINAL_ACCEPTED
P8D–P8G/P9: NOT_AUTHORIZED
```

## Script hashes (literal, post-fix)
- inventory.py: git blob `3def89382087d3c202037fcc906fa13287254867`, SHA-256 `c735214f0570c32ff87c25c78453c350d04a05749886e0e87f40fec9be4851a9`
- inventory_test.py: git blob `eb28cb5e1575a39e7c26e5e46dc99f936e4f30f7`, SHA-256 `05abd66943aa0ed7bd0eef8c116ad9b0869b2861103bc56bfca4b27d9f371dff`
- collection-map.md: git blob `387938acbbe40096a211fd852bbb2c2206cd314c`

## Still BLOCKED_EXTERNAL
Live inventory requires an authorized cluster session; script prepared for
review, NOT handed to an operator yet.
