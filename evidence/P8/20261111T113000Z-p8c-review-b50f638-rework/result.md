# P8C — source rework for review b50f638 — result

FINAL_SOURCE_SHA=7adcb29135c0e3bec7cf16c177e028dd91d1d440
BASE_REVIEW_SHA=b50f638a785af436ac02c987dddbfce3be44fe63 (review of 7235e71 / evidence 73a5c28)
FAST_FORWARD=YES (b50f638..7adcb29, no force/rebase/amend)

## Verdict
SOURCE_WORK=COMPLETE (full b50f638 contract: R1 + R4; R2/R3 already accepted)
SOURCE_ACCEPTANCE=AWAITING_ARCHITECT (independent re-check on 7adcb29)
CI_RELEASE / LIVE_READINESS / PRODUCTION / WORKFLOW_PUBLICATION_DISPATCH = NOT_EXECUTED
P8C=NOT_FINAL_ACCEPTED; P8D–P8G / P9 = NOT_AUTHORIZED

## Closure matrix

### R1 one permit -> bounded operation -> consume-all -> terminal outcome
- default_http_get reads via read1 (single recv) and re-arms the underlying socket inactivity
  timeout to the remaining deadline, so the absolute deadline is enforced DURING a slow trickle
  (real http.client.HTTPResponse over an AF_UNIX socketpair, no IP network).
  -> TransportBoundaries.test_http_absolute_deadline_during_trickle_read (PASS).
- _remaining_wal_seconds subtracts the in-flight elapsed of the current sample (_WAL_SAMPLE_START),
  so a later WAL read is bounded by the already-consumed time.
  -> TransportBoundaries.test_wal_remaining_decreases_inside_sample (PASS).
- partial consumption on every error path is charged durably to BOTH overall and WAL subset via
  _charge_partial; an overrun in one counter never skips the others; run_kubectl_raw charges the WAL
  subset only while a WAL sample is active (_WAL_ACTIVE).
  -> TransportBoundaries.test_kubectl_partial_error_counts_wal_subset,
     test_overall_overrun_does_not_skip_wal_consumption (PASS).
- the WAL slot wait is a first-class permit bounded by min(overall, WAL) remaining time, so an
  exhausted WAL budget stops the next wait/slot.
  -> TransportBoundaries.test_window_wait_cannot_outspend_wal_remaining (PASS).

### R4 executor exception still reaches cleanup
- _run_job_steps normalizes subprocess.TimeoutExpired (and any other executor exception) into a
  failed outcome: subsequent protected steps are skipped, remaining if:always() cleanup still runs,
  and the route cannot PASS (value-free reason preserved).
  -> RouteMatrix.test_timeout_exception_still_reaches_cleanup (PASS).
  (seed REUSE/STOP full routing + readiness/build/proof failure matrix already PASS and are kept.)

## Offline suite (single launcher, source SHA 7adcb29)
23 readiness + 25 residual-working + 3 qualification + 4 release + 7 release-negative
+ 5 route E2E + 28 regression + 14 scheduler-authority + 15 contract-authority
+ 34 completion-authority + 20 residual-contract + 17 remaining-contract (active working copy)
+ 12 residual-contract (c98fea1) + 7 final-contract (935feb3) + 12 remaining-execution (a5e58bd)
+ 8 execution-boundaries (b50f638) = 234 methods, plus qualification CLI (qualified:true),
offline pin verification (10/10), bash -n and py_compile.

Result: SUITE RESULT: PASS (launcher exit 0). The 8 b50f638 execution-boundary controls all PASS
(were 2 PASS / 6 failures on 7235e71); the prior 12 (a5e58bd), 7 (935feb3), 12 (c98fea1),
17 (e60d1db, active) controls remain PASS.

## External prerequisites (NOT_EXECUTED; future execution gate)
Real clock evidence, CI runtime, private GHCR visibility, cosign/syft/trivy crypto execution,
live E2E S0->S4, workflow publication/dispatch, production apply/migration.

Evidence: raw-transcript.txt, secret-scan.txt (no matches), source-manifest.txt.
