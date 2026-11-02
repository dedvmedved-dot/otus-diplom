# P8C RV-02 — flow matrix (reconciled, LI-01..03 corrected)

## Current Architect decision — b5d8cab (2026-11-02, OD-01..05)

Authority: docs/architecture/P8C_RV02_REVIEW_a9e6fac_20261102.md (REVIEW_HEAD=a9e6fac).
AUTHORIZED_READ_SET_COMPLETE=YES; FLOW_MATRIX_COMPLETE=NO; EFFECTIVE_POLICY_UNION=UNKNOWN.
NETPOL_APPROVED_FOR_APPLY=NO; CI/PRODUCTION=NOT_AUTHORIZED; P8C=NOT_FINAL_ACCEPTED.
This decision supersedes the c872eed header below. The offline rollout plan was reworked (R1):
docs/architecture/P8C_RV02_OFFLINE_ROLLOUT_DECISION_20261102.md resolves OD-01..05 —
PR-1 (CalicoNodeStatus backend) and PR-2 (IPPool/DNS) REMOVED; B1 resolved by a
representation-robust API rule (10.96.0.1/32:443 + 172.30.140.101/102/103/32:6443, not /24);
B2 resolved via P7 historical S3 fact + Barman role decomposition; B3 resolved from
gateway.yaml/deployment.yaml; union-aware state/rollback; candidate delta NOT_APPROVED
(Barman controller→5432, API /24). Candidate policy YAML unchanged.

## Historical Architect decision — c872eed (2026-11-02)

Authority: docs/architecture/P8C_RV02_ACCEPTANCE_c872eed_20261102.md.
AUTHORIZED_READ_SET_COMPLETE=YES; FOLLOWUP_LIVE_ARTIFACT=ACCEPTED_WITH_LIMITS.
FLOW_MATRIX_COMPLETE=NO; EFFECTIVE_POLICY_UNION=UNKNOWN; NETPOL_APPROVED_FOR_APPLY=NO.
This supersedes conflicting historical status paragraphs below.
F-I1 succeeded for three Calico Pods; historical failing field remains UNKNOWN.
F-CNP/F-NP/F-GNP/F-HEP were complete empty lists at 2026-11-02T09:35:24–25Z.
F-NP is crd.projectcalico.org/v1, not a new networking.k8s.io NetworkPolicy inventory.
F-FELIX observes default Auto only; F-TIER observes three tier configurations, not traffic effects.
The one-run budget is consumed; no further live run is authorized.

## Current 14-flow reconciliation — c872eed

Evidence F-* refers to evidence/P8/20261102T094000Z-p8c-rv02-podlist-onerun/followup.jsonl.
The nine successful reads establish identity/policy configuration, not new directed traffic.
All previous observations retain their original timestamps; current emptiness must not be
combined with October observations as if they were one atomic snapshot.

| FLOW-ID | Effect of this run / remaining decision |
|---|---|
| REP-5432 | No new replication observation; base R1–R3 remain configuration proof. Preserve existing CNPG traffic in candidate isolation plan. |
| IM-8000 | No new instance-manager flow observation; retain versioned/base proof and assess both directions. |
| OP-IM-8000 | No new operator traffic observation; exact existing selector/direction requires source-based decision. |
| BAR-5432 (legacy) | No new Barman reading; controller 9090 versus sidecar backup/WAL roles remain distinct; no controller→DB5432 permission inferred. |
| MON-9187 | No new monitoring survey; not-found in older surveyed sources does not establish universal absence. |
| DNS-53 | Base Service/EndpointSlice configuration retained; destination representation under proposed CNI rules remains a design decision. |
| API-6443 | F-I1 confirms Calico identity; F-FELIX default Auto does not resolve effective mode or Service DNAT enforcement. |
| S3-443 | Prior endpoint configuration retained; actual routed destination/allowlist is not established by this run. |
| APP-DB-5432 | PLANNED; read-only inventory does not deploy Portal or prove DB TLS connectivity. |
| APP-MET-9187 | PLANNED; exact application-to-CNPG selector/port remains candidate design. |
| MIG-DB-5432 | PLANNED; migrator requires only its accepted DB/DNS dependencies, not platform mutation rights. |
| ENV-XDS-18000 | PLANNED; prior control-plane configuration retained, no new dataplane evidence. |
| ENV-BACK-8080 | PLANNED; Gateway-owned source namespace/name and Portal selector remain required. |
| ENV-LISTENER | PLANNED; external listener/backend/health-check treatment must be explicit before apply review. |

Shared baseline: F-CNP/F-NP/F-GNP/F-HEP complete empty; F-TIER has three configured tiers.
This closes blocked follow-up reads, not effective-policy-union evaluation. No change to candidate
policy YAML or permission to isolate CNPG follows. FLOW_MATRIX_COMPLETE=NO.


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

## Review of offline decision a9e6fac — current scope

Authority: docs/architecture/P8C_RV02_REVIEW_a9e6fac_20261102.md.
OFFLINE_ROLLOUT_DECISION=PARTIAL / REWORK_REQUIRED (OD-01…05).
PR-1 CalicoNodeStatus does not expose the proposed dataplane/DNAT field; PR-2 IPPool/DNS
must not be represented as proof of CNPG S3 reachability. Neither proposal is authorized.
The first selecting Ingress/Egress CNPG policy already isolates its Pods; state-dependent
rollback and a completed ingress design are required before apply review.
Accepted c872eed inventory and eed114e collector remain CLOSED. No new collector/run/tests.
Only OFFLINE-ROLLOUT-DECISION-R1 documentary corrections are authorized.
FLOW_MATRIX_COMPLETE=NO; NETPOL_APPROVED_FOR_APPLY=NO; CI/production remain closed.
