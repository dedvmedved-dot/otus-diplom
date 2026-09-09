# TASK-P6D-R1 — result

TASK: TASK-P6D-R1
RUN_ID: 20260909T220600Z
BASELINE: cc05c59721adb96c1707c511141d6f746cbcc1fc
MODE: NETWORK PERSISTENCE CORRECTION / EXTERNAL E2E RE-VALIDATION / VERIFIER HARDENING

## Итог: PASS

## 1. Route persistence (converted temporary -> persistent)
- Persistent route: 172.30.20.0/24 via 172.30.140.1 dev bond0.140 (proto static) on node-01/02/03.
- Mechanism: nmcli on existing bond0.140 profile (VLAN 140 Management), no new profile.
- UUIDs: node-01 9f1f26e5..., node-02 2ac0036f..., node-03 0317a359...
- ip route get 172.30.20.51: src 172.30.140.101/102/103 (correct per node).
- nmcli reload survival: route remains (proto static).
- Idempotence: first run changed=0, second run changed=0.
- Reboot test: NOT EXECUTED — NOT AUTHORIZED (nmcli persistent + reload conclusively proven).
- Default route / addresses / VLAN / bond / rp_filter: unchanged.

## 2. Declarative route playbook
ansible/playbooks/p6d-external-return-route.yml (idempotent, secret-free, narrow scope).

## 3. Durable P6D verifier hardened
- Added route check (kernel) -> P6D_EXTERNAL_RETURN_ROUTE_OK (on all 3 nodes).
- Added persistent source check (nmcli profile) -> P6D_EXTERNAL_RETURN_ROUTE_PERSISTENT.
- Fail-closed residue: replaced obj.get("items", []) with isinstance(list) assert.
- 14 isolated negative tests PASS (A-N).
- Static safety 0 mutation ops (incl nmcli/ip route). Syntax + list-tasks PASS.

## 4. External E2E re-validation (raw source evidence)
- External client atlas-1.brest.local (172.30.20.51), routed via 172.30.20.1 -> SVI 172.30.140.1.
- Gateway Accepted=True, Programmed=True; data plane Ready (digest pinned).
- LB IP 172.30.140.110 (approved pool); MetalLB L2 announcer node-03.
- HTTPRoute Accepted=True, ResolvedRefs=True.
- Internal control: HTTP 200 + P6D_R1_EXTERNAL_E2E_OK.
- Probe 1/2/3: SOURCE_IP=172.30.20.51, HTTP 200 + P6D_R1_EXTERNAL_E2E_OK (raw route evidence).
- Negative path: HTTP 404 (marker absent).

## 5. Cleanup + residue
- p6d-r1-validation deleted (NotFound). Residue counters ALL zero:
  P6D_R1_NAMESPACE_COUNT=0, GATEWAY_COUNT=0, HTTPROUTE_COUNT=0,
  LB_SERVICE_COUNT=0, ENVOY_DATAPLANE_COUNT=0, VALIDATION_RESIDUE_TOTAL=0.
- Post-cleanup external: HTTP=000, marker absent.

## 6. Final state + regression
- Kubernetes v1.36.2; Envoy 1.9.1 1/1; GatewayClass eg Accepted; MetalLB 3/3; BGP/BFD=0; kube-vip .100.
- Post P1-P5/P6B/P6C: changed=0 failed=0 unreachable=0.
- Final P6D verifier: changed=0 failed=0 unreachable=0, all 11 markers present.

Hermes НЕ присваивает статусы. Ждёт независимый GitHub Connector audit.
