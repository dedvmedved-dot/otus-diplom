# P8C-R1 RV-02 — bounded projection completion B1/B2

Date: 2026-11-01 (UTC). Source-only. No cluster access, no live run. Accepted R2/R3, FU-01/FU-07,
S1, schema normalizer, registry chain, supplemental.py, typed contract, Portal untouched.

## Provenance / environment
```text
RECOVERY_MAIN_SHA: 3be8d6746b0e4aad3880128230e453da628b4934 (Architect commit)
SOURCE_SHA: 05d61ac74e88256adee455dcefd2d9c33335b6b3
Python: 3.11.15
START_UTC: 2026-11-01T01:42:14Z · END_UTC: 2026-11-01T01:42:16Z
command: python3 networkpolicy/followup_test.py -v  (exit 0, 99 tests)
followup.py:      blob 8f2d7f6d0d3d033810046d93b33448f465ab57f6  sha256 f48cfc825f25a002cac6afcc63da9f7d5800a3a92b5bc231eeb456b7d6328b98
followup_test.py: blob 85ba87f1841a90a17b54e9bf0c5e758ed73ec633  sha256 e0d7172b6ba3b731d4371c7289f4f14a84cc47a0a8687c42436fc07b6081ede1
```

## B1 — bound BEFORE projection (done)
- After envelope/list validation, `remaining = TOTAL_CAP - len(projected)`; only
  `page_items[:remaining]` is shape-checked + projected + strictly serialized. The discarded
  overflow suffix is NOT processed (not shape-checked, not projected) and stays UNKNOWN.
- Outcome precedence preserved: `len(page_items) > remaining` → PARTIAL `over cap`; else
  `received > limit` → PARTIAL `page overlong`. Stop that read; complete=false.
- Valid prefix retained on overflow (bounded ≤ 500); malformed/unknown semantics WITHIN the
  retained prefix still PARSE_ERROR/UNSUPPORTED with empty output.

## B2 — truthful validated count (done)
- `entry['validated']` is incremented after EACH item's projection + strict serialization
  succeeds, so `[valid, malformed]` reports `validated=1` (received=2) on a mid-page error,
  while the affected record output stays empty; first-malformed stays `validated=0`.
- Counters never imply validation of the skipped overflow suffix.

## Results
```text
supplied bounded_projection_test.py: 4/4 PASS (B1/B2)
previous reviewer regression_test.py: 7/7 PASS
followup_test.py: 99/99 PASS (incl. integrated TestBoundedProjection)
supplemental_test.py: 36/36 PASS (unchanged)
```

## Status
```text
FOLLOWUP_SOURCE: REVIEW_READY
OFFLINE_TESTS: 99/99 + 36/36 + 7/7 + 4/4 (all supplied harnesses)
R1/R2/R3: CLOSED · S1/IDENTITY_CHAIN/FU-01/FU-07: ACCEPTED_NOT_REOPENED
PHASE2_NEW_RUN_APPROVED: NO
NETPOL_APPROVED_FOR_APPLY: NO
P8C: NOT_FINAL_ACCEPTED · P8D–P8G/P9: NOT_AUTHORIZED
```
STOP. No script transmitted; no live run; historical evidence unmodified.
