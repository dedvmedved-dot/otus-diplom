# P8C RV-02 — flow matrix (candidate, pre-live-inventory)

Every row is keyed by a stable FLOW-ID. `proof type`:
- `VERSIONED_DESIGN` — derived from versioned source manifests (portal/manifests,
  barman-cloud manifest), not from live observation;
- `PLANNED` — object not yet created (Portal Gateway/dataplane/Portal pods);
- `UNKNOWN` — requires live read-only inventory (blocked: no authorized kubectl).
No row is claimed as runtime-verified; live raw proof is pending (see gaps.md).

Policy reference = object (namespace/name) + rule direction from
`portal/manifests/networkpolicy.yaml` (NOT APPROVED FOR APPLY).

| FLOW-ID | Source (ns:labels) | Destination (ns:labels/IP) | proto:port | dir/purpose | proof | policy rule |
|---|---|---|---|---|---|---|
| REP-5432 | portal: cnpg.io/cluster=portal-db, podRole=instance | portal: same | TCP 5432 | replication | VERSIONED_DESIGN (CNPG) | p8c-cnpg-existing-flows ingress+egress |
| IM-8000 | portal: cnpg.io/cluster=portal-db | portal: same | TCP 8000 | instance-manager | VERSIONED_DESIGN (source port 8000) | p8c-cnpg-existing-flows ingress+egress |
| OP-IM-8000 | cnpg-system: app.kubernetes.io/name=cloudnative-pg | portal: cnpg.io/cluster=portal-db | TCP 8000 | operator reconcile | VERSIONED_DESIGN (CNPG) | p8c-cnpg-existing-flows ingress |
| BAR-5432 | cnpg-system: app=barman-cloud | portal: cnpg.io/cluster=portal-db | TCP 5432 | Barman plugin | UNKNOWN (declared 9090 vs DB5432 direction) | p8c-cnpg-existing-flows ingress |
| MON-9187 | monitoring (UNKNOWN ns/labels) | portal: cnpg.io/cluster=portal-db | TCP 9187 | metrics scrape | UNKNOWN (no ServiceMonitor/PodMonitor discovery) | p8c-cnpg-existing-flows ingress |
| DNS-53 | portal: cnpg.io/cluster=portal-db / pak-portal / pak-portal-migrator | kube-system: k8s-app=kube-dns | UDP+TCP 53 | resolution | UNKNOWN (kube-dns Service/eps not verified) | cnpg/dns baseline egress + portal/migrator egress |
| API-6443 | portal: cnpg.io/cluster=portal-db (+ portal pod) | API (UNKNOWN exact dest; candidate 172.30.140.0/24 NOT approved) | TCP 6443 | Kubernetes API | UNKNOWN (Service/DNAT/CNI path) | cnpg egress ipBlock + portal egress ipBlock |
| S3-443 | portal: cnpg.io/cluster=portal-db | SeaweedFS (candidate 172.30.143.10/32) | TCP 443 | backup/objectstore | UNKNOWN (canonical ObjectStore endpoint) | cnpg egress ipBlock |
| APP-DB-5432 | portal: app.kubernetes.io/name=pak-portal | portal: cnpg.io/cluster=portal-db | TCP 5432 | app DB | VERSIONED_DESIGN (deployment.yaml) | portal egress + cnpg ingress |
| APP-MET-9187 | portal: app.kubernetes.io/name=pak-portal | portal: cnpg.io/cluster=portal-db | TCP 9187 | CNPG metrics | VERSIONED_DESIGN | portal egress + cnpg ingress |
| MIG-DB-5432 | portal: app.kubernetes.io/name=pak-portal-migrator | portal: cnpg.io/cluster=portal-db | TCP 5432 | schema bootstrap | VERSIONED_DESIGN (Job) | migrator egress + cnpg ingress |
| ENV-XDS-18000 | envoy-gateway-system: owning-gateway-name=portal-gateway, owning-gateway-namespace=portal | envoy-gateway-system: control-plane=envoy-gateway | TCP 18000 | xDS | PLANNED (dataplane not created) | dataplane egress |
| ENV-BACK-8080 | envoy-gateway-system: owning… (dataplane) | portal: app.kubernetes.io/name=pak-portal | TCP 8080 | UI backend (svc:80→8080) | PLANNED | dataplane egress + portal ingress |
| ENV-LISTENER | external → dataplane | envoy-gateway-system: dataplane | UNKNOWN listener port | ingress | PLANNED/NOT_CREATED_EXPECTED | NOT modeled (external admission is deployment-gate) |

## Explicitly NOT resolved (gaps.md)
- Barman plugin actual service/port/direction (declared TCP9090 in barman-cloud
  manifest ≠ assumed controller→DB5432).
- API 6443 actual destinations (Service/DNAT/CNI enforcement point) — /24 NOT approved.
- Monitoring: served ServiceMonitor/PodMonitor + actual scrape workload identity
  (absence NOT established).
- DNS kube-dns Service/EndpointSlices + TCP/UDP actual.
- S3 canonical ObjectStore endpoint + protocol/port.
- Envoy GatewayClass/EnvoyProxy/controller + dataplane namespace/labels + owning
  name+namespace (objects not created → NOT_CREATED_EXPECTED).
- Existing NetworkPolicy union + all portal namespace workload identities.
