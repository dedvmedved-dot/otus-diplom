# TASK-P7C-B1-LAB result

TASK: TASK-P7C-B1-LAB
BASELINE SHA: 4e02f7b948519b2f87e9c7fe2dd57c2952488a70
NEW SHA: EXTERNAL_POST_COMMIT_VALUE — VERIFY BY CONNECTOR
RUN_ID: 20260914T211447Z

RUNTIME MUTATION: ISOLATED_THROWAWAY_ONLY

CONTROL:
  normal create diskful: 2 (node-01, node-02)
  normal create UpToDate: 1 (node-02 stayed Inconsistent)

RESTORE:
  seed nodes: NOT REACHED
  seed diskful: n/a
  seed UpToDate: n/a

AUTOPLACE:
  requested total: 2
  existing diskful: n/a
  requested additional: n/a
  result: NOT REACHED
  blocking constraint: NOT_EXPOSED_BY_SERVER

ORDERING:
  second diskful created: NOT REACHED
  second diskful UpToDate: NO (control: node-02 Inconsistent)
  TieBreaker timing: control only (node-03 tie-breaker on auto-place 2)
  AutoQuorum timing: control only (off -> majority)
  safe 2-replica state reachable: NOT_PROVEN

ROOT CAUSE:
  classification: SERVER_DOES_NOT_EXPOSE_ENOUGH_DETAIL
  statement: The throwaway snapshot never deployed (snapshot suspend IO + node-02
    Inconsistent + quorum majority -> snapshot/initial-sync deadlock), so the
    single-node restore seed and the autoplace constraint could not be reproduced.

RECOMMENDATION:
  escalate to LINBIT/Piraeus upstream with the reproducible minimal case
  (snapshot create on a 2-diskful + tie-breaker + quorum=majority resource with an
  Inconsistent peer does not deploy the snapshot).

CSI_CHANGE_REQUIRED: MAYBE (blocked by upstream clarity)
RETRY_B1_READY: NO

CLEANUP:
  throwaway residue: 0
  global config changed: NO
  LINSTOR healthy: YES
  DRBD healthy: YES

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
