# P8C RV-02 — gaps (reconciled, LI-01..03 corrected)

Base evidence: `evidence/P8/20261026T173244Z-p8c-rv02-live-inventory/inventory.jsonl`.

1. BAR-5432 — **PARTIAL DESIGN / UNKNOWN LIVE** (legacy ID).
   R1/R2/R3 observe the plugin control Service TCP9090 and its endpoint.
   Versioned Barman design distinguishes this control service from per-instance
   backup/WAL sidecars; see supplemental-design.md §4. It does not establish
   controller→DB5432 traffic. S1/S2 can provide projected sidecar/controller identity,
   not prove directed traffic, Pod-local IPC or live S3 route/port.
   R9 backup/archiving conditions describe the base collection time only.

2. API-6443 — **PARTIAL**. `default/kubernetes` 10.96.0.1:443→6443 (R2) + EndpointSlice
   addresses 172.30.140.101/102/103:6443 ready=true (R3). UNKNOWN: Calico DNAT /
   enforcement point. (Addresses already collected — no re-collect.)

3. MON-9187 — **NOT FOUND (surveyed sources)**. monitoring.coreos.com not served
   (R11-13); no Prometheus/Grafana pod; only metrics-server (R1,R2). CNPG 9187 exposed,
   no scraper. Not proven-absent cluster-wide.

4. DNS-53 — **RESOLVED**. kube-dns 10.96.0.10:53 UDP+TCP; eps 10.244.254.65/.66 ready (R2,R3).

5. S3-443 — **UNKNOWN (live)**. Source (objectstore-portal-db.yaml) defines
   `spec.configuration.endpointURL = https://s3-backup.demo-pak.test` + destinationPath
   `s3://portal-postgres-backup/` + secret refs. Base collector read `spec.data` (wrong
   path) → R10 nulls are NOT_COLLECTED_AT_CORRECT_PATH. Live value requires supplemental
   `spec.configuration` projection (P2-C1).

6. ENV-* — **RESOLVED (NOT_CREATED)**. GatewayClass `eg` (R6); Gateways [] (R7);
   EnvoyProxies [] (R8). Control-plane envoy-gateway present (R1,R2). Dataplane NOT_CREATED.

7. BASELINE — **PARTIAL→UNKNOWN**. K8S_NETWORKPOLICY_LIST=EMPTY (R5). But R14 serves
   `crd.projectcalico.org/v1` AND `policy.networking.k8s.io/v1alpha2` → Calico
   NetworkPolicy/GlobalNetworkPolicy + other policy CRDs may exist. EFFECTIVE_POLICY_UNION=UNKNOWN.
   Phase-2 C3/C4/D2 can add bounded configuration facts, but not HostEndpoint/Tier
   membership or a complete policy-engine evaluation. Namespaces catalogued (R4).

8. CNI semantics — **PARTIAL**. Calico present (`crd.projectcalico.org` R14); actual
   pod IPs 10.244.184/190/254.* ≠ node podCIDRs 10.244.0/1/2.0/24 (R15) — podCIDR is not
   an IP allowlist. Versioned configuration-source precedence is documented in supplemental-design.md §3.
   UNKNOWN: actual accepted runtime identity, effective per-node mode (iptables/eBPF/nftables),
   policy applicability/tier ordering and DNAT. I1 + C5 reads only identity and global
   defaults; node/selector overrides, env/config and HostEndpoint/Tier are not collected.

Source/documentary preparation closure does not close these live gaps or authorize
additional collection. PHASE2_LIVE_READS_APPROVED=NO; NETPOL_APPROVED_FOR_APPLY=NO.
