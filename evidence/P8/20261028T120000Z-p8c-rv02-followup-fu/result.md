# P8C-R1 RV-02 — follow-up collector corrections (FU-01..08)

Date: 2026-10-28. Source-only corrective pass per review 4c21b2a. No cluster access, no live
execution. Identity gate + registry chain not reopened; supplemental.py/S1 unchanged.

## FU fixes (requirement → code → test)
| FU | Fix | Coverage |
|---|---|---|
| FU-01 | `--context` must equal `kubernetes-admin@pak-portal`; validated BEFORE output-dir creation and any subprocess; one context used in all request paths and records | `TestContext.test_wrong_context_rejected_before_calls` (zero calls/no output), `test_approved_context_positive` |
| FU-02 | hard list envelope (kind+apiVersion per GVR), nonempty-string resourceVersion, absent-or-string continue, item-object check, PodList/v1 envelope, cap 500 items + 3 pages (overlong → PARTIAL `over cap`); wrong-list-kind/missing-metadata/null-rv/false-continue/scalar-item → PARSE_ERROR | `TestPagination.*` (oversized_501, three_pages_600, wrong_list_kind, missing_metadata, null_rv, false_continue, scalar_item) |
| FU-03 | first-page error → distinct FORBIDDEN/API_NOT_SERVED/CONNECTION/TIMEOUT/GET_FAILED with actual returncode (null if not obtained); later-page failure → PARTIAL retaining validated prefix + cause; per-page journal (page/limit/start/end/returncode/cause/count), continue token never emitted | `TestListErrors.*`, `TestPagination.test_no_continue_token_in_output` |
| FU-04 | structural isolation (scalar/null item/container/metadata → PARSE_ERROR, no crash, independent reads continue); cluster-scope namespace absent/empty enforced for CNP/GNP/HEP/Tier/Felix; NaN/Infinity rejected | `TestStructuralIsolation.*`, `TestClusterScope.*`, `TestTier.test_nonfinite_order` |
| FU-05 | `served is True` (not truthy), versions entries must be well-formed objects, corrected `normalize_schema` (drop `description` only as schema annotation, preserve semantic `description` property + literal defaults; unknown representation fails closed); mismatch → UNSUPPORTED, malformed → PARSE_ERROR | `TestCRDSchema.*` (served_string_false, malformed_version_entry, annotation-still-compatible, semantic-property-mismatch) |
| FU-06 | presence checks (explicit null rejected, absent allowed), per-direction rule allowlists (ingress `from`/egress `to`, wrong-direction → UNSUPPORTED), duplicate set-list members rejected, Tier/HEP/CNP labels preserved, HEP port.name accepts empty string (string), finite numbers | `TestCNP.*`, `TestHEP.*`, `TestTier.*` |
| FU-07 | per-resource discovery verdicts (`D1:<resource>` tokens); a missing/wrong descriptor blocks only its consumer | `TestDiscovery.test_missing_tier_blocks_only_tier` |
| FU-08 | full corrective suite 68/68 with distinct 201/501 objects, fixed context, three saved Pod identities, honest page journal | `followup_test.py` 68 tests |

## Test result
```text
followup_test.py: 68/68 PASS (FU corrective suite)
supplemental_test.py: 36/36 PASS (unchanged, no regression)
```
Schema fingerprint normalization verified against `schema_normalization_reference.py`:
pinned hash `770130a4…` unchanged; annotation-only change unchanged; semantic `description`
property changes hash; literal defaults preserved.

## Status
```text
RECOVERY_MAIN_SHA: ac587444f1da25d786541a6e71ef52446f833c77
FOLLOWUP_SOURCE: REVIEW_READY (post FU-01..08)
OFFLINE_TESTS: 68/68 PASS (followup) + 36/36 PASS (supplemental)
IDENTITY_CHAIN / S1: ACCEPTED_PREVIOUSLY_NOT_RERUN
PHASE2_NEW_RUN_APPROVED: NO
NETPOL_APPROVED_FOR_APPLY: NO
P8C: NOT_FINAL_ACCEPTED · P8D–P8G/P9: NOT_AUTHORIZED
```
STOP. No script transmitted; no live run.
