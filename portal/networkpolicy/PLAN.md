# P8C NetworkPolicy plan (D1) — read-only preparation, not yet applied

## Active source-only task — CANDIDATE-AND-GATES-R3-CORRECTION

Authority: docs/architecture/P8C_REVIEW_dfb9130_AND_R3_CORRECTION_20261103.md.
Primary Hermes only. dfb9130 is PARTIAL: functional test additions accepted; structural guard,
deployment draft consistency, bounded observation design and scan evidence require correction.
Architect selects operator-only primary-bound exporter observation and separate private-seed bootstrap
as SOURCE-ONLY designs, not live authorization. Preserve accepted YAML/app/collector and inventory 9/9.
Only addressed tests, three gate drafts, this active reference and new evidence may change.
No live/SSH/registry, workflow/CI, Owner helpers, policy apply or production action is authorized.

## Current Architect acceptance — 1b32e4d

Authority: docs/architecture/P8C_RV02_ACCEPTANCE_1b32e4d_20261102.md.
OFFLINE_DESIGN=ACCEPTED_WITH_RUNTIME_LIMITS; DOCUMENT_REWORK_REQUIRED=NO.
A/B/C document corrections are closed in the canonical plan published with this acceptance.
The author commit alone is not declared error-free; Architect corrections are recorded.
Collector/source and c872eed 9/9 remain accepted; no reruns or source changes.
FLOW_MATRIX_COMPLETE=NO; EFFECTIVE_POLICY_UNION=UNKNOWN; EXECUTION_GATE_READY=NO.
Fresh S3/WAL verification and current baseline remain runtime dependencies; S1 cannot start.
PHASE2_NEW_RUN_APPROVED=NO; NETPOL_APPROVED_FOR_APPLY=NO; CI/production/P8D–P8G/P9 closed.
No new task to rework the offline document is assigned to Hermes or Hermes2.
Candidate policy YAML is unchanged and NOT_APPROVED_FOR_APPLY.

## Historical Architect decision — b5d8cab (2026-11-02, OD-01..05)

Authority: docs/architecture/P8C_RV02_REVIEW_a9e6fac_20261102.md.
AUTHORIZED_READ_SET_COMPLETE=YES; FLOW_MATRIX_COMPLETE=NO; EFFECTIVE_POLICY_UNION=UNKNOWN.
NETPOL_APPROVED_FOR_APPLY=NO; CI/PRODUCTION=NOT_AUTHORIZED; P8C=NOT_FINAL_ACCEPTED.
Rollout plan reworked (R1): docs/architecture/P8C_RV02_OFFLINE_ROLLOUT_DECISION_20261102.md.
PR-1/PR-2 removed; B1 (API DNAT) resolved by representation-robust rule (10.96.0.1/32:443 +
172.30.140.101/102/103/32:6443); B2 (S3) resolved via P7 historical fact; B3 (ingress) resolved
from gateway.yaml/deployment.yaml; union-aware state/rollback (S0–S4); candidate delta NOT_APPROVED
(Barman controller→5432, API /24). Candidate policy YAML unchanged.

The older rollout sections remain historical candidates, not execution instructions.
The old S3 'live value UNKNOWN' row is superseded by accepted Phase-2 endpoint configuration;
routing remains UNKNOWN. No new live activity is implied by documentary reconciliation.


