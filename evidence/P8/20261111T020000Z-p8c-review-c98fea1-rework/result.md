# P8C — source rework for review c98fea1 — result

FINAL_SOURCE_SHA=3422e31e97742dd32ad5044451eb062ee5dacf1d
BASE_REVIEW_SHA=2a38af9f8caa84268a41158efc8459e564b83fad (review of 61e4a44 / evidence c98fea1)
FAST_FORWARD=YES (2a38af9..3422e31, no force/rebase/amend)

## Verdict
SOURCE_WORK=COMPLETE (full c98fea1 contract: R1 + R2 + R3 + R4 + E)
SOURCE_ACCEPTANCE=AWAITING_ARCHITECT (independent re-check on 3422e31)
CI_RELEASE / LIVE_READINESS / PRODUCTION / WORKFLOW_PUBLICATION_DISPATCH = NOT_EXECUTED
P8C=NOT_FINAL_ACCEPTED; P8D–P8G / P9 = NOT_AUTHORIZED

## Closure matrix

### R1 accounting (reservation/consumption/failure — one mechanism)
- `_charge(..., commit=)` splits overrun semantics: bytes/seconds RECORDED on overrun
  (commit=True; a failure never becomes "nothing was consumed"); requests/wal_requests not recorded
  on overrun (commit=False; a slot is not spent twice). Request concurrency fix preserved.
  -> TransportDurability.test_consumed_bytes_are_not_lost_on_remaining_cap_error,
     test_wal_seconds_cap_overrun_is_not_silently_dropped (PASS).
- `_io_call` wraps every kubectl/HTTP transport call and charges actual elapsed time to overall
  seconds (I/O time no longer lost alongside sleeps).
  -> RouteControls.test_actual_transport_elapsed_persists_in_overall_budget (PASS).
- WAL metadata/HTTP reads bounded by min(sample/window/WAL/overall) remaining body.
  -> RouteControls.test_wal_remaining_byte_limits_first_metadata_read (PASS).

### R2 health W/I/N (one table drives execution + total budget)
- N = total observations INCLUDING first GET and final freshness re-read (retries = N-2).
  DB/ARCH(shared)/OP/Portal = W60/I10/N6; DNS = W30/I5/N6; Gateway = W120/I10/N12 (<=12 GETs).
  Absolute window end, failure precedence, per-check freshness age (<=30s, Gateway <=60s).
  -> RouteControls.test_fifth_operator_observation_within_accepted_window,
     test_gateway_observations_stay_within_accepted_n12, test_positive_s0_control (PASS).

### R3 release-gate binding
- actual run_attempt must be 1 (argv compared, not ignored); workflow_sha must equal runtime
  GITHUB_WORKFLOW_SHA (missing binding is NOT authorization); issued_at must be already elapsed
  (no +300s future grace). Same for first-creation.
  -> ReleaseGateControls.test_bound_gate_positive_control, test_actual_attempt_two_rejected_...,
     test_different_runtime_workflow_sha_rejected, test_future_gate_is_not_active_yet (PASS).

### R4 route E2E (execution + result checking, not name-only)
- Full seed CREATE_ALLOWED and release routes executed; only network modes (private/registry) and
  external binaries faked. Gate/digest/predicate/verified validators run for real.
  GITHUB_ENV/GITHUB_OUTPUT/if/always-cleanup emulated; every mandatory step's exit asserted; a
  digest mismatch is caught by the real `verified` validator.
  -> test_route_e2e.py (5 methods) PASS; positive route => payloadBinding PASS; negative => nonzero.

### E cached image proof
- verify_offline image path binds cached observed manifest_sha256 to the lock digest.
  -> test_offline_image_evidence_requires_observed_digest_binding (PASS).

## Offline suite (single launcher, source SHA 3422e31)
23 readiness + 25 residual-working + 3 qualification + 4 release + 7 release-negative
+ 5 route E2E + 28 regression + 14 scheduler-authority + 15 contract-authority
+ 34 completion-authority + 20 residual-contract + 17 remaining-contract (e60d1db)
+ 12 residual-contract (c98fea1) = 206 methods, plus qualification CLI (qualified:true) and
offline pin verification (10/10) + bash -n + py_compile.

Result: SUITE RESULT: PASS (launcher exit 0). The 12 c98fea1 residual controls all PASS
(were 2 PASS / 10 failures on 61e4a44).

## External prerequisites (NOT_EXECUTED; future execution gate)
Real clock evidence, CI runtime, private GHCR visibility, cosign/syft/trivy crypto execution,
live E2E S0->S4, workflow publication/dispatch, production apply/migration.

Evidence: raw-transcript.txt, secret-scan.txt (no matches), source-manifest.txt.
