# TASK-P7C-DRBD-PATH result

TASK: TASK-P7C-DRBD-PATH
BASELINE SHA: f2c9f332852d66a8b2504f5459f51c2d2cc80036
NEW SHA: EXTERNAL_POST_COMMIT_VALUE — VERIFY BY CONNECTOR
RUN_ID: 20260915T112652Z

RUNTIME MUTATION: TEMPORARY_REPRO_ONLY

RESOURCE:
  PVC: test-pvc
  PV: pvc-8dea8e63-50b7-42e6-91f8-2380d42906c4
  LINSTOR resource: pvc-8dea8e63-50b7-42e6-91f8-2380d42906c4

NODE INTERFACES:
  node-01 drbd141: 172.30.141.101
  node-02 drbd141: 172.30.141.102
  node-03 drbd141: 172.30.141.103

NODECONNECTION:
  pair 01-02 path: Paths/drbd141/* = drbd141
  pair 01-03 path: Paths/drbd141/* = drbd141
  pair 02-03 path: Paths/drbd141/* = drbd141
  protocol C: YES

DRBDSETUP RESOURCE PATHS (authoritative):
  01->02: 172.30.140.101:7000 -> 172.30.140.102:7000 / Connecting
  01->03: 172.30.140.101:7000 -> 172.30.140.103:7000 / Connected
  02->01: 172.30.141.102:7000 -> 172.30.141.101:7000 / Connecting
  02->03: 172.30.141.102:7000 -> 172.30.141.103:7000 / Connecting
  03->01: 172.30.140.103:7000 -> 172.30.140.101:7000 / Connected
  03->02: 172.30.140.103:7000 -> 172.30.140.102:7000 / Connecting

RESOURCE_PATHS_ALL_VLAN141: NO

RESOURCE CONNECTION:
  NodeConnection-to-resource materialization: FAIL (per-node inconsistent)
  effective path facts: node-01/03 use default-ipv4; node-02 uses drbd141

ROOT CAUSE:
  classification: LINSTOR_RESOURCE_PATH_GENERATION_ERROR
  statement: node interfaces and node-connection path drbd141 are correct and
    symmetric, but the controller-generated DRBD config materializes default-ipv4
    (VLAN140) for node-01 and node-03 while node-02 correctly gets drbd141 (VLAN141).
    This splits the DRBD mesh: node-01<->node-03 Connected on VLAN140, node-02
    Connecting/stuck (VLAN141 vs VLAN140).

FIX:
  recommended: UPSTREAM_OR_CONTROL_PLANE_REMEDIATION_REQUIRED
  blast radius: LINSTOR controller path-materialization for node-01/node-03
  rollback: re-apply canonical LinstorNodeConnection (already canonical)
  upstream-supported: NOT_PROVEN

DRBD_PATH_REMEDIATION_READY: NO
P7C_B1_RETRY_READY: NO

CLEANUP:
  throwaway residue: 0
  global config changed: NO

P7C-B1: BLOCKED
P7C-B2: NOT AUTHORIZED
P7C-C: NOT AUTHORIZED
P8: NOT AUTHORIZED

SECRETS: 0
GIT SCOPE: PASS
PUSH: PASS

HERMES RESULT: PASS (diagnostic complete)
STATUS: READY FOR CHATGPT CONNECTOR VERIFICATION

STOP
