# P8C — source rework for review 935feb3 — result

FINAL_SOURCE_SHA=225004d12abe5ed2796c4bcd5e57c7ba945ded52
BASE_REVIEW_SHA=e196f0d57b228217f0c3a68d284dc99d4e004d26 (review of 3422e31 / evidence 935feb3)
FAST_FORWARD=YES (e196f0d..225004d, no force/rebase/amend)

## Verdict
SOURCE_WORK=COMPLETE (full 935feb3 contract: R1 + R2 + R3 + R4)
SOURCE_ACCEPTANCE=AWAITING_ARCHITECT (independent re-check on 225004d)
CI_RELEASE / LIVE_READINESS / PRODUCTION / WORKFLOW_PUBLICATION_DISPATCH = NOT_EXECUTED
P8C=NOT_FINAL_ACCEPTED; P8D–P8G / P9 = NOT_AUTHORIZED

## Closure matrix

### R1 terminal accounting / deadlines / partial consumption
- `_overall_exhausted`/`_wal_exhausted` consult the on-disk authority (recorded overruns count):
  after the overall time budget is spent, no further I/O is issued (terminal stop).
  -> BudgetTermination.test_no_second_io_after_overall_time_exhaustion (PASS).
- `run_read`/`run_wal_sample` bound each transport call's `timeout` up-front by
  min(timeout, remaining enclosing deadline).
  -> BudgetTermination.test_timeout_argument_is_bounded_by_remaining_overall (PASS).
- `default_http_get` charges any partial body already received before a deadline/transport error.
  -> BudgetTermination.test_http_partial_body_is_charged_on_read_error (PASS).

### R2 health window (multiple simultaneous transient checks)
- window end anchored to each check's FIRST observation (not a shared clock); final freshness
  re-read cannot turn INCONCLUSIVE into PASS after the window expired.
  -> HealthWindows.test_late_dns_cannot_turn_expired_window_into_pass,
     test_positive_s0_control (PASS).

### R3 seed single-attempt
- first-creation rejects a bound `GITHUB_RUN_ATTEMPT != 1` or a gate `attempt != 1` (a real second
  seed run is rejected); absent binding stays backward-compatible with the prior positive control.
  -> SeedGate.test_actual_second_seed_run_rejected (PASS).

### R4 negative routing (cleanup after failure)
- one shared route runner handles positive and negative: a nonzero non-always step marks failure,
  skips subsequent protected steps, but still executes `if: always()` cleanup before the test fails.
  -> NegativeRoute.test_release_build_failure_executes_always_cleanup (PASS).

## Offline suite (single launcher, source SHA 225004d)
23 readiness + 25 residual-working + 3 qualification + 4 release + 7 release-negative
+ 5 route E2E + 28 regression + 14 scheduler-authority + 15 contract-authority
+ 34 completion-authority + 20 residual-contract + 17 remaining-contract (e60d1db)
+ 12 residual-contract (c98fea1) + 7 final-contract (935feb3) = 214 methods, plus qualification
CLI (qualified:true), offline pin verification (10/10), bash -n and py_compile.

Result: SUITE RESULT: PASS (launcher exit 0). The 7 final 935feb3 controls all PASS (were
1 PASS / 6 failures on 3422e31); the prior 12 c98fea1 controls and 17 e60d1db controls remain PASS.

## External prerequisites (NOT_EXECUTED; future execution gate)
Real clock evidence, CI runtime, private GHCR visibility, cosign/syft/trivy crypto execution,
live E2E S0->S4, workflow publication/dispatch, production apply/migration.

Evidence: raw-transcript.txt, secret-scan.txt (no matches), source-manifest.txt.
