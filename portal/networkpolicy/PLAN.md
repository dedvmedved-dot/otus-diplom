# P8C NetworkPolicy plan (D1) — read-only preparation, not yet applied

Live policy rollout is deferred until supply-chain (R3) and auth/pull (R4)
preconditions are ready (per D1/R2: "не вводить live policies без необходимости
deploy"). This document records candidate flows and known source facts. It does not certify the live inventory.

## Historical inventory claims — fresh raw proof required

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
| Barman plugin (cnpg-system, ref spec.plugins[].parameters.barmanObjectName) | CNPG pod / S3 (172.30.143.10:443) | svc 9090 observed; direction DB/S3 UNKNOWN | backup/WAL archiver (plugin flow UNVERIFIED) |
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

Use `inventory.py --context <approved-context> --output <new-evidence-dir>` on the
already authorized Hermes environment. It only issues fixed `kubectl get` reads
with safe projections; no exec, writes, secrets, full Pod specs or env dumps.
Missing command/access/API produces a failure record, never an empty/absent proof.
The generated JSONL covers object identity and endpoints. It cannot prove packet
DNAT enforcement by itself: attach existing CNI configuration/documentation and
read-only observed path evidence. Do not run traffic/failure tests or add broad
CIDRs to overcome missing facts. No P4/P8A/P8B qualification reruns.

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
