# P8C-RV02-PODLIST-ITEM-COMPATIBILITY — MI-01/MI-02 source fix

Date: 2026-11-02 (UTC). Executor: PRIMARY HERMES. Offline source-only correction per review 980cee5.
No SSH/live/registry, no rerun, no policy/CI/production changes. supplemental.py byte-identical.

## MI-01 — typed PodList item TypeMeta compatibility
Root cause (proven by review 980cee5 against Kubernetes v1.36.2 sources): core/v1 PodList.Items
is []Pod and the JSON serializer emits items WITHOUT TypeMeta. The strict `project_pod_identity`
starts with `_require(obj,'Pod','v1')`, so absent kind/apiVersion failed.
Fix in followup.py only:
- `_i1_adapt_type_meta(item)` runs AFTER the raw endpoint, PodList/v1 envelope, metadata/
  resourceVersion, continue and limit-200 checks have passed.
- Absent `kind`/`apiVersion` are filled from the verified typed-list context (Pod/v1) on a copy
  (`dict(it)`) — the input object is never mutated.
- Present-but-invalid value (null, empty string, bool/number/list/object, wrong kind/version) →
  PARSE_ERROR with itemDiag TYPEMETA_KIND / TYPEMETA_API_VERSION; never overwritten.
- The unchanged strict `project_pod_identity` + S1 identity gate run afterward.

## MI-02 — value-free itemDiag
ITEM failures now carry an optional finite `itemDiag` code (never a raw value/token/object):
```text
TYPEMETA_KIND | TYPEMETA_API_VERSION | METADATA | SPEC | CONTAINERS | CONTAINER_NAME | IMAGE |
IMAGE_ID | PORTS | RESTART_POLICY | STATUS | SERIALIZATION | OTHER
```
`_i1_item_diag(item)` classifies the failure structurally; `OTHER` is the safe fallback when not
confidently distinguishable. Error projection stays empty, complete=false, five dependent reads
blocked; F-CS/F-CNP continue. valid-but-unbound identity remains UNSUPPORTED with the safe
projection (no itemDiag, no digest/image allowlist expansion).

## Tests
```text
followup_test.py: 143/143 PASS (TestTypedPodListBoundary 6 + TestI1ItemDiag 15 added)
supplemental_test.py: 36/36 PASS (byte-identical: blob 1b613fbd…, sha256 ddd9a4dc…)
supplied podlist_boundary_regression_test.py: 6/6 PASS
Python 3.11.15
START_UTC=2026-11-02T07:35:04Z · END_UTC=2026-11-02T07:35:07Z
```

## File hashes
```text
followup.py:      blob 4292774bb7031e2be9c2c4fffb19169c2e88f55f  sha256 374e4be65d58da1c64090429f6808380a1a453a8b65c55e08898184d6220397e
followup_test.py: blob 23d969d02518e348e4f720e9b87c741fa01786be  sha256 913f38481d00ce909865664c63dabef7137821e3f853403793dc771a9915a10e
supplemental.py:  blob 1b613fbd1e35a109072d2843d6e5f3a3fd47b3d6  sha256 ddd9a4dc17bca97d6b36ae6b4d501e1722c5d38d6e5ac8c7b051698fa0b15491 (UNCHANGED)
```

## Requirement → code → test → evidence
| Requirement | Code | Test |
|---|---|---|
| absent TypeMeta derived from verified context | `_i1_adapt_type_meta` + `dict(it)` copy | TestTypedPodListBoundary (explicit/both/kind/version absent) |
| present-invalid TypeMeta rejected | `_i1_adapt_type_meta` | test_present_invalid_typemeta_stays_rejected + TestI1ItemDiag |
| finite itemDiag codes, no raw values | `_i1_item_diag` + `I1_ITEM_CODES` | TestI1ItemDiag (12 classes) + test_canary_not_leaked_in_item_diag |
| gate not bypassed by omission | `_read_podlist` UNSUPPORTED path | test_omission_does_not_bypass_identity_gate |

## Status
```text
REVIEW_HEAD / RECOVERY_MAIN_SHA: 980cee55e32bf87451919d37c898d40ae33d4557
ACCEPTED_SOURCE_SHA (under review): fdfc776570c7f44e559eefcd092e2ca58595ee48
MI01=FIXED · MI02=FIXED
SUPPLIED_REGRESSION=6/6 · FOLLOWUP_TESTS=143/143 · SUPPLEMENTAL_TESTS=36/36
SUPPLEMENTAL_BYTE_IDENTICAL=YES
LIVE_FAILING_FIELD=UNKNOWN
SOURCE_PACKAGE=REVIEW_READY
NEW_GATE_RUN_BUDGET=CONSUMED
PHASE2_NEW_RUN_APPROVED=NO · NETPOL_APPROVED_FOR_APPLY=NO
P8C=NOT_FINAL_ACCEPTED · P8D–P8G/P9=NOT_AUTHORIZED
```
STOP for Architect review. No live rerun authorized by this source change.
