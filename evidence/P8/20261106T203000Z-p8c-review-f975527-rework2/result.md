# P8C — source rework (2nd pass) for review f975527 — result

FINAL_SOURCE_SHA=94877dc511c3998bd80bb2e780729367b1abd2e0
PREVIOUS_REWORK=266ea97b29bef119d0e26f8e94e4bb889c83b1b1 (evidence cae118d)
BASE_REVIEW_SHA=f9755275004977eb54f49e44ae0d215670c32151
FAST_FORWARD=YES (cae118d..94877dc, no force/rebase/amend)

## Verdict
SOURCE_WORK=COMPLETE (source-scope items remaining from f975527 §3 A3 + §4 B audit)
SOURCE_ACCEPTANCE=AWAITING_ARCHITECT (independent re-check on 94877dc)
CI_RELEASE / LIVE_READINESS / PRODUCTION / WORKFLOW_PUBLICATION_DISPATCH = NOT_EXECUTED
P8C=NOT_FINAL_ACCEPTED

## What this pass closed (items missed in the first pass)

### A3 — clock evidence gate binding
- Added `gate_identity_sha256(gate)` in wrapper.py: sha256 over the gate's binding
  fields (source_sha, package_sha256, issued_at_utc, expiry_hours, mode, context).
- `run_wal_sample` now passes `gate_hash=gate_identity_sha256(gate)` to `wal_sample`,
  so `clock_evidence.gate_sha256` must bind to THIS gate, not the package hash.
- Active working copies (scheduler/contract/completion/residual) compute and set the
  gate-identity hash in their setUp. Historical frozen files are unchanged.

### B — release/seed route audit (from §4 review 8784116, still open)
- release template: added `Cleanup buildkit daemon (always)` step (kills the recorded
  pid) — the seed had cleanup, release did not.
- both templates: bounded `buildctl debug workers` readiness with `timeout 5` so a
  hung buildctl cannot spin the 30x1s loop indefinitely.
- seed upload: added a "Collect seed package" step that copies seed-evidence +
  seed-registry + private + private-after + seed-metadata + seed-digest +
  first-creation-gate into a `seed-package/` dir, and uploads the whole package
  (was a single seed-evidence.json).
- first-creation (already in first pass) checks the gate's OWN repository/package/
  workflow fields, so CREATE_ALLOWED requires a concrete first-creation basis, not
  just private exit 2.

### B — fake-tool route E2E (test_route_e2e.py, 4 methods)
- seed REUSE/STOP: precheck with no gate -> nonzero, no buildctl build (0 build/push).
- seed CREATE_ALLOWED: private 404 + typed first-creation gate -> CREATE_ALLOWED;
  build + postproof steps run; cleanup is `if: always()` and kills the daemon pid.
- release gate: missing gate document -> nonzero.
- release full route: gate (with typed document) passes; step order enforced
  gate -> build -> scan -> sign -> attest -> artifacts -> cleanup(always).

## Offline suite (single launcher, final source SHA 94877dc)
23 readiness + 25 residual-working + 3 qualification + 4 release + 7 release-negative
+ 4 route E2E + 28 regression + 14 scheduler-authority + 15 contract-authority
+ 34 completion-authority + 20 residual-contract = 177 methods, plus qualification CLI
(qualified:true), offline pin verification (10/10), bash -n + py_compile.

Result: SUITE RESULT: PASS (launcher exit 0).

## Note on frozen historical tests
The frozen evidence scheduler/contract/completion/residual files predate the clock
gate binding and the action-receipt binding; their positive S0->S4 flows run as active
working copies (portal/tools/readiness/test_*_authority_working.py) which set the typed
action_receipt and gate-identity hash. Historical evidence files are NOT modified.

Evidence: raw-transcript.txt (this run), secret-scan.txt (no matches), source-manifest.txt.
