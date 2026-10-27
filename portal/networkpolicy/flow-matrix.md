# P8C RV-02 — flow matrix (reconciled, LI-01..03 corrected)

Proof types: `OBSERVED_CONFIG` / `OBSERVED_STATUS` (inventory.jsonl record R#),
`VERSIONED_DESIGN` (source manifests), `PLANNED` (not created), `UNKNOWN`.
Base evidence: `evidence/P8/20261026T173244Z-p8c-rv02-live-inventory/inventory.jsonl`.

| FLOW-ID | Source | Destination | proto:port | purpose | proof | policy rule |
|---|---|---|---|---|---|---|
| REP-5432 | portal: cnpg.io/cluster=portal-db, cnpg.io/podRole=instance | portal: same | TCP 5432 | replication | OBSERVED_CONFIG (R1 pods 5432; R3 eps 10.244.184.22/.254.108/.190.50) | p8c-cnpg-existing-flows |
| IM-8000 | portal: cnpg.io/cluster=portal-db | portal: same | TCP 8000 | instance-manager | OBSERVED_CONFIG (R1 port 8000) | p8c-cnpg-existing-flows |
| OP-IM-8000 | cnpg-system: app.kubernetes.io/name=cloudnative-pg | portal: cnpg.io/cluster=portal-db | TCP 8000 | operator | OBSERVED_CONFIG (R1 operator) + VERSIONED_DESIGN | p8c-cnpg-existing-flows ingress |
| BAR-5432 (legacy ID) | CNPG operator → plugin control Service; separately per-instance sidecar | cnpg-system/barman-cloud control endpoint; separate ObjectStore target | control TCP9090 source/endpoint; sidecar local IPC and live S3 routing UNRESOLVED | separate control and backup/WAL roles | OBSERVED identity/9090 endpoint R2/R3; VERSIONED_DESIGN in supplemental-design.md §4; sidecar/controller identity OBSERVED_CONFIG (Phase-2 S1/S2); traffic UNKNOWN | existing candidate ingress is NOT validated by this row; no plugin→DB5432 permission inferred |
| MON-9187 | monitoring scraper | portal: cnpg.io/cluster=portal-db | TCP 9187 | metrics scrape | NOT FOUND (R11-13 no Prometheus Operator; no scraper pod) | p8c-cnpg-existing-flows ingress |
| DNS-53 | portal workloads | kube-system kube-dns 10.96.0.10; eps 10.244.254.65/.66 | UDP+TCP 53 | resolution | OBSERVED_CONFIG (R2 svc; R3 eps) | dns baseline egress + portal/migrator egress |
| API-6443 | portal workloads | default/kubernetes 10.96.0.1:443→6443; eps 172.30.140.101/102/103 ready (R3) | TCP 6443 | Kubernetes API | OBSERVED_CONFIG (R2 svc + R3 eps); DNAT/CNI UNKNOWN | cnpg/portal egress ipBlock |
| S3-443 | portal: cnpg.io/cluster=portal-db | ObjectStore endpoint `s3-backup.demo-pak.test` | TCP 443 (https) | backup/objectstore | OBSERVED_CONFIG (Phase-2 C1): endpointURL `https://s3-backup.demo-pak.test`, destinationPath `s3://portal-postgres-backup`; secret-ref names/keys only; 443 inferred from scheme, live route/traffic UNKNOWN | candidate cnpg egress ipBlock NOT validated |
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
  exact `quay.io/calico/node` v3.32.0 pin + pinned digest. The one authorized Phase-2 run is complete: I1 UNSUPPORTED; C3/C4/C5 blocked.
  No further run is authorized.

## Architect reconciliation after 7970620

The BAR-5432 identifier is historical, not evidence that the plugin controller connects
to database port 5432. See supplemental-design.md §§3–5 for source-backed roles,
Felix priority and DNAT limits. S3-443 now has observed endpoint configuration (Phase-2 C1), not a validated live allowlist.
HostEndpoint/Tier and node-specific Felix overrides are outside the ten reads;
EFFECTIVE_POLICY_UNION remains UNKNOWN even if those reads later succeed.
PHASE2_LIVE_READS_APPROVED=NO; NETPOL_APPROVED_FOR_APPLY=NO.

## Phase-2 review 832591b (supersedes stale pre-run wording)

Evidence: evidence/P8/20261027T140000Z-p8c-rv02-phase2-live/result/supplemental.jsonl.
Review: docs/architecture/P8C_RV02_REVIEW_832591b_20261027.md.
D1/D2 discovery observes Calico resources and ClusterNetworkPolicy API, not object presence.
I1 bare imageID is UNSUPPORTED by format before digest comparison; relation to the pin
is UNPROVEN (not established platform-child). C3/C4/C5 were NOT_EXECUTED.
S1/S2 establish per-instance native sidecar (restartPolicy=Always) and controller identity,
not traffic direction. C1 URL path is discarded; bucket suffix/prefix not collected.
ONE_RUN_BUDGET=CONSUMED; NEW_LIVE_RUN_APPROVED=NO; FLOW_MATRIX_COMPLETE=NO.
