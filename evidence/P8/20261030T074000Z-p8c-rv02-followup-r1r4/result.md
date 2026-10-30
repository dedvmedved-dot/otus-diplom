# P8C-R1 RV-02 — follow-up collector corrections R1–R4

Date: 2026-10-30 (UTC). Source-only corrective pass per review d71af18. No cluster access,
no live execution. Accepted FU-01/FU-07, schema normalizer, S1, registry chain untouched.

## Environment / provenance
```text
RECOVERY_MAIN_SHA: e6df2a918d228fa0b448e02f2a735b716bd630f2
SOURCE_SHA: c4477cf299916332848a00af73f0927d427f4ba4
Python: 3.11.15
followup.py:      blob 719e778d35e80da148b727ddf63e1d7d474105b9  sha256 0023847b59d6c9439ed7c2c0a7f31c9d17884b928bfb23a559a414cbcd4942a5
followup_test.py: blob 50fe0e4858c8b7723cf2d1b1109188b26a1a857a  sha256 2830f2a6ae6b89bc29035228bef61a83a2f510c6ff65102a379b3cb1cf764c47
command: python3 networkpolicy/followup_test.py -v  (exit 0, 81 tests)
```

## R1 — preserved error state + journal (done)
- Every non-OK list result → `complete=false` (projector PARSE_ERROR / UNSUPPORTED / PARTIAL).
- Journal survives decode/envelope/item/projector failures; every attempted page recorded with
  page/limit/path/continue-present/start/end/actual-returncode(0 or null)/cause/received/validated.
- Known returncode (0) no longer replaced with null on parsing failure.
- Continuation token never emitted; per-page path/limit/token-present in journal.
Tests: `TestR1JournalAndExit.*` (projector error, unsupported projector, invalid-page journal+exit,
nonfinite GNP).

## R2 — boundary semantics + identity diagnostics (done)
- Per-page overlong (>requested limit) → PARTIAL `page overlong`; total>500 → PARTIAL `over cap`
  (bounded to 500); 200+1 across two pages = COMPLETE.
- `metadata.continue=null` → PARSE_ERROR; PodList resourceVersion must be nonempty string.
- Cluster-scope metadata.namespace: absent/empty-string only; explicit null/non-string/nonempty → PARSE_ERROR
  (applied to CNP/GNP/HEP/Tier/Felix/CRD).
- Structurally-valid but unbound identity → UNSUPPORTED with safe projected identity retained (no raw/env/args).
Tests: `TestR2Boundaries.*` (continue-null, namespace-null, unbound-identity-retained, 201 overlong,
200+1 complete).

## R3 — typed CRD version identity (done)
- Every `versions[]` element: nonempty-string name; `served` (when present) bool; exactly one v1alpha2;
  selected v1alpha2 must be served=True. Malformed entry → PARSE_ERROR, empty output, zero F-CNP calls.
Tests: `TestR3CRDVersions.*` (empty entry, name null, name int, served string).

## R4 — coverage + evidence (done)
- Added full-disposition assertions (category/complete/output/exit/journal counts) across the
  new R1–R3 classes; literal path + synthetic-token continuation exercised in mocks
  (`test_invalid_page_preserves_journal_and_exit`, `TestPagination`); canary no-leak retained.
- Three-Pod fixture is `DERIVED_FROM_ACCEPTED_EVIDENCE` (synthetic re-construction of safe projected
  fields only, original evidence not re-read).

## Status
```text
FOLLOWUP_SOURCE: REVIEW_READY (post R1-R4)
OFFLINE_TESTS: 81/81 PASS (followup) + 36/36 PASS (supplemental, unchanged)
IDENTITY_CHAIN / S1: ACCEPTED_PREVIOUSLY_NOT_RERUN
PHASE2_NEW_RUN_APPROVED: NO
NETPOL_APPROVED_FOR_APPLY: NO
P8C: NOT_FINAL_ACCEPTED · P8D–P8G/P9: NOT_AUTHORIZED
```
STOP. No script transmitted; no live run; historical evidence unmodified.
