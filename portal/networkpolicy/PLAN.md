# P8C NetworkPolicy plan (D1) — read-only preparation, not yet applied

Live policy rollout is deferred until supply-chain (R3) and auth/pull (R4)
preconditions are ready (per D1/R2: "не вводить live policies без необходимости
deploy"). This document records the verified inventory + planned objects.

## Verified inventory (R0, read-only)

- No NetworkPolicy exists cluster-wide (`kubectl get networkpolicy -A` -> none).
  portal namespace and envoy-gateway-system have NO default-deny baseline.
- Existing workloads/controllers in portal: CNPG operator (cnpg-system),
  postgres cluster portal-db (3 pods + barman-cloud sidecars), Barman plugin
  controller (barman-cloud), Velero (velero namespace: 4 deploy + node-agent),
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
| Barman controller (cnpg-system) | CNPG pod | 5432 | backup plugin |
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
   CNPG pods; one object containing the FULL verified ingress+egress allowlist
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
