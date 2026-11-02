# P8C RV-02 — gaps (reconciled, LI-01..03 corrected)

## Current Architect decision — c872eed (2026-11-02)

Authority: docs/architecture/P8C_RV02_ACCEPTANCE_c872eed_20261102.md.
AUTHORIZED_READ_SET_COMPLETE=YES; FOLLOWUP_LIVE_ARTIFACT=ACCEPTED_WITH_LIMITS.
FLOW_MATRIX_COMPLETE=NO; EFFECTIVE_POLICY_UNION=UNKNOWN; NETPOL_APPROVED_FOR_APPLY=NO.
This current decision supersedes conflicting historical status paragraphs below.
F-I1 succeeded for three Calico Pods; historical failing field remains UNKNOWN.
F-CNP/F-NP/F-GNP/F-HEP were complete empty lists at 2026-11-02T09:35:24–25Z.
F-NP is crd.projectcalico.org/v1, not a new networking.k8s.io NetworkPolicy inventory.
F-FELIX observes default Auto only; F-TIER observes three tier configurations, not traffic effects.
The one-run budget is consumed; no further live run is authorized.
Next authorized work is the bounded OFFLINE-ROLLOUT-DECISION in the linked decision.
No collector/source rework or accepted platform tests are required.


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

## Phase-4 compat one-run 20261102 (gate e9553b8)

Artifact: evidence/P8/20261102T023500Z-p8c-rv02-followup-compat-onerun/ (followup.jsonl, 9 records, EXIT=1, 4 collector invocations).

- F-D1 **OK** — 23 Calico API resource descriptors served (unchanged surface).
- F-CS **compatible=true** — live CNP v1alpha2 normalized spec hash `ff433d34…` equals the pinned
  Calico manifest value. The earlier "schema drift" was a wrong pin, not a live change (LR-02 confirmed).
- F-CNP **OK, 0 items** — `clusternetworkpolicies` list is empty: **no ClusterNetworkPolicy
  objects deployed** in the cluster.
- F-I1 **PARSE_ERROR (diag=ITEM)** — raw GET PodList envelope/metadata parsed (exit 0) but a
  calico-node pod item failed the accepted `project_pod_identity`; identity not approved →
  F-NP/F-GNP/F-FELIX/F-HEP/F-TIER remain BLOCKED_NOT_EXECUTED. Failing field not recovered
  (raw stdout suppressed by design).
  Post-run review 980cee5 isolated MI-01: typed core/v1 PodList items MAY omit TypeMeta
  (kind/apiVersion), which the strict `_require(obj,'Pod','v1')` rejected — a proven source defect
  consistent with the observed ITEM, now fixed offline (absent TypeMeta derived from the verified
  typed-list context; MI-02/MI-02A add finite value-free itemDiag codes). The exact live failing
  field is NOT established from this evidence; LIVE_FAILING_FIELD=UNKNOWN.
- BASELINE: CNP schema present + compatible, CNP object count = 0. CNI: identity still unresolved
  (now at ITEM stage, not envelope). No effective-policy-union / per-node mode / traffic-flow
  conclusion. NEW_GATE_RUN_BUDGET=CONSUMED; PHASE2_NEW_RUN_APPROVED=NO.

## Architect review 980cee5 — typed PodList boundary

Review: docs/architecture/P8C_RV02_REVIEW_980cee5_20261102.md.
Four SHA256SUMS entries independently verified; 9 records / 4 collector calls.
F-CS compatibility and complete empty F-CNP list are accepted at collection time
2026-11-02T02:33:09Z only; they do not establish an empty effective policy union.
F-I1 ITEM remains live-unresolved. Offline reproduction proves that the strict standalone
Pod projector rejects legal typed PodList items without nested kind/apiVersion.
Those fields in derived-i1-fixture.json were synthetic, not captured live.
Exact live failing field remains UNKNOWN; missing TypeMeta is a reproduced source defect,
not a recovered raw live fact. Narrow F-I1 adapter + value-free item diagnostics authorized
source-only. Shared S1/digest guard and accepted LC-01/02/03 are not reopened.
Preflight/remote hash-check details remain operator-attested (no separate raw transcript).
NEW_GATE_RUN_BUDGET=CONSUMED; PHASE2_NEW_RUN_APPROVED=NO;
NETPOL_APPROVED_FOR_APPLY=NO; FLOW_MATRIX_COMPLETE=NO.

## Architect review 4913f07 — MI-01 closed, MI-02A diagnostic residual

