# TASK-P7C-D2 result

TASK: P7C-D2 READ-ONLY DRBD PATH SEMANTICS SOURCE AUDIT
MAIN_HEAD_START: b29516b384fde5d9bc08f48143d3f1866a831467

Q1: Aux/piraeus.io/configured-interfaces = Piraeus Operator bookkeeping of
    owned NetInterfaces (created from satellite Pod IPs). NOT a DRBD path
    selector; drbd141 absence there does not cause DRBD to ignore drbd141.

Q2: node-01/node-03 satellites lack NodeConnection Paths in effective state ->
    ConfFileBuilder falls back default-ipv4. node-02 has drbd141 -> VLAN141.

Q3: priority (ConfFileBuilder): ResourceConnection Paths -> NodeConnection
    Paths -> PrefNic (KEY_STOR_POOL_PREF_NIC) -> default-ipv4.

Q4: STALE_ON_SATELLITES (controller correct, node-01/node-03 satellites stale).

Q5: minimal supported fix = controller-side re-push of NodeConnection Paths
    drbd141 to node-01/node-03 satellites (same-value re-push; Piraeus no-ops
    when actual==desired). Not PrefNic, not CR field, not manual .res rewrite.

ROOT_CAUSE_BOUNDARY:
  NodeConnection (correct) -> satellite effective state (partial/stale) ->
  ConfFileBuilder fallback to default-ipv4.

MOST_LIKELY_EXACT_SUBLAYER:
  Controller -> Satellite NodeConnection property propagation / FullSync
  (Paths/drbd141 not reliably present in node-01/node-03 satellite state).

PIRAEUS_SPEC_INTERFACES_FIELD: ABSENT (LinstorSatelliteConfigurationSpec has no
  interfaces field; confirmed in api/v1/linstorsatelliteconfiguration_types.go).

LINSTOR_1_33_3_RELEVANCE: PARTIAL ("node properties not properly applied after
  FullSync" names node props; our defect is NodeConnection props, same FullSync
  propagation family).

RUNTIME_CHANGES_EXECUTED: NO
P7C-B1: BLOCKED
P7C-B2: NOT AUTHORIZED
P7C-C: NOT AUTHORIZED
P8: NOT AUTHORIZED
REMEDIATION_AUTHORIZED: NO
STATUS: READY FOR CHATGPT CONNECTOR VERIFICATION
