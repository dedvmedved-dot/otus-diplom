# P8C — source rework for review a5e58bd — result

FINAL_SOURCE_SHA=7235e713ad22ab530bbd67c16c1b33a587506964
BASE_REVIEW_SHA=4cff2e709d50f05bfb182fae3cc950cddd3f818b (review of 225004d / evidence a5e58bd)
FAST_FORWARD=YES (4cff2e7..7235e71, no force/rebase/amend)

## Verdict
SOURCE_WORK=COMPLETE (full a5e58bd contract: R1 + R2 + R3 + R4)
SOURCE_ACCEPTANCE=AWAITING_ARCHITECT (independent re-check on 7235e71)
CI_RELEASE / LIVE_READINESS / PRODUCTION / WORKFLOW_PUBLICATION_DISPATCH = NOT_EXECUTED
P8C=NOT_FINAL_ACCEPTED; P8D–P8G / P9 = NOT_AUTHORIZED

## Closure matrix

### R1 unified permit/consume/terminal (all transports + all outcomes)
- remaining-capacity reads the CURRENT authority (recorded overruns included), not stale
  process-local base; run_read + both WAL metadata/HTTP reads bound timeout by
  min(overall seconds, WAL seconds, sample deadline) before the I/O.
  -> Budgets.test_wal_timeout_respects_overall_remaining, test_wal_timeout_respects_wal_remaining,
     test_read_timeout_uses_current_authority_remaining (PASS).
- default_http_get counts a late chunk and charges the partial body (overall + WAL subset) on any
  deadline/transport error.
  -> Budgets.test_late_http_chunk_still_counts_bytes,
     test_http_partial_charged_to_wal_subset (PASS).

### R2 window on every path
- window checked before sleep, after sleep, and at GET completion; transport timeout bounded by the
  remaining window; a late healthy response cannot close a check that never passed in-window.
  -> HealthWindow.test_retry_response_after_dns_deadline_not_pass, test_positive_s0 (PASS).

### R3 mandatory seed binding
- first-creation requires GITHUB_RUN_ATTEMPT=1 AND typed integer attempt=1 (missing/null/bool/2
  rejected; no permissive bypass). Historical positive fixture frozen; active working copy
  (test_remaining_contract_working.py) binds attempt=1 + GITHUB_RUN_ATTEMPT=1.
  -> SeedBinding.test_positive_bound_attempt_one, test_missing_runtime_binding_rejected,
     test_missing_document_binding_rejected, test_null_document_binding_rejected (PASS).

### R4 cleanup outcome
- _run_job_steps records ANY nonzero (including if:always() cleanup) as a route failure; a nonzero
  non-always step still skips subsequent protected steps while cleanup runs.
  -> CleanupOutcome.test_cleanup_nonzero_cannot_report_route_pass (PASS).

## Offline suite (single launcher, source SHA 7235e71)
23 readiness + 25 residual-working + 3 qualification + 4 release + 7 release-negative
+ 5 route E2E + 28 regression + 14 scheduler-authority + 15 contract-authority
+ 34 completion-authority + 20 residual-contract + 17 remaining-contract (active working copy)
+ 12 residual-contract (c98fea1) + 7 final-contract (935feb3) + 12 remaining-execution (a5e58bd)
= 226 methods, plus qualification CLI (qualified:true), offline pin verification (10/10),
bash -n and py_compile.

Result: SUITE RESULT: PASS (launcher exit 0). The 12 a5e58bd remaining-execution controls all PASS
(were 2 PASS / 10 failures on 225004d); the prior 7 (935feb3), 12 (c98fea1), 17 (e60d1db, active)
controls remain PASS.

## External prerequisites (NOT_EXECUTED; future execution gate)
Real clock evidence, CI runtime, private GHCR visibility, cosign/syft/trivy crypto execution,
live E2E S0->S4, workflow publication/dispatch, production apply/migration.

Evidence: raw-transcript.txt, secret-scan.txt (no matches), source-manifest.txt.
