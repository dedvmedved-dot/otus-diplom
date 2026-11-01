# P8C-R1 RV-02 — follow-up collector completion R1/R3/R4

Date: 2026-11-01 (UTC). Source-only. No cluster access, no live run. Accepted FU-01/FU-07/R2,
schema normalizer, S1 identity, registry chain, supplemental.py, typed contract, Portal untouched.

## Provenance
```text
RECOVERY_MAIN_SHA: 7567910014b066f599154855ba12def81e1b9d3e (Architect commit)
SOURCE_SHA: 164b29760c1ef8227de4230083ae9a11d5598e92
Python: 3.11.15
followup.py:      blob 3649df1332dfc847369598fad2d7f6f7dd10a722  sha256 b64a047c9149545b2adb5135a7a1087656d1d0009b5f66faf0a0ae8dbe065bf0
followup_test.py: blob f0055e7b0db9c7ef8853da0caa876f4188c6d488  sha256 97dc92c587378cfa2a529372ee03d8975b170cbfa89138c32fc785822ddd8e42
```

## R1 — per-page projection before continuation (done)
- `_list_pages` now receives the pure projector; decode/envelope/item shape validated and each
  item TYPED-projected + strict-serialized (allow_nan=False) before it becomes accepted state or
  any continuation is issued.
- Bounded PROJECTED accumulator (cap 500), not a raw accumulator.
- Exactly ONE journal entry per attempted request (repeated token updates the same entry, never a
  second). Entry carries page/limit/path/continue-present/start/end/actual-returncode/cause/received/validated.
  `received` = raw page count; `validated` = successful typed projections for that page; `emitted` is
  implied by output length.
- Projector/shape/nonfinite error → PARSE_ERROR, unknown semantic → UNSUPPORTED; complete=false,
  empty output, no later request. Independent reads continue (len(rows)==9).
- Terminal attempt timeout/OSError → aggregate exit=null + terminal journal returncode=null;
  previous successful 0 remains only in its own page entry. Transport failure after valid pages →
  PARTIAL with the validated prefix retained.

## R3 — duplicate CRD version names (done)
- `versions[]` names tracked in a `seen_names` set across ALL entries (incl. non-v1alpha2); any
  duplicate → PARSE_ERROR, empty F-CS output, zero F-CNP calls.

## R4 — matrix + supplied fixture (done)
- Integrated the reviewer's behavioral regressions into `followup_test.py`:
  `TestRemainingContract` (projector-failure-stops-continuation, projector-journal-not-success,
  unsupported-stops-continuation, unknown-later-returncode-null, one-journal-per-repeated-token,
  duplicate-nonselected-versions) — all over the five list types.
- `TestFiveListMatrix` parameterizes empty/one-page/overlong-201/501-over-cap/wrong-list-kind/
  rv-swap/first-page-forbidden-notserved-connection across all five lists.
- `test_real_archived_identity_mapping` loads `derived-i1-fixture.json` (provenance: commit
  832591b, path evidence/P8/20261027T140000Z-p8c-rv02-phase2-live/result/supplemental.jsonl, blob
  7c6151b49…, SHA256 02e872e7…, record I1) and asserts exact projection equality. The prior
  POD/POD_CFG/POD_DIGEST test is renamed `test_three_synthetic_pod_identity_formats` and labelled
  SYNTHETIC. Fixed `objects()` to emit distinct names (`test_two_pages_201_complete` now 201 distinct).
- Fixed the ordinary resource leak in the test harness (context manager for the JSONL read).

## Results
```text
reviewer regression_test.py: 7/7 PASS (supplied harness)
followup_test.py: 95/95 PASS
supplemental_test.py: 36/36 PASS (unchanged)
```

## Status
```text
FOLLOWUP_SOURCE: REVIEW_READY
OFFLINE_TESTS: 95/95 (followup) + 36/36 (supplemental) + 7/7 (reviewer regression)
IDENTITY_CHAIN / S1 / FU-01 / FU-07 / R2: ACCEPTED / NOT_REOPENED
PHASE2_NEW_RUN_APPROVED: NO
NETPOL_APPROVED_FOR_APPLY: NO
P8C: NOT_FINAL_ACCEPTED · P8D–P8G/P9: NOT_AUTHORIZED
```
STOP. No script transmitted; no live run; historical evidence unmodified.
