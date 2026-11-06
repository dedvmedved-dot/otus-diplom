# P8C — source rework for review f975527 — result

FINAL_SOURCE_SHA=266ea97b29bef119d0e26f8e94e4bb889c83b1b1
BASE_REVIEW_SHA=f9755275004977eb54f49e44ae0d215670c32151
FAST_FORWARD=YES (f975527..266ea97, no force/rebase/amend)

## Verdict
SOURCE_WORK=COMPLETE (for the source-scope authorized by review f975527)
SOURCE_ACCEPTANCE=AWAITING_ARCHITECT (independent re-check on 266ea97)
CI_RELEASE / LIVE_READINESS / PRODUCTION / WORKFLOW_PUBLICATION_DISPATCH = NOT_EXECUTED
P8C=NOT_FINAL_ACCEPTED

## What changed (A1/A2/A3/B — the 18 remaining assertions of review 8784116/f975527)

### A1 budgets/transport
- remaining body/time enforced INSIDE each I/O (attempt charged before the transport call;
  bytes charged even on partial/timeout bodies; EOF after deadline rejected via absolute deadline).
- overall elapsed (seconds) tracked during execution (sleeps counted), limited by remaining budget.

### A2 health scheduler
- failure precedence: a first FAIL is never erased by a later sweep.
- bounded retry interval (10s, limited by remaining time budget) for transient INCONCLUSIVE.
- freshness gate at verdict: every mandatory health observation age <= 30s, else FAIL.
- PR-5 exact namespace (envoy-gateway-system); PR-6 typed items + max_items per list;
  HC-OP nested malformed -> typed verdict (no uncaught exception).

### A3 WAL identity + operation boundary
- instanceRole=primary checked on BOTH bracket sides (before + after pod).
- baseline stores pod UID + observed time, re-checked on read (cross-sample UID change invalidates).
- operation_end_utc must bind a verified action_receipt (source_sha+package_sha256+operation_end_utc);
  an arbitrary number is not authority.

### B release/seed
- release Future execution gate requires a typed gate document (missing -> nonzero).
- first-creation checks the gate's OWN repository/package/workflow fields (not only env).
- scan-image binds exact image@digest (substring IMAGE is insufficient).
- seed Record step tolerates absent APP_IMAGE_DIGEST (first bootstrap; only enforces distinction
  when an application digest is present).

### Active working copies (single-pass correction directive)
- portal/tools/readiness/test_contract_authority_working.py (15)
- portal/tools/readiness/test_completion_authority_working.py (34)
- portal/tools/readiness/test_residual_contract_working.py (20)
These add the typed action_receipt to the positive S0->S4 flows and adopt the exhausted-authority
budget fixture (write_budget). Historical frozen evidence files are NOT modified.
- launcher uses offline pin verification (verify-pins.py --offline: cached bytes + prior evidence,
  no network). TestDigestPredicate.test_digest_mode_accepts_valid now uses a real file (exit 0 on
  valid, nonzero on invalid).

## Offline suite (single launcher, final source SHA 266ea97)
23 readiness + 25 residual-working + 3 qualification + 4 release + 7 release-negative
+ 28 regression + 14 scheduler + 15 contract-authority + 34 completion-authority
+ 20 residual-contract = 173 methods, plus qualification CLI (qualified:true), offline pin
verification (10/10), bash -n + py_compile.

Result: SUITE RESULT: PASS (launcher exit 0).

## Note on frozen historical tests
The frozen evidence completion_contract_test.py / residual_contract_test.py / contract_test.py
contain positive S0->S4 flows that predate the action-receipt binding; running them directly now
fails only those positive flows (op_end=now[0] without action_receipt). The active working copies
supply the typed action_receipt, per the single-pass correction directive (historical files unchanged).

Evidence: raw-transcript.txt (this run), secret-scan.txt (no matches), source-manifest.txt.
