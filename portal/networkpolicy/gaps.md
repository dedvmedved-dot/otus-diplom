# P8C RV-02 — gaps (reconciled, LI-01..03 corrected)

Base evidence: `evidence/P8/20261026T173244Z-p8c-rv02-live-inventory/inventory.jsonl`.

1. BAR-5432 — **PARTIAL DESIGN / LIVE IDENTITY OBSERVED** (legacy ID).
   R1/R2/R3 observe the plugin control Service TCP9090 and its endpoint.
   Phase-2 S1/S2 live read: per-instance Barman sidecar `plugin-barman-cloud`
   (init container in each portal-db pod) + plugin controller `barman-cloud`
   (cnpg-system pod) both present. Versioned Barman design distinguishes the control
   service (9090) from per-instance sidecars; see supplemental-design.md §4. It does
   not establish controller→DB5432 traffic, Pod-local IPC or live S3 route/port
   (declared, not observed).
   R9 backup/archiving conditions describe the base collection time only.

2. API-6443 — **PARTIAL**. `default/kubernetes` 10.96.0.1:443→6443 (R2) + EndpointSlice
   addresses 172.30.140.101/102/103:6443 ready=true (R3). UNKNOWN: Calico DNAT /
   enforcement point. (Addresses already collected — no re-collect.)

3. MON-9187 — **NOT FOUND (surveyed sources)**. monitoring.coreos.com not served
   (R11-13); no Prometheus/Grafana pod; only metrics-server (R1,R2). CNPG 9187 exposed,
   no scraper. Not proven-absent cluster-wide.

4. DNS-53 — **RESOLVED**. kube-dns 10.96.0.10:53 UDP+TCP; eps 10.244.254.65/.66 ready (R2,R3).

5. S3-443 — **PARTIAL (endpoint configuration observed)**. Phase-2 C1 live read: `spec.configuration.endpointURL`
   = `https://s3-backup.demo-pak.test` (origin-only), destinationPath
   `s3://portal-postgres-backup`; secret refs `portal-barman-s3-credentials` (keys only,
   no values). Port 443 implied by https; actual traffic/backup path still UNKNOWN.
   URL path is dropped by projection; bucket suffix/prefix is NOT_COLLECTED.

6. ENV-* — **RESOLVED (NOT_CREATED)**. GatewayClass `eg` (R6); Gateways [] (R7);
   EnvoyProxies [] (R8). Control-plane envoy-gateway present (R1,R2). Dataplane NOT_CREATED.

7. BASELINE — **PARTIAL→UNKNOWN**. K8S_NETWORKPOLICY_LIST=EMPTY (R5). But R14 serves
   `crd.projectcalico.org/v1` AND `policy.networking.k8s.io/v1alpha2` → Calico
   NetworkPolicy/GlobalNetworkPolicy + other policy CRDs may exist. EFFECTIVE_POLICY_UNION=UNKNOWN.
   Phase-2 D2 observes ClusterNetworkPolicy discovery (UNSUPPORTED); C3/C4/C5
   are BLOCKED_NOT_EXECUTED. No policy object presence/absence, HostEndpoint/Tier
   membership or complete policy-engine evaluation is established. Namespaces catalogued (R4).

8. CNI semantics — **PARTIAL**. Calico present (`crd.projectcalico.org` R14); actual
   pod IPs 10.244.184/190/254.* ≠ node podCIDRs 10.244.0/1/2.0/24 (R15) — podCIDR is not
   an IP allowlist. Versioned configuration-source precedence is documented in supplemental-design.md §3.
   UNKNOWN: actual accepted runtime identity, effective per-node mode (iptables/eBPF/nftables),
   policy applicability/tier ordering and DNAT. I1 + C5 reads only identity and global
   defaults; node/selector overrides, env/config and HostEndpoint/Tier are not collected.

Source/documentary preparation closure does not close these live gaps or authorize
additional collection. PHASE2_LIVE_READS_APPROVED=NO; NETPOL_APPROVED_FOR_APPLY=NO.

## Phase-2 review 832591b

Artifact: evidence/P8/20261027T140000Z-p8c-rv02-phase2-live/result/supplemental.jsonl.
Review/task: docs/architecture/P8C_RV02_REVIEW_832591b_20261027.md.
I1 imageID sha256:6bc9fa4dc2b10ca1d4b97a1cd570036651898cea8b3c3bcbb1d55cf813e43f65
is bare and rejected by the pinned parser before digest comparison. Its relationship to
pinned f4fafd8... remains UNPROVEN; platform-child/config classification is not established.
Three matching image tags and ebpf-bootstrap names do not prove effective CNI mode.
Access-method provenance is NOT_FULLY_EVIDENCED; existing operator records may clarify
host-key authentication and non-use of previously disclosed credentials without new login.
ONE_RUN_BUDGET=CONSUMED. Only source-only follow-up task is authorized; no new cluster reads.

## Phase-3 follow-up one-run 20261101 (gate fbaa9a4)

Artifact: evidence/P8/20261101T193800Z-p8c-rv02-followup-onerun/ (followup.jsonl, 9 records, EXIT=1).

- F-D1 **OK** — `crd.projectcalico.org/v1` lists 23 Calico API resource descriptors, including a status subresource (incl. networkpolicies,
  globalnetworkpolicies, felixconfigurations, hostendpoints, tiers, networksets,
  globalnetworksets, ippools, ipamblocks, bgppeers, bgpconfigurations, blockaffinities,
  bgpfilters, caliconodestatuses, clusterinformations, ipamconfigs, ipamhandles,
  ipreservations, kubecontrollersconfigurations, staged* variants). Confirms the Calico policy
  API surface is live.
- F-I1 **PARSE_ERROR** — `get pods -n kube-system -l k8s-app=calico-node -o json` exit 0 but
  typed projection/identity parse fails (empty output) → blocks F-NP/F-GNP/F-FELIX/F-HEP/F-TIER.
  (Historical phase-2 I1 was UNSUPPORTED; this run returns PARSE_ERROR — a new disposition.)
- F-CS **UNSUPPORTED** — CNP `v1alpha2` served=true but schema SHA256 `ff433d34…` ≠ pinned
  `770130a4…` (compatible=false) → blocks F-CNP. The observed normalized spec hash matches the repository-pinned Calico v3.32.0 manifest; the old comparison pin came from a different upstream candidate. Live schema drift is NOT established.
- No effective-policy-union, per-node CNI mode or traffic/directed-flow conclusion is drawn.
  BAR-5432/API-6443/MON-9187/S3-443/ENV-* gaps unchanged. NEW_GATE_RUN_BUDGET=CONSUMED.

## Architect review 3a0afb4 — current interpretation

Review: docs/architecture/P8C_RV02_REVIEW_3a0afb4_20261101.md.
F-I1 request/parser incompatibility is reproduced offline: kubectl generic List output versus
strict API PodList/nonempty resourceVersion expectation. Exact live failing field remains
unavailable because raw stdout was suppressed; this is not evidence of a Calico change.
F-CS hash ff433d3463dfa2264a7a3ff6201baabf1ec789e98664aff3401a7ef79ae7ce5e matches
the normalized spec subtree in calico-v3.32.0.yaml, blob21ea9b4b163305ea479bc7708965104465ffc716.
Source compatibility corrections are authorized offline only. Accepted immutable identity
binding and Owner access attestations supersede older historical UNPROVEN/access paragraphs;
current live identity and policy configuration remain uncollected by this follow-up.
NEW_GATE_RUN_BUDGET=CONSUMED; PHASE2_NEW_RUN_APPROVED=NO; NETPOL_APPROVED_FOR_APPLY=NO.
