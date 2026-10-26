# P8C RV-02 — gaps (post live-inventory)

Base evidence: `evidence/P8/20261026T173244Z-p8c-rv02-live-inventory/inventory.jsonl` (15 records).
Status after reconciliation: RESOLVED / PARTIAL / UNKNOWN / NOT_FOUND.

1. BAR-5432 — **UNKNOWN**. Observed: barman-cloud pod+svc in cnpg-system TCP 9090
   (R1,R2). Cluster `portal-db` conditions ContinuousArchiving + LastBackupSucceeded
   True (R9) → backup active. But the plugin→DB(5432) direction and the actual S3
   endpoint are NOT captured: the base projection extracts only
   `spec.backup.barmanObjectStore.name` (null, R9) and ObjectStore `spec.data.*`
   (all null, R10). The inline backup endpoint/s3Credentials reference lives in the
   Cluster `spec.backup.barmanObjectStore` body, which is not projected. Phase-2.

2. API-6443 — **PARTIAL**. `default/kubernetes` Service 10.96.0.1:443→targetPort 6443
   (R2). Node InternalIPs 172.30.140.101/102/103 (R15). Still UNKNOWN: kube-apiserver
   EndpointSlice addresses + Calico DNAT/enforcement point. Phase-2.

3. MON-9187 — **NOT FOUND (surveyed sources)**. `monitoring.coreos.com` NOT served
   (R11,R12,R13 = API_NOT_SERVED). No Prometheus/Grafana pod (R1); only metrics-server
   (R1,R2). Cluster monitoring=false (R9). CNPG pods expose 9187 but no scraper is
   observed. "Not found in surveyed sources" ≠ proven absent cluster-wide.

4. DNS-53 — **RESOLVED**. kube-dns Service 10.96.0.10, UDP+TCP 53 (+metrics 9153) in
   kube-system (R2).

5. S3-443 — **UNKNOWN**. ObjectStore `portal-db-backup` projected endpointURL/
   destinationPath/s3CredentialsName all null (R10). Backup works (R9 conditions) but
   the canonical endpoint is not in the projected fields (inline config / secret-ref).
   Phase-2.

6. ENV-* — **RESOLVED (NOT_CREATED)**. GatewayClass `eg` present (R6); Gateways `[]`
   (R7); EnvoyProxies `[]` (R8). Control-plane envoy-gateway pod+svc present (R1,R2).
   Dataplane/Gateway objects not created → NOT_CREATED_EXPECTED.

7. BASELINE — **RESOLVED**. `networkpolicies.networking.k8s.io -A` = `[]` (R5) → no
   existing k8s NetworkPolicy. Namespaces catalogued (R4): cert-manager, cnpg-system,
   default, envoy-gateway-system, kube-node-lease, kube-public, kube-system,
   metallb-system, piraeus-datastore, portal, velero. (Calico-specific policies are
   separate — Phase-2.)

8. CNI semantics — **PARTIAL**. CNI = Calico (API group `crd.projectcalico.org` served,
   R14); node podCIDRs 10.244.0/1/2.0/24 (R15). Still UNKNOWN: Calico mode
   (iptables/eBPF), Calico NetworkPolicy/GlobalNetworkPolicy, DNAT enforcement point.
   Phase-2.
