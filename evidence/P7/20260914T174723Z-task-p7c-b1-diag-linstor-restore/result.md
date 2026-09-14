# TASK-P7C-B1-DIAG result

TASK: TASK-P7C-B1-DIAG
BASELINE SHA: 1c3e26ef222149e9087fd798092ede0b5b7c706f
NEW SHA: EXTERNAL_POST_COMMIT_VALUE — VERIFY BY CONNECTOR
RUN_ID: 20260914T174723Z

RUNTIME MUTATION: 0

OBSERVED FAILURE:
  CreateVolume-from-snapshot: FAIL
  actual diskful replicas: 1
  tie breaker: node-03 (auto-added)
  AutoQuorum: off -> majority
  primary error: Need access to UpToDate data
  exitcode: 17

PLACEMENT:
  StorageClass placementCount: 2
  ResourceGroup replica/select filter: DfltRscGrp PlaceCount 2; piraeus-r2 no props
  normal CreateVolume behavior: 2 diskful + tie-breaker (WORKS)
  snapshot restore behavior: 1 diskful seed + tie-breaker
  replica-count source: LINSTOR CSI reconcileSnapshotResources single-node seed

QUORUM:
  AutoQuorum trigger: auto-add-quorum-tiebreaker=True on 1-diskful resource
  quorum required: 2 (majority)
  UpToDate replicas available: 1
  promotion failure mechanism: majority quorum needs 2 UpToDate, only 1 present

ROOT CAUSE:
  classification: INTERACTION_BETWEEN_PLACEMENT_AND_AUTOQUORUM (contributing LINSTOR_CSI_BUG)
  statement: VolFromSnap restores snapshot onto one node, autoplace does not produce
    2nd UpToDate diskful before DRBD AutoQuorum majority -> primary fail.

FIX:
  recommended minimal fix: NONE_PROVEN_SAFE_YET (post-restore autoplace candidate, NOT_PROVEN)
  blast radius: n/a
  preserves placementCount=2: n/a (option C would)
  preserves quorum safety: n/a
  upstream-supported: NOT_PROVEN
  rollback: n/a

RETRY_B1_READY: NO

P7C-B1: BLOCKED
P7C-B2: NOT AUTHORIZED
P7C-C: NOT AUTHORIZED
P8: NOT AUTHORIZED

SECRETS: 0
GIT SCOPE: PASS
PUSH: PASS

HERMES RESULT: PASS
STATUS: READY FOR CHATGPT CONNECTOR VERIFICATION

STOP