Live policy rollout is deferred until supply-chain (R3) and auth/pull (R4)
preconditions are ready (per D1/R2: "не вводить live policies без необходимости
deploy"). This document records candidate flows and known source facts. It does not certify the live inventory.

Current authority after 7970620: supplemental-design.md, coverage-matrix.md,
flow-matrix.md and gaps.md distinguish source design, observed base facts and UNKNOWN.
The historical bullets/rollout sequence below are not execution instructions.
Base inventory is already executed and is not to be rerun. Phase-2 live, apply,
rollback, CI and production gates remain CLOSED. Candidate policy YAML is unchanged.

## Historical inventory claims — superseded where contradicted by the reconciled evidence

- No NetworkPolicy exists cluster-wide (`kubectl get networkpolicy -A` -> none).
  portal namespace and envoy-gateway-system have NO default-deny baseline.
- Existing workloads/controllers in portal: CNPG operator (cnpg-system),
  postgres cluster portal-db (3 pods + barman-cloud sidecars), Barman plugin
  controller (cnpg-system; repository manifest confirmed), Velero (velero namespace: 4 deploy + node-agent),
  cert-manager (cert-manager ns), Envoy Gateway controller (envoy-gateway-system),
  MetalLB speaker/controller (metallb-system).
- DNS: CoreDNS kube-dns (kube-system), TCP/UDP 53.
- API server: 172.30.140.100:6443 (VIP).
- S3 (SeaweedFS): 172.30.143.10:443 (TLS; CNPG/Barman only).
- CNPG replication: pods portal-db-1/2/3, ports 5432 + 8000 (instance-manager,
  VERIFIED 2026-10-20 via pod spec containerPort; NOT 8008).
- Gateway: name `portal-gateway` (namespace portal), dataplane pods labeled
  `gateway.envoyproxy.io/owning-gateway-name: portal-gateway`; controller in
  envoy-gateway-system (control-plane=envoy-gateway) xDS on 18000.
- Barman plugin: S3 egress to 172.30.143.10:443 + CNPG cluster.
- Portal DB app: portal-db-rw.portal.svc:5432 (verify-full).
- Metrics: portal-db-metrics.portal.svc:9187 (CNPG instance manager).

## Flow matrix (source → destination:port → purpose)

| Source | Destination | Port | Purpose |
|---|---|---|---|
| CNPG pod (peer) | CNPG pod | 5432/8000 | replication / instance-manager |
| CNPG operator (cnpg-system) | CNPG pod | 8000 | reconcile/switchover |
| CNPG operator → plugin control Service; separate instance sidecar | barman-cloud control endpoint; separate ObjectStore target | control TCP9090; sidecar local IPC/live S3 routing unresolved | roles separated in supplemental-design.md §4; no controller→DB5432 permission inferred |
| Portal pod | CNPG pod | 5432/9187 | app DB / metrics scrape |
| Migrator Job | CNPG pod | 5432 | schema bootstrap |
| CNPG pod | DNS (kube-system) | 53 | resolution |
| CNPG pod | API (172.30.140.0/24) | 6443 | Kubernetes API |
| CNPG pod | S3 (172.30.143.10/32) | 443 | SeaweedFS backup |
| Portal pod | DNS/API/CNPG | 53/6443/5432/9187 | app dependencies |
| Envoy dataplane | control-plane (envoy-gateway-system) | 18000 | xDS |
| Envoy dataplane | Portal pod | 8080 | UI backend (svc :80→8080) |

## Planned new objects (created at deploy, after R3/R4)

1. `p8c-cnpg-existing-flows` (NetPol, portal) — FIRST policy selecting existing
   CNPG pods; one object containing the complete ingress+egress allowlist ONLY AFTER inventory closure
   (DNS, API, S3, replication, operator, monitoring, Portal/migrator). No
   separate DNS-only policy before it; no temporary allow-all.
2. `baseline-default-deny-all` + `baseline-allow-dns-egress` (portal) — after
   (1), per P4B baseline.
3. `p8c-portal-flows` (portal) — Portal pod: ingress only from Portal Envoy
   dataplane TCP 8080; egress DNS, Kubernetes API, CNPG 5432, metrics 9187.
4. `p8c-migrator-flows` (portal) — migrator: DNS + CNPG 5432 only, no API.
5. `p8c-portal-dataplane-flows` (envoy-gateway-system) — exact Gateway-owned
   dataplane labels, full listener/xDS/DNS/backend matrix; NO namespace-wide
   deny in envoy-gateway-system.

## Safety order (D1)

- Apply (1) first; read-only health check (CNPG 3/3, WAL, BSL) after each step;
  any degradation -> immediate rollback of only this task's new policies.
- Then (2) baseline, then (3)/(4) before Portal/migrator workloads, then (5)
  before external traffic is admitted to the new dataplane.
- Rollback: delete only policies listed above (return to the observed
  no-policy baseline); never mutate existing controller/CNPG/Velero specs.


## RV-02 inventory gate — BLOCKED, not approved for apply

Source correction (2026-10-21): immutable main `17c832c1be518bdc70e300cbbdc2bbee3bfc201c`,
`manifests/barman-cloud/v0.13.0/plugin-barman-cloud-v0.13.0-digest-pinned.yaml`
Deployment `cnpg-system/barman-cloud`, selector `app=barman-cloud`, container
port TCP9090. The prior `barman-cloud` namespace statement was wrong. A source
manifest is not proof of actual peer traffic. In particular inventory must resolve
CNPG/operator/instance-manager/plugin TCP9090 interactions before any CNPG isolation;
do not infer a flow from a declared port or assume controller->DB5432 suffices.
Gateway candidates now match BOTH owning name `portal-gateway` and namespace `portal`.

Required safe raw read-only evidence (UTC start/end, command, exit, selected fields):

| Flow | Required observation | Current proof |
|---|---|---|
| CNPG peers 5432/8000 | portal Pods labels/ports + Service targetPorts/EndpointSlices | OBSERVED (R1 pods 5432/9187/8000; R2 svc r/ro/rw→5432; R3 eps) |
| operator/plugin | cnpg-system Pods labels/ports, selected Service endpoints; controller API configuration for plugin and reconcile paths | OBSERVED identity (R1 cnpg-controller-manager; R3 barman-cloud pluginName+9090); direction UNKNOWN |
| DNS53 TCP/UDP | kube-dns Service/EndpointSlices + CoreDNS Pod labels | OBSERVED (R2 kube-dns 10.96.0.10:53; R3 eps 10.244.254.65/.66) |
| Kubernetes API | default/kubernetes Service and EndpointSlices, API Node addresses, CNI mode and documented service DNAT enforcement point | OBSERVED Service+eps (R2 10.96.0.1:443→6443; R3 172.30.140.101/102/103:6443 ready); DNAT/CNI UNKNOWN |
| S3 TLS443 | canonical ObjectStore endpoint plus permitted read-only routing facts | source spec.configuration.endpointURL (objectstore-portal-db.yaml); live value UNKNOWN (base read wrong path) |
| monitoring9187 | API discovery of ServiceMonitor/PodMonitor; served resources and selectors; Prometheus Pod namespace/labels | OBSERVED not-served (R11-13 API_NOT_SERVED); no Prometheus pod (R1) → not-found |
| Portal/migrator | candidate Deployment/Job labels and ports (repository) | offline both-side tests; not runtime (NOT_CREATED) |
| Envoy xDS18000/backend8080/listener | GatewayClass/EnvoyProxy source configuration, controller and eventual dataplane labels, Service targetPorts, owning namespace | control-plane OBSERVED (R1/R2 18000); GatewayClass eg (R6); dataplane NOT_CREATED (R7/R8) |
| baseline union | all existing policies and all portal namespace workload identities | K8S netpol EMPTY (R5); EFFECTIVE union UNKNOWN (Calico + policy.networking.k8s.io served R14) |

The approved base inventory has already been executed; its 15-record artifact is
preserved with aggregate EXIT=1. Do not repeat it. The separate supplemental
collector is source-reviewed but has no operator execution approval. A later
exact-script handoff gate must specify the ten reads, hashes, permitted context,
output handling and STOP behavior. It must preserve all current UNKNOWN limits.
No traffic/failure tests, broad CIDR workarounds or new ConfigMap/host reads are
authorized. Source evidence cannot itself prove runtime DNAT/enforcement.

Offline `go test ./networkpolicy` checks the current candidate union on both
sides, name+namespace isolation, ports, protocols, migrator labels and denial of
unrelated clients. This is not CNI/runtime validation and does not close missing
monitoring/API/plugin inventory. Reconcile every row above with raw refs before
requesting the later apply gate.

D1 exact rollback inventory (only objects newly created by the future rollout):
portal/{p8c-cnpg-existing-flows,baseline-default-deny-all,baseline-allow-dns-egress,
p8c-portal-flows,p8c-migrator-flows}; envoy-gateway-system/p8c-portal-dataplane-flows.
Record preexisting names/UIDs before rollout. If any name already exists STOP;
never delete a preexisting policy. Each phase requires CNPG Ready3/3, archiving,
BSL, DNS/API/operator/monitoring status reads; degradation stops the rollout and
rolls back only UIDs created by that rollout. Rollback execution remains gated.
