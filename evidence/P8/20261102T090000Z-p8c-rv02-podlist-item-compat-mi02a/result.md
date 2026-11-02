# P8C-RV02-PODLIST-ITEM-COMPATIBILITY — MI-02A diagnostic correction

Date: 2026-11-02 (UTC). Executor: PRIMARY HERMES. Offline source-only, per review 4913f07.
MI-01 is ACCEPTED and NOT reopened. No SSH/live/registry, no policy/CI/production change.

## MI-02A — optional status must not mask a proven leaf failure
`project_pod_identity` uses `_dict(status)`: absent/null `status` becomes `{}` (optional). The
first-pass `_i1_item_diag` returned `STATUS` for any non-dict including `None`, so a genuine
image/ports/restartPolicy failure under an absent/null status was mislabeled `STATUS`.
Fix in `_i1_item_diag` only:
- `status is None` → local `{}` (matches `_dict` optional semantics); **no truthiness coercion**
  (`status or {}`), so `false`/`0`/`''`/`[]` are NOT hidden and still return `STATUS`.
- non-dict non-null status (false/0/''/list/list-of-object) remains `STATUS`.
- leaf failure now yields its own code (IMAGE/PORTS/RESTART_POLICY) or safe `OTHER`.
Blocking is unchanged: category=PARSE_ERROR, diag=ITEM, complete=false, empty output, five
dependent reads blocked, F-CS/F-CNP continue; no raw values/canary leak. Shared supplemental.py
and the accepted TypeMeta adapter / S1 are untouched.

## Tests
```text
followup_test.py: 147/147 PASS (TestOptionalStatusDiagnostic 4 methods / 14 subcases added)
supplemental_test.py: 36/36 PASS (byte-identical, not redeveloped)
supplied item_diag_regression_test.py: 4/4 PASS (14 subcases)
Python 3.11.15
START_UTC=2026-11-02T08:56:34Z · END_UTC=2026-11-02T08:56:38Z
```

## File hashes
```text
followup.py:      blob 4917bc9db76748202dfa3e799651474808aaf567  sha256 8e01355087db65d3c124f0a21ac5a4dd89acf0caaabc092836d469169fe57a7b
followup_test.py: blob fb1b191bc54c8382263cab68efbaebde7173a145  sha256 ed3356d1f9d576aa355ce66360e9a0066419067f4e1929053505bd6d3b4a20b3
supplemental.py:  blob 1b613fbd1e35a109072d2843d6e5f3a3fd47b3d6  sha256 ddd9a4dc17bca97d6b36ae6b4d501e1722c5d38d6e5ac8c7b051698fa0b15491 (UNCHANGED)
```

## Requirement → code → test → evidence
| Requirement | Code | Test |
|---|---|---|
| absent/null status → {} (not STATUS), leaf failure surfaced | `_i1_item_diag` `status is None → {}` | TestOptionalStatusDiagnostic.test_optional_status_does_not_mask_{image,ports,restart} (9 subcases) |
| false/0/''/list status still STATUS (no truthiness coercion) | `_i1_item_diag` `elif not isinstance(...)` | test_true_malformed_status_stays_status (5 subcases) |
| blocking + no canary leak preserved | unchanged fail-closed path | all `_check` assertions (0 deps, empty output, F-CS/F-CNP continue, no CANARY) |

## Status
```text
REVIEW_HEAD:             4913f07abd2914dbfa24f39526e05bbc9f0f4ca1
ACTUAL_PARENT:           239c593b76830889b290c8c091be671f522218f3
FINAL_SOURCE_SHA (TBD):  (set at commit)
MI01=ACCEPTED_NOT_REOPENED
MI02A=FIXED
SUPPLEMENTAL_BYTE_IDENTICAL=YES
LIVE_FAILING_FIELD=UNKNOWN
PHASE2_NEW_RUN_APPROVED=NO · NETPOL_APPROVED_FOR_APPLY=NO
P8C=NOT_FINAL_ACCEPTED · P8D–P8G/P9=NOT_AUTHORIZED
```
STOP for Architect review. No live rerun authorized by this source change.
