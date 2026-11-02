# P8C candidate delta (NP-01..04) — before/after rules

## NP-01 — API tuples
- **before** (existing-flows + portal-flows egress): `to: 172.30.140.0/24; ports: 6443`.
- **after** (each policy): two separate egress rules:
  1. `to: 10.96.0.1/32; ports: TCP 443`;
  2. `to: 172.30.140.101/32, 172.30.140.102/32, 172.30.140.103/32; ports: TCP 6443`.
- Effect: no cross-product (10.96.0.1:6443 и endpoint:443 запрещены), no VIP .100, no /24, no UDP.
- FLOW-ID: API-6443.

## NP-02 — Barman controller→DB5432
- **before**: ingress peer `cnpg-system` + `app=barman-cloud` → TCP 5432 (+ stale comment).
- **after**: removed. Control RPC 9090 and per-instance sidecar S3 are separate (supplemental-design §4);
  sidecar/CNPG Pod→172.30.143.10/32:443 preserved. FLOW-ID: BAR-5432 legacy.

## NP-03 — dataplane 5-label identity
- **before**: dataplane podSelector и Portal ingress peer = 2 owning labels only.
- **after**: 5 labels — `app.kubernetes.io/component=proxy`, `app.kubernetes.io/managed-by=envoy-gateway`,
  `app.kubernetes.io/name=envoy`, `gateway.envoyproxy.io/owning-gateway-name=portal-gateway`,
  `gateway.envoyproxy.io/owning-gateway-namespace=portal`. Portal ingress peer: namespace
  `envoy-gateway-system` AND podSelector (single AND peer). FLOW-ID: ENV-XDS-18000, ENV-BACK-8080, ENV-LISTENER.

## NP-04 — preserved (unchanged)
CNPG peer 5432/8000, operator→8000, Portal→5432/9187, migrator→5432, DNS UDP/TCP 53,
dataplane→xDS 18000 + Portal 8080. mgmt 8081 not opened.
