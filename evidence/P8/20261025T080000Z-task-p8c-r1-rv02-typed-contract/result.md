# P8C RV-02 — typed output contract closure (review 66ae7e7)

Date: 2026-10-25 UTC. Correction of review 66ae7e7 remaining findings.

## Fix: full typed output contract (not example-specific checks)

Added typed primitive validators — `_str`, `_int` (bounds), `_bool`, `_str_map`,
`_str_list`, `_enum`, `_port_value` — and applied them to EVERY exported leaf
across all six projectors:

| Output group | Typed validation now applied |
|---|---|
| Identity | `kind` REQUIRED + exact match (missing now fails); name string; namespace string if present; labels string→string map |
| Selectors | matchLabels string map; matchExpressions projected to key/operator/values only (unknown members dropped), operator enum In/NotIn/Exists/DoesNotExist, values string list |
| NetworkPolicy | policyTypes string enum list (Ingress/Egress); peer selectors typed; ipBlock.cidr string + except string list; port int(1..65535)/named-string; protocol enum TCP/UDP/SCTP; endPort int(1..65535) + ≥ port; bool rejected as int |
| GatewayClass/Gateway | controllerName/gatewayClassName strings; listeners typed name(string)/port(int 1..65535)/protocol(string) |
| Conditions | type/status/reason strings; status enum True/False/Unknown |
| CNPG | instances int ≥1; readyInstances int ≥0; storage/wal size strings; barmanObjectStoreName string; monitoring bool; phase string; typed conditions |
| ObjectStore | s3CredentialsName string; strict URL origin; endpointCA presence boolean only |

URL authority: whitespace/control characters in hostname now rejected (None), not
raw fallback. `urlsplit` alone is no longer treated as authority validation.

## Tests (36/36 PASS)
- Table-driven `TestMalformedLeaves` — 23 malformed leaf cases (from the review
  reproducer) each assert PARSE_ERROR + empty output + nonzero exit + no canary.
- matchExpressions unknown-member → dropped (projected to key/operator/values),
  canary absent, benign fields retained.
- Realistic valid fixtures for all six projectors with kind/apiVersion/identity/
  spec/status; assert required projected facts (not "result is list").
- Error paths (FORBIDDEN/TIMEOUT/CONNECTION) suppress stdout/stderr + exit1.
- no-overwrite: pre-existing output untouched, zero kubectl reads.
- Exact argv (--raw), no-kubectl-before-output, strict URL variants (IPv6,
  whitespace authority, malformed port, unsupported scheme, non-string).

## Status fields
```text
RECOVERY_MAIN_SHA: 22954c09478fe4abb7f831b2e61318ce32b59bbe  (actual fetched head)
FINAL_SOURCE_SHA: 3c661bd8099e37b8d0785ca6687306c4981c4312
FINAL_REMOTE_MAIN_SHA: <set after evidence push>
APPLICATION_RUNTIME_SOURCE_UNCHANGED: YES (817f0ece…)
NATIVE_PG17_EVIDENCE: ACCEPTED_PREVIOUSLY_NOT_RERUN
ACCESS_PATH: NONE
NETPOL_LIVE_INVENTORY: NOT_EXECUTED (BLOCKED_EXTERNAL)
OWNER_INVENTORY_SCRIPT_APPROVED: NO
FLOW_MATRIX_COMPLETE: NO (14 FLOW-IDs; 8 live-only UNKNOWN)
OFFLINE_FLOW_TESTS: PASS (python 36/36; go networkpolicy PASS)
SECRET_SCAN: heuristic; documentation reference patterns only, no values
NETPOL_PACKAGE_REVIEW_READY: YES
NETPOL_APPROVED_FOR_APPLY: NO
CI_RELEASE / OWNER_HELPERS / PRODUCTION_MIGRATION_DEPLOYMENT: NOT_EXECUTED
P8C: NOT_FINAL_ACCEPTED
P8D–P8G/P9: NOT_AUTHORIZED
```

## Script hashes (literal, post-fix)
- inventory.py: git blob `e8c7adc06860f4ec7b60bde487247fa8d5f4577b`, SHA-256 `afb9a38010a5787612c88bb84a8fe4968e3d8f95b83e19eb163189656a99123d`
- inventory_test.py: git blob `be4083321f3509aac2f257bc06c7694a5e63e65c`, SHA-256 `fe8efe57d043ba3708d65ec9a8e433db7ef114fca9b712e10b8a9fad5bf10fa5`

## Still BLOCKED_EXTERNAL
Live inventory requires an authorized cluster session; script prepared for
review, NOT handed to an operator yet.
