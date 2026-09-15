# TASK-P7C-D1 result

TASK: P7C-D1 DRBD Effective-Path Forensic
MAIN_HEAD: bf8215c562e4822e0ed5d560c3e02a56f6aaa589
RESULT: PASS-A

CONTROLLER_PATH:
  node-01/node-02 = Paths/drbd141/* = drbd141 (protocol C)
  node-01/node-03 = Paths/drbd141/* = drbd141 (protocol C)
  node-02/node-03 = Paths/drbd141/* = drbd141 (protocol C)
  ResourceConnection Paths = (empty) -> inherits NodeConnection
  PrefNic = ABSENT everywhere

GENERATED_RES (local endpoint, per node):
  node-01 = 172.30.140.101 (VLAN140)
  node-02 = 172.30.141.102 (VLAN141)
  node-03 = 172.30.140.103 (VLAN140)

DRBD_RUNTIME (drbdsetup show / drbdadm dump — matches .res on every node):
  node-01 = 172.30.140.101 (VLAN140)
  node-02 = 172.30.141.102 (VLAN141)
  node-03 = 172.30.140.103 (VLAN140)

ROOT_CAUSE_LAYER:
  LINSTOR satellite effective NodeConnection propagation / config generation input.
  Controller NodeConnection = drbd141 (correct); drbd141 NetInterface exists;
  ResourceConnection does not override. Yet node-01 and node-03 satellites
  generate the .res with default-ipv4 (VLAN140), while node-02 generates
  drbd141 (VLAN141). The generated config and the applied runtime are identical
  on each node (no apply-layer divergence), so Variant B is excluded.

  Asymmetry: node-02 satellite applies the drbd141 path; node-01/node-03
  satellites fall back to default-ipv4.

  Piraeus Configured=True only proves controller-side reconcile completed; it
  does not verify the satellite effective generated .res.

AUX_CONFIGURED_INTERFACES:
  Aux/piraeus.io/configured-interfaces=["default-ipv4"] is Piraeus-internal
  bookkeeping listing which LINSTOR NetInterfaces the Operator manages. It is
  NOT the DRBD replication path selector. drbd141 may legitimately exist
  outside this list and be used by DRBD.

SUPPORTED_FIX (recommendation only, NOT executed):
  A separate Architect-authorized remediation: re-push NodeConnection path
  drbd141 to node-01/node-03 satellites via supported LINSTOR API/CLI, then
  verify generated .res switches to VLAN141. Requires pre/post evidence; no
  topology/quorum change.

  LinstorSatelliteConfiguration.spec.interfaces DOES NOT EXIST in Piraeus
  Operator 2.10.6 — do not use it as the remediation.

MINIMAL_BLAST_RADIUS:
  LINSTOR satellite effective NodeConnection state for node-01 and node-03
  (re-push path drbd141); no network/routing/quorum/TieBreaker change.

SAFETY:
  Read-only forensic. No config/runtime mutation. Nodes Ready 3/3, satellites
  Online 3/3, storage pools/quorum/network unchanged. Temporary PVC cleaned up.

P7C-B1: BLOCKED
REMEDIATION_EXECUTED: NO
