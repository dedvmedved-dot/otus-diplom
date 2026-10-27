# P8C RV-02 — flow matrix (reconciled, LI-01..03 corrected)

Proof types: `OBSERVED_CONFIG` / `OBSERVED_STATUS` (inventory.jsonl record R#),
`VERSIONED_DESIGN` (source manifests), `PLANNED` (not created), `UNKNOWN`.
Base evidence: `evidence/P8/20261026T173244Z-p8c-rv02-live-inventory/inventory.jsonl`.

| FLOW-ID | Source | Destination | proto:port | purpose | proof | policy rule |
|---|---|---|---|---|---|---|
| REP-5432 | portal: cnpg.io/cluster=portal-db, cnpg.io/podRole=instance | portal: same | TCP 5432 | replication | OBSERVED_CONFIG (R1 pods 5432; R3 eps 10.244.184.22/.254.108/.190.50) | p8c-cnpg-existing-flows |
| IM-8000 | portal: cnpg.io/cluster=portal-db | portal: same | TCP 8000 | instance-manager | OBSERVED_CONFIG (R1 port 8000) | p8c-cnpg-existing-flows |
| OP-IM-8000 | cnpg-system: app.kubernetes.io/name=cloudnative-pg | portal: cnpg.io/cluster=portal-db | TCP 8000 | operator | OBSERVED_CONFIG (R1 operator) + VERSIONED_DESIGN | p8c-cnpg-existing-flows ingress |
| BAR-5432 | cnpg-system plugin `barman-cloud.cloudnative-pg.io` (R3) | portal DB / S3 | 9090 svc / 5432 db / S3 443 | Barman plugin | OBSERVED: pluginName + svc 9090 + eps 10.244.190.49 (R2,R3); direction DB/S3 UNKNOWN | p8c-cnpg-existing-flows ingress |
| MON-9187 | monitoring scraper | portal: cnpg.io/cluster=portal-db | TCP 9187 | metrics scrape | NOT FOUND (R11-13 no Prometheus Operator; no scraper pod) | p8c-cnpg-existing-flows ingress |
| DNS-53 | portal workloads | kube-system kube-dns 10.96.0.10; eps 10.244.254.65/.66 | UDP+TCP 53 | resolution | OBSERVED_CONFIG (R2 svc; R3 eps) | dns baseline egress + portal/migrator egress |
| API-6443 | portal workloads | default/kubernetes 10.96.0.1:443→6443; eps 172.30.140.101/102/103 ready (R3) | TCP 6443 | Kubernetes API | OBSERVED_CONFIG (R2 svc + R3 eps); DNAT/CNI UNKNOWN | cnpg/portal egress ipBlock |
| S3-443 | portal: cnpg.io/cluster=portal-db | ObjectStore endpoint | TCP 443 | backup/objectstore | VERSIONED_DESIGN source = `https://s3-backup.demo-pak.test` (objectstore-portal-db.yaml); LIVE value UNKNOWN (base read spec.data, real path spec.configuration) | cnpg egress ipBlock |
| APP-DB-5432 | portal: pak-portal | portal: cnpg cluster | TCP 5432 | app DB | PLANNED (Portal NOT_CREATED) | portal egress + cnpg ingress |
| APP-MET-9187 | portal: pak-portal | portal: cnpg cluster | TCP 9187 | CNPG metrics | PLANNED | portal egress + cnpg ingress |
| MIG-DB-5432 | portal: pak-portal-migrator | portal: cnpg cluster | TCP 5432 | bootstrap | PLANNED | migrator egress + cnpg ingress |
| ENV-XDS-18000 | envoy dataplane | envoy-gateway-system control-plane | TCP 18000 | xDS | PLANNED (control-plane 18000 R1/R2; dataplane NOT_CREATED) | dataplane egress |
| ENV-BACK-8080 | envoy dataplane | portal: pak-portal | TCP 8080 | UI backend | PLANNED | dataplane egress + portal ingress |
| ENV-LISTENER | external → dataplane | envoy dataplane | listener | ingress | PLANNED (NOT_CREATED) | NOT modeled |

## LI corrections (supersede prior inaccurate conclusions)
- **LI-01** ObjectStore endpoint lives in `spec.configuration` (not `spec.data`). Base
  R10 nulls = NOT_COLLECTED_AT_CORRECT_PATH, NOT "no endpoint". CNPG plugin mapping is
  `spec.plugins[].parameters.barmanObjectName` (=portal-db-backup), NOT
  `spec.backup.barmanObjectStore.name`. Source refs: manifests/barman-cloud/v0.13.0/
  objectstore-portal-db.yaml + manifests/cnpg/v1.30.1/portal-db-cluster.yaml.
- **LI-02** API endpoints already in R3 (172.30.140.101/102/103:6443 ready); kube-dns
  eps 10.244.254.65/.66:53; barman-cloud slice pluginName + 9090 + 10.244.190.49. No re-collect.
- **LI-03** K8S_NETWORKPOLICY_LIST=EMPTY (R5) ≠ no policies: R14 serves
  `crd.projectcalico.org/v1` + `policy.networking.k8s.io/v1alpha2` → EFFECTIVE_POLICY_UNION=UNKNOWN.
  Node podCIDRs (10.244.0/1/2.0/24) ≠ actual pod IPs (10.244.184/190/254.*) — not an allowlist.
- **LI-04** Port 9090 alone does not prove plugin→DB/S3 direction. R1 projects containers
  only, not initContainers; direction/route/enforcement remain UNKNOWN. Phase-2 supplemental
  identity (I1/S1/S2) collects pod image/imageID; version-specific Calico reads gate on the
  exact `quay.io/calico/node` v3.32.0 pin + pinned digest. Collector prepared
  (supplemental.py + supplemental_test.py), NOT approved to run.
