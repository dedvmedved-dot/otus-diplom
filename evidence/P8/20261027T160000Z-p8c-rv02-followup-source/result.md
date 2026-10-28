# P8C-R1 RV-02 — follow-up collector implementation (offline)

Date: 2026-10-27. Source-only implementation per the Architect-corrected contract
`portal/networkpolicy/followup-read-design.md` + `followup-typed-contract.json` (published 6272877).
No live execution, no handoff, no apply. Identity gate + registry chain not reopened.

## Scope
New separate module `portal/networkpolicy/followup.py` (F-D1..F-TIER) + `followup_test.py`.
Reuses accepted pure projectors and the finite S1 identity gate from supplemental.py; adds:
- CNP/HEP/Tier typed projectors (exact spec from followup-typed-contract.json).
- F-CS schema fingerprint: extract `openAPIV3Schema.properties.spec`, strip `description`,
  canonicalize (sorted keys, ensure_ascii=False, allow_nan=False), SHA256 compare to the pinned
  `770130a412fd6fab2f02d953edf35f8cc68bf4379db8307e2185937c1e699568`. Mismatch → UNSUPPORTED;
  malformed → PARSE_ERROR.
- Pagination: 5 `--raw` list reads limit=200/200/100, cap 500, 3 pages; continue token URL-encoded,
  resourceVersion tracked, repeated token / cap / next-page failure / rv swap → PARTIAL (complete=false).
- F-I1 inspects `metadata.continue`; nonempty → identity-dependent reads BLOCKED_NOT_EXECUTED.
- Dependency resolution (F-CS→F-CNP; F-D1+F-I1→F-NP/F-GNP/F-FELIX/F-HEP/F-TIER); no-overwrite output.

## Offline test result
`followup_test.py` — **37/37 PASS** (transcript attached). Coverage: identity legacy/new positives +
fail-closed negatives; discovery scope/kind/verbs + zero-call dependency blocking; F-CS hash
match/mismatch/malformed-no-raw-leak; CNP selectors/peers/protocols/port-ranges + bounds + unknown
semantic fields; HEP cluster scope + labels/ports/profiles + node/interface conditions; Tier
defaultAction preserved/invalid/absent-vs-observed; empty/one-page/201/501/continue-error/repeated-
token/rv-swap/malformed list; subprocess timeout/forbidden/not-served/connection/OS error;
no-overwrite/no-kubectl; literal argv + no raw/annotation/env/credential canary leak.
Existing supplemental.py tests remain 36/36 (no regression).

## Status
```text
RECOVERY_MAIN_SHA: 62728773ea8f235c634a63302481bf2b3390055e
FOLLOWUP_SOURCE: REVIEW_READY
OFFLINE_TESTS: 37/37 PASS (followup) + 36/36 PASS (supplemental, unchanged)
IDENTITY_CHAIN: ACCEPTED_PREVIOUSLY_NOT_RERUN
PHASE2_NEW_RUN_APPROVED: NO
NETPOL_APPROVED_FOR_APPLY: NO
P8C: NOT_FINAL_ACCEPTED · P8D–P8G/P9: NOT_AUTHORIZED
```
No script transmitted for execution; no cluster/node connection. STOP.
