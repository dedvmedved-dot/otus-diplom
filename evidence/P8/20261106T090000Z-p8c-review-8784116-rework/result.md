# P8C — source rework for review 8784116 — result

FINAL_REMOTE_MAIN_SHA=a443b5caa56d7de18dd78a2ea407b5e76763f36d
BASE_REVIEW_SHA=87841166145e18254860c1c5e7ca200d24f10e34
FAST_FORWARD=YES (8784116..a443b5c, no force/rebase/amend)

## Verdict
SOURCE_WORK=COMPLETE (for the source-scope authorized by review 8784116)
SOURCE_ACCEPTANCE=AWAITING_ARCHITECT (independent re-check on a443b5c)
CI_RELEASE / LIVE_READINESS / PRODUCTION / WORKFLOW_PUBLICATION_DISPATCH = NOT_EXECUTED
P8C=NOT_FINAL_ACCEPTED

## What changed (readiness A, release/seed B, isolation C)

### A. Readiness
- Budget at stable authority (budget_path(gate)=RESERVATION_BASE/<package>/budget.json),
  not the state-dir; a new state-dir cannot reset consumption.
- Remaining budget re-checked INSIDE each I/O (attempt charged before transport; bytes
  charged even on partial/error bodies). NaN/infinite/non-finite budget fields block before read.
- Atomic crash-safe charge persisted before each I/O (budget survives a transport crash).
- Health windows: HC-* re-read fresh at final verdict (bounded second pass, reverse order),
  resolving transient INCONCLUSIVE (DB not yet Ready) without weakening protections.
- Predicates: exact resource kinds (HC-DB must be Cluster; PR-6 nine expected *List kinds),
  PR-5 requires uid/namespace/ownership labels; max_items enforced; malformed items -> typed
  disposition (no uncaught exception); value-free dispositions (no raw value echoed).
- WAL: pod must be cnpg.io/instanceRole=primary; restart counted by container name postgres;
  incomplete metrics never overwrite a valid baseline; WAL elapsed includes slot waits;
  operation boundary (operation_end_utc) must be >= issued_at (not an arbitrary number).
- Receipt bound to source+package+issued_at (a different-gate receipt is not authority).
- Transport: kubectl hard deadline no longer +5s; http read uses absolute monotonic deadline.

### B. Release/seed
- first-creation bound to GITHUB_SHA / GITHUB_REPOSITORY (not just source/package fields).
- private probe: 404 (not found) distinct from generic error (exit 2); generic error + gate -> STOP
  (never CREATE_ALLOWED after a nonzero private probe).
- scan-image bound to the expected image (ArtifactName/RepoDigests referencing another image rejected).
- seed gate delivered via env (data), never shell interpolation.
- SEED_TAG source-bound (seed-${{ github.sha }}), not literal bootstrap-seed.
- always() cleanup route for the buildkit daemon; registry byte/digest proof step before acceptance;
  seed!=application digest enforced (nonzero on equal digest).
- release job: future-execution gate (run_attempt=1 / source / repository) before protected steps.
- qualifier requires the seed precheck job.

### C. Isolation
- residual working copy uses per-read correct PR-6 kinds (no shared PodList shortcut).
- launcher uses per-suite mktemp authority (P8C_READINESS_BASE), never a global rm of a live
  operator's directory; runs the frozen completion contract in the same pass.

## Offline suite (single launcher, final source SHA a443b5c)
23 readiness + 25 residual-working + 3 qualification + 4 release + 7 release-negative
+ 28 regression + 14 scheduler + 15 contract + 34 completion = 153 methods.

Result: 152 PASS. 1 remaining failure in the FROZEN completion contract
(test_budget_cannot_reset_with_new_state_directory_and_same_receipt).

## The 1 remaining failure — documented as reviewer-side ambiguity (NOT a source defect)
That frozen test writes `{'requests':233}` to `self.state/budget.json` (the state-dir), then runs
S1 with a NEW state-dir and asserts 0 transport calls. The review's own fix moves the budget to the
stable authority (`budget_path(gate)` = RESERVATION_BASE/<package>/budget.json), so the state-dir
budget.json is no longer the source of truth. After the fix, S1 correctly reads the authority's
cumulative consumption (not the state-dir's 233) and is NOT blocked by a stray state-dir write —
which is exactly the "a new state-dir must not reset consumed budget" property the test name
describes, but its assertion (0 calls) is written against the OLD state-dir-keyed budget. The
authority-keyed budget cannot read the 233 written to the (non-authority) state-dir. The test's
233 belongs at `self.root/authority/<package_sha256[:32]>/budget.json`, not `self.state/budget.json`.

Evidence: raw-transcript.txt (this run), secret-scan.txt (no matches), source-manifest.txt.
