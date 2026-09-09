# TASK-P6D — result

TASK: TASK-P6D
RUN_ID: 20260908T174149Z
BASELINE: a23ba308511c9ba15d1d81c9e0fa6fd7d33b5510
MODE: EXTERNAL END-TO-END INTEGRATION ACCEPTANCE

## Итог: PASS (external E2E proven from real non-Kubernetes client via routed path)

## External client (valid)
- atlas-1.brest.local (172.30.20.51), Astra Linux 1.8, physical server (Proxmox), VLAN 21.
- NOT a Kubernetes node/pod/synthetic. Reachable to VLAN140 via routed path (L3).
- Route fix: SVI 172.30.140.1 (network engineer) + node-side route
  172.30.20.0/24 via 172.30.140.1 (Owner-authorized) to fix strict rp_filter drop.

## Validation (temporary, cleaned)
- Gateway p6d-gateway: Accepted=True, Programmed=True.
- Envoy data plane Ready (envoy@sha256:9e24a3b4... pinned; shutdown-manager gateway@sha256:2999d87c...).
- LB Service type=LoadBalancer, IP 172.30.140.110 (approved MetalLB pool .110-.119).
- MetalLB L2 announcement: serviceAnnounced .110 protocol=layer2, announcer node-01 (speaker-xwxtr).
- HTTPRoute p6d-http: Accepted=True, ResolvedRefs=True.
- Internal control (node-02): HTTP 200 + P6D_EXTERNAL_E2E_OK.

## External E2E (mandatory acceptance)
- Probe 1 (172.30.20.51): HTTP 200 + P6D_EXTERNAL_E2E_OK (14:34:28 UTC)
- Probe 2 (172.30.20.51): HTTP 200 + P6D_EXTERNAL_E2E_OK (14:34:52 UTC)
- Probe 3 (172.30.20.51): HTTP 200 + P6D_EXTERNAL_E2E_OK (14:34:56 UTC)
- Negative path /p6d-negative-not-found: HTTP 404 (marker absent)

## Full path attribution
external client 172.30.20.51 -> 172.30.20.1 (L3) -> SVI 172.30.140.1
-> MetalLB L2 (announcer node-01) -> LB 172.30.140.110
-> Envoy pod envoy-p6d-validation-p6d-gateway-b6c03a20 (node-01, 10.244.190.21)
-> HTTPRoute p6d-http -> backend svc p6d-backend (10.102.212.144:8080)
-> backend pod p6d-backend-5d5c9c48f-chpqh (node-03, 10.244.254.82)

## Cleanup + post-cleanup
- p6d-validation NotFound; Gateway=0; HTTPRoute=0; LB services=0; data plane GC'd.
- Post-cleanup external test: HTTP=000, MARKER_ABSENT (validation path gone).

## Final production state
- Kubernetes v1.36.2; Envoy 1.9.1 controller 1/1; GatewayClass eg Accepted=True.
- MetalLB 0.16.1 controller 1/1, speaker 3/3, BGP/BFD=0.
- kube-vip .100 (svc_enable=false) preserved.
- P6D validation residue = 0.

## Durable P6D verifier
ansible/playbooks/p6d-final-readonly-verify.yml (read-only, fail-closed, 9 markers).
Static safety 0 mutation ops. Final run changed=0 failed=0 unreachable=0, exit 0.
Post P1-P5 / P6B / P6C: all changed=0 failed=0 unreachable=0.

## Note
Node-side route 172.30.20.0/24 via 172.30.140.1 added temporarily (ip route add).
Not yet persisted via nmcli — flagged as follow-up for production permanence.

Hermes НЕ присваивает статусы. Ждёт независимый GitHub Connector audit.
