# P8C RV-02 — gaps (reconciled, LI-01..03 corrected)

Base evidence: `evidence/P8/20261026T173244Z-p8c-rv02-live-inventory/inventory.jsonl`.

1. BAR-5432 — **UNKNOWN (direction)**. OBSERVED: barman-cloud pluginName
   `barman-cloud.cloudnative-pg.io`, svc 9090, eps 10.244.190.49, Pod
   barman-cloud-fddd984d8-ckw25 (R1,R2,R3). Cluster conditions archiving+backup True
   (R9). Still UNKNOWN: plugin→DB(5432) vs →S3(443) direction and sidecar path
   (R1 projects containers, not initContainers). Phase-2 (supplemental S1/S2 pod identity).

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
   Phase-2 (P2-C3/C4 + P2-D2). Namespaces catalogued (R4).

8. CNI semantics — **PARTIAL**. Calico present (`crd.projectcalico.org` R14); actual
   pod IPs 10.244.184/190/254.* ≠ node podCIDRs 10.244.0/1/2.0/24 (R15) — podCIDR is not
   an IP allowlist. UNKNOWN: Calico version/mode (iptables/eBPF), policy precedence. Phase-2 (I1 identity + C5 FelixConfiguration).
