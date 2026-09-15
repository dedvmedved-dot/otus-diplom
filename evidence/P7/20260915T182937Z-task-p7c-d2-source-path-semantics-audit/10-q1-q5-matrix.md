# Q1-Q5 matrix

Q1 ANSWER (Aux/piraeus.io/configured-interfaces):
  Piraeus Operator internal bookkeeping of which LINSTOR NetInterfaces it owns
  (created from satellite Pod IPs). Source: internal/controller/linstorsatellite_controller.go
  v2.10.6 lines ~412-455: iterates Pod.Status.PodIPs, names default-ipv4 (IPv4) /
  default-ipv6 (IPv6), appends NetInterface{Name, Address=podIP, SatellitePort},
  then CreateOrUpdateNode(NetInterfaces: netIfs). It is NOT a DRBD path selector.
  drbd141 missing from this list does NOT cause DRBD to ignore drbd141 (the DRBD
  endpoint is selected in ConfFileBuilder from ResourceConnection/NodeConnection
  Paths, independent of configured-interfaces).

Q2 ANSWER (why node-01/node-03 use VLAN140):
  ConfFileBuilder (satellite) resolves the DRBD endpoint path in priority order;
  on node-01/node-03 satellites the NodeConnection Paths namespace is absent in
  effective state -> paths == null -> fallback getPreferredNetIf -> PrefNic null
  -> default-ipv4 (172.30.140.x). node-02 satellite has Paths/drbd141 present ->
  uses drbd141 (172.30.141.x). Asymmetry = stale/partial NodeConnection state on
  node-01/node-03 satellites.

Q3 ANSWER (exact endpoint control / priority):
  linstor-server v1.33.2 satellite/.../drbd/resfiles/ConfFileBuilder.java:
    1. ResourceConnection Paths (NAMESPC_CONNECTION_PATHS)  (line ~370)
    2. NodeConnection Paths (NAMESPC_CONNECTION_PATHS)      (line ~436)
    3. getPreferredNetIf -> KEY_STOR_POOL_PREF_NIC (PrefNic) (line ~788-830)
    4. default net interface (DEFAULT_NET_INTERFACE_NAME = default-ipv4) (line ~847)
  NetInterface resolved via node.getNetInterface(new NetInterfaceName(nicName)).
  Port: localPort/peerPort from resource connection (default 7000).

Q4 ANSWER (LinstorNodeConnection state classification):
  STALE_ON_SATELLITES.
  Controller API: Paths/drbd141/* = drbd141 present, Configured=True (correct).
  Satellite effective state: node-02 has Paths; node-01/node-03 do not (fallback
  default-ipv4). So controller correct, satellites partially stale.

Q5 ANSWER (minimal supported fix):
  Re-push NodeConnection Paths to the stale satellites via a supported
  controller-side operation. Because Piraeus reconcile is a no-op when
  actual == desired (linstornodeconnection_controller.go: MakePropertiesModification
  -> mod == nil -> no SetNodeConnection), a same-value re-push does not happen
  automatically. The minimal supported fix is to force the controller to re-send
  the node-connection to satellites (targeted satellite state refresh / re-push),
  NOT a CR field change and NOT PrefNic.

ROOT_CAUSE_BOUNDARY:
  NodeConnection (correct, controller) -> satellite effective state (partial/stale)
  -> ConfFileBuilder fallback to default-ipv4.

MOST_LIKELY_EXACT_SUBLAYER:
  Controller -> Satellite NodeConnection property propagation / FullSync (the
  Paths/drbd141 namespace is not reliably present in node-01/node-03 satellite
  state at .res generation), matching LINSTOR v1.33.2/v1.33.3 satellite
  merge/FullSync fix notes.

CONFIDENCE: HIGH (ConfFileBuilder fallback path is source-proven; the exact
  propagation trigger for the asymmetry is inferred from changelog + runtime
  evidence, so the precise trigger is MEDIUM).