Review: docs/architecture/P8C_RV02_REVIEW_4913f07_20261102.md.
MI-01 typed-PodList TypeMeta adaptation independently accepted (143/36/6 suites pass;
input immutability checked). Supplemental/S1 remain byte-identical. Historical live
failing field remains UNKNOWN; TypeMeta omission is an offline-proven compatibility defect.
MI-02 empty-output/fail-closed/value-free behavior passes. One diagnostic accuracy issue:
absent/null optional status masks malformed image/ports/restartPolicy as STATUS. Supplied
14-case regression: 8 pass / 6 fail; narrow diagnostic None-to-{} correction authorized offline.
Do not reopen MI-01 or rerun accepted platform tests. PHASE2_NEW_RUN_APPROVED=NO;
OWNER_PHASE2_HANDOFF_ALLOWED=NO; NETPOL_APPROVED_FOR_APPLY=NO; FLOW_MATRIX_COMPLETE=NO.

## Architect acceptance eed114e — source compatibility closed

Decision: docs/architecture/P8C_RV02_ACCEPTANCE_eed114e_20261102.md.
MI-01 remains accepted; MI-02/MI-02A CLOSED / INDEPENDENTLY VERIFIED.
Fresh followup 147/147 and supplied diagnostic regression 4 methods/14 subcases PASS.
Supplemental/S1 byte-identical. No further source rework for these findings.
This supersedes the preceding MI-02A residual paragraph for current source status only;
all historical live results are unchanged. LIVE_FAILING_FIELD=UNKNOWN;
FLOW_MATRIX_COMPLETE=NO; last live F-I1 still unresolved until a separately authorized run.
PHASE2_NEW_RUN_APPROVED=NO; OWNER_PHASE2_HANDOFF_ALLOWED=NO;
NETPOL_APPROVED_FOR_APPLY=NO; P8C=NOT_FINAL_ACCEPTED.

## Phase-5 podlist one-run 20261102 (gate 740a620) — complete read (EXIT=0)

Artifact: evidence/P8/20261102T094000Z-p8c-rv02-podlist-onerun/ (followup.jsonl, 9 records, EXIT=0, 9 collector invocations).

- F-I1 **OK** — 3 calico-node pods identified (`calico-node-4krkt`, `calico-node-lgmtz`,
  `calico-node-mqrgg`); identity approved through the unchanged S1 gate. The MI-01 typed-PodList
  TypeMeta adapter resolved the previous ITEM failure. LIVE_FAILING_FIELD no longer UNKNOWN at the
  read level, but the exact historical field that failed the pre-fix run remains unrecovered.
- F-CS **compatible=true** (ff433d34… = pin); F-CNP/F-NP/F-GNP/F-HEP all **0 items**.
- F-FELIX **default FelixConfiguration `nftablesMode=Auto`** (bpfEnabled/iptablesBackend/nodeSelector null).
- F-TIER **3 objects**: `default` (1000000, Deny), `kube-admin` (1000, Pass), `kube-baseline` (10000000, Pass).
- BASELINE: Calico policy surface live (23 descriptors); no NP/GNP/CNP/HEP objects; 3 tiers present.
- CNI: identity RESOLVED (3 pods); effective per-node mode still UNKNOWN (only default Felix read,
  per-node overrides not collected). Effective policy union / tier→endpoint binding / DNAT /
  traffic-flow remain UNKNOWN (no policy objects + tier defaults are recorded, not evaluated).
FLOW_MATRIX_COMPLETE=YES at the read level (all 9 reads OK); semantic limits above stand.
NEW_GATE_RUN_BUDGET=CONSUMED; PHASE2_NEW_RUN_APPROVED=NO; NETPOL_APPROVED_FOR_APPLY=NO.

## Offline rollout decision status (review f7bf263)

Review: docs/architecture/P8C_RV02_REVIEW_f7bf263_20261102.md.
OFFLINE_ROLLOUT_DECISION=PARTIAL / RESIDUAL_REQUIRED → R1-RESIDUAL
(docs/architecture/P8C_RV02_OFFLINE_ROLLOUT_DECISION_20261102.md) closes RR-01…03.
ARCHITECT_ACCEPTED: удаление PR-1/PR-2, P7 historical S3, ограниченный API /32-кандидат,
UID-precondition rollback, candidate delta (Barman controller→5432, API /24) NOT_APPROVED.
AUTHOR_PROPOSAL (не Architect-accepted): ingress-модель, union-aware S0–S4 rollback, PR-3..6.
Candidate policy YAML unchanged; FLOW_MATRIX_COMPLETE=NO; NETPOL_APPROVED_FOR_APPLY=NO.


## Architect review 1a0b4c1 — 2026-11-02

Authority: docs/architecture/P8C_RV02_REVIEW_1a0b4c1_20261102.md.
The residual proposal remains PARTIAL. Document corrections A/B/C are required; this does not reopen
accepted source or 9/9 inventory. No live read, collector test, apply, CI or production gate is opened.
FLOW_MATRIX_COMPLETE=NO; EFFECTIVE_POLICY_UNION=UNKNOWN; P8C=NOT_FINAL_ACCEPTED.
