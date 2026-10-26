# P8C RV-02 — flow matrix (post live-inventory reconciliation)

Proof types: `OBSERVED_CONFIG` (from inventory.jsonl record R#), `OBSERVED_STATUS`,
`VERSIONED_DESIGN` (source manifests), `PLANNED` (object not created), `UNKNOWN`
(not provable from base inventory). Base evidence: `evidence/P8/20261026T173244Z-p8c-rv02-live-inventory/inventory.jsonl`.
Policy reference = object (namespace/name) + rule from `portal/manifests/networkpolicy.yaml` (NOT APPROVED FOR APPLY).

| FLOW-ID | Source (ns:labels) | Destination (ns:labels/IP) | proto:port | dir/purpose | proof | policy rule |
|---|---|---|---|---|---|---|
| REP-5432 | portal: cnpg.io/cluster=portal-db, podRole=instance | portal: same | TCP 5432 | replication | OBSERVED_CONFIG (R1 pods 5432, R2 svc r/ro/rw) | p8c-cnpg-existing-flows ingress+egress |
| IM-8000 | portal: cnpg.io/cluster=portal-db | portal: same | TCP 8000 | instance-manager | OBSERVED_CONFIG (R1 port 8000) | p8c-cnpg-existing-flows ingress+egress |
| OP-IM-8000 | cnpg-system: app.kubernetes.io/name=cloudnative-pg | portal: cnpg.io/cluster=portal-db | TCP 8000 | operator reconcile | OBSERVED_CONFIG (R1 operator) + VERSIONED_DESIGN | p8c-cnpg-existing-flows ingress |
| BAR-5432 | cnpg-system: app=barman-cloud (plugin) | portal: cnpg.io/cluster=portal-db / S3 | TCP 9090 svc / 5432 db | Barman plugin | PARTIAL — plugin 9090 observed (R1,R2); DB/S3 direction UNKNOWN | p8c-cnpg-existing-flows ingress |
| MON-9187 | monitoring scraper | portal: cnpg.io/cluster=portal-db | TCP 9187 | metrics scrape | NOT FOUND (R11-13 no Prometheus Operator; no scraper pod) | p8c-cnpg-existing-flows ingress |
| DNS-53 | portal workloads | kube-system: k8s-app=kube-dns (10.96.0.10) | UDP+TCP 53 | resolution | OBSERVED_CONFIG (R2) | cnpg/dns baseline egress + portal/migrator egress |
| API-6443 | portal workloads | default/kubernetes 10.96.0.1:443→6443 | TCP 6443 | Kubernetes API | PARTIAL (R2 svc; DNAT/CNI UNKNOWN) | cnpg egress ipBlock + portal egress ipBlock |
| S3-443 | portal: cnpg.io/cluster=portal-db | ObjectStore endpoint (UNKNOWN) | TCP 443 | backup/objectstore | UNKNOWN (R10 endpoint null; inline not projected) | cnpg egress ipBlock |
| APP-DB-5432 | portal: app.kubernetes.io/name=pak-portal | portal: cnpg.io/cluster=portal-db | TCP 5432 | app DB | PLANNED (Portal NOT_CREATED) | portal egress + cnpg ingress |
| APP-MET-9187 | portal: pak-portal | portal: cnpg cluster | TCP 9187 | CNPG metrics | PLANNED | portal egress + cnpg ingress |
| MIG-DB-5432 | portal: pak-portal-migrator | portal: cnpg cluster | TCP 5432 | schema bootstrap | PLANNED (NOT_CREATED) | migrator egress + cnpg ingress |
| ENV-XDS-18000 | envoy-gateway-system: dataplane | envoy-gateway-system: control-plane | TCP 18000 | xDS | PLANNED (control-plane 18000 R1/R2; dataplane NOT_CREATED) | dataplane egress |
| ENV-BACK-8080 | envoy dataplane | portal: pak-portal | TCP 8080 | UI backend | PLANNED | dataplane egress + portal ingress |
| ENV-LISTENER | external → dataplane | envoy dataplane | listener port | ingress | PLANNED (NOT_CREATED) | NOT modeled (deployment-gate) |

## Newly established facts (vs pre-inventory)
- CNI = **Calico** (`crd.projectcalico.org` served, R14); node podCIDRs 10.244.0/1/2.0/24 (R15).
- Existing k8s NetworkPolicy union = **EMPTY** (R5 `[]`).
- GatewayClass `eg` exists; **no Gateway / no EnvoyProxy** (R6-R8) → dataplane NOT_CREATED.
- CNPG Cluster `portal-db` healthy, 3/3 ready, 10Gi (R9); backup conditions True (archiving+backup working).
- ObjectStore `portal-db-backup` projected data all null (R10) → inline backup endpoint not captured by base projection.
- Prometheus Operator absent (`monitoring.coreos.com` API_NOT_SERVED R11-13); only metrics-server (R1/R2).
- Envoy control-plane ports: grpc 18000, ratelimit 18001, wasm 18002, metrics 19001, webhook 9443 (R1/R2).
