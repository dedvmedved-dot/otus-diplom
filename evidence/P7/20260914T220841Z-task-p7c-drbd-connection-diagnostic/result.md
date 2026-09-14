# TASK-P7C-DRBD-CONN result

TASK: TASK-P7C-DRBD-CONN
BASELINE SHA: abefd66c574d9e7e62d07faab8aa43f6d2680a25
NEW SHA: EXTERNAL_POST_COMMIT_VALUE — VERIFY BY CONNECTOR
RUN_ID: 20260914T220841Z

RUNTIME MUTATION: TEMPORARY_REPRO_ONLY

P5C2 REFERENCE:
  satellite hostNetwork expected: true
  VLAN141 endpoints expected: 172.30.141.101/102/103

CURRENT:
  VLAN141 host state: MATCH
  satellite hostNetwork 3/3: YES
  satellite VLAN visibility 3/3: YES
  LINSTOR endpoint selection: FAIL (node-01/node-03 bound VLAN140)
  L3 reachability: PASS
  DRBD TCP reachability: PASS (VLAN141) but listener on wrong IP for node-01/03
  MTU: PASS (1500)
  rp_filter anomaly: NO (rp_filter=1, symmetric)
  firewall block: NOT_PROVEN

DRBD:
  node-02 connection state: Connecting (stuck)
  node-02 peer disk state: Inconsistent
  kernel error: NONE (clean attach, connecting)
  satellite error: NONE (no EADDRNOTAVAIL/refused)

REPRODUCTION:
  reproduced: YES
  packet path: DRBD listener asymmetry (node-01/03 VLAN140 vs node-02 VLAN141)

ROOT CAUSE:
  classification: LINSTOR_ENDPOINT_SELECTION_ERROR
  statement: node-01 and node-03 satellites bind DRBD to VLAN140 (default-ipv4,
    172.30.140.x) while node-02 binds VLAN141 (drbd141, 172.30.141.x); asymmetric
    endpoints break the DRBD mesh -> node-02 Inconsistent/Connecting.

FIX:
  recommended: reconcile node-01/node-03 satellites to bind DRBD on drbd141 (VLAN141)
  blast radius: LINSTOR satellite DRBD interface binding (node-01, node-03)
  rollback: re-point DRBD interface (config-only, reversible)
  P5C2 architecture preserved: YES

DRBD_REMEDIATION_READY: YES
RETRY_B1_READY: NO

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

HERMES RESULT: PASS
STATUS: READY FOR CHATGPT CONNECTOR VERIFICATION

STOP
