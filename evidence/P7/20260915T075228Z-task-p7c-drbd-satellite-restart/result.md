# TASK-P7C-DRBD-RESTART result

TASK: TASK-P7C-DRBD-RESTART
BASELINE SHA: bad9579f7f96f6669c7de012a87933c186066270
NEW SHA: EXTERNAL_POST_COMMIT_VALUE — VERIFY BY CONNECTOR
RUN_ID: 20260915T075228Z

RUNTIME MUTATION:
  node-01 satellite restart
  node-03 satellite restart
  temporary validation PVC

RESTART:
  node-01 old UID: b7926963-50de-4b3c-8b2b-5a13ee5cb34e
  node-01 new UID: 8c13f6d1-a2a1-4478-ad28-39aee6ce19e2
  node-01 Ready/Online: PASS

  node-03 old UID: 008e08bc-740d-4fca-a88b-442e5f5f583a
  node-03 new UID: b52a207c-e664-472e-81c5-a0db6faa6da4
  node-03 Ready/Online: PASS

  node-02 UID unchanged: YES (4f03206a-fdd8-42f0-9461-ba0d24b7c4ba)

POST:
  satellites Ready: 3/3
  LINSTOR Online: 3/3
  pair paths drbd141: 3/3 (config)

DRBD BINDING:
  node-01: 172.30.140.101:7000 (VLAN140)
  node-02: 172.30.141.102:7000 (VLAN141)
  node-03: 172.30.140.103:7000 (VLAN140)
  DRBD_VLAN141_BINDING_3_OF_3: FAIL

REPLICATION:
  diskful replicas: 2 (node-01, node-02)
  UpToDate diskful replicas: 1 (node-01 only)
  peer connections: node-01<->node-03 Connected (VLAN140); node-02 Connecting stuck
  TieBreaker: node-03
  quorum: majority
  VALID_SOURCE_2_DISKFUL_UPTODATE: NO

DATA_CHECK: NOT_USED (writer completed but replication unhealthy)
P5_STORAGE_REGRESSION: PASS (config layer; runtime binding asymmetric)

CLEANUP:
  throwaway residue: 0

DRBD_ENDPOINT_REMEDIATION: BLOCKED
P7C_B1_RETRY_READY: NO

P7C-B1: BLOCKED — RETRY NOT EXECUTED
P7C-B2: NOT AUTHORIZED
P7C-C: NOT AUTHORIZED
P8: NOT AUTHORIZED

SECRETS: 0
GIT SCOPE: PASS
PUSH: PASS

HERMES RESULT: BLOCKED
STATUS: READY FOR CHATGPT CONNECTOR VERIFICATION

STOP
