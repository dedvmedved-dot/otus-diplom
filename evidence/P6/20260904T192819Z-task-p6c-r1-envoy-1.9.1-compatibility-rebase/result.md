# TASK-P6C-R1 — result

TASK: TASK-P6C-R1
RUN_ID: 20260904T192819Z
BASELINE: 4dfbac45578b5129c5eb3fa4fafb49ea16c1c112
MODE: ARCHITECTURE BASELINE CORRECTION / COMPATIBILITY REBASE / VERIFIER HARDENING

## Итог: PASS (Envoy Gateway rebased 1.8.3 -> 1.9.1, k8s v1.36.2 compatible)

## Compatibility (Architect decision validated)
Kubernetes v1.36.2 KEEP (no downgrade).
Envoy Gateway v1.8 does NOT support k8s v1.36; v1.9 DOES (matrix v1.9: k8s v1.33-v1.36).
K8S_1_36_COMPATIBLE_WITH_ENVOY_GATEWAY_1_9 = TRUE.

## Artifact / supply-chain (HARD gate, immutable)
- gateway-helm v1.9.1 OCI digest sha256:91bae9aedb91ab34731e987afe01a3ccf454393015abeca705eea8ee15553e86
- gateway-crds-helm v1.9.1 OCI digest sha256:45693764cab8aae661bc32f0f706f5c8e5aaa9a151b6d03fb0a468cc535a155c
- controller docker.io/envoyproxy/gateway@sha256:2999d87c3a2b3e890e0ee1a2b11a159b60963aadb2cbb9f2c0a49e0197df3c72 (linux/amd64)
- envoy proxy docker.io/envoyproxy/envoy@sha256:9e24a3b459b463dd37e116a0f46d2abfcb6a1cb9897d87e85cf2ee25edbe373b (distroless-v1.39.0, linux/amd64)
- ratelimit NOT enabled.

## Upgrade
- CRD set 1.8.3 (16) -> 1.9.1 (18 CRDs, +tcproutes +udproutes), all Established=True.
  server-side apply --force-conflicts for ValidatingAdmissionPolicy field ownership.
- Controller 1.8.3 -> 1.9.1: 1/1 Ready, runtime imageID == v1.9.1 digest.
- GatewayClass eg Accepted=True (controllerName unchanged).

## Validation (temporary, then cleaned)
- Gateway p6c-r1-gateway: Accepted=True, Programmed=True.
- Envoy data plane Ready, imageID == envoy@sha256:9e24a3b4... (distroless-v1.39.0).
- LB Service type=LoadBalancer, IP 172.30.140.110 (approved MetalLB pool).
- HTTPRoute p6c-r1-http: Accepted=True, ResolvedRefs=True.
- Internal HTTP: 200 + body "P6C_R1_ENVOY_GATEWAY_1_9_1_OK" (node-02 -> LB .110 -> Envoy 1.9.1 -> HTTPRoute -> backend).
- Optional features zero; no cert-manager/external-dns.

## Cleanup + final state
- p6c-r1-validation NotFound; Gateway=0; HTTPRoute=0; LB services=0; data plane GC'd.
- Envoy 1.9.1 controller 1/1; GatewayClass eg Accepted=True.
- MetalLB 0.16.1 preserved (controller 1/1, speaker 3/3, BGP/BFD=0).
- kube-vip .100 preserved (svc_enable=false).
- versions.lock envoy_gateway=1.9.1; images.lock rebased to v1.9.1 digests.

## Durable verifier (hardened, fail-closed)
ansible/playbooks/p6c-final-readonly-verify.yml — rewritten:
- Gateway + HTTPRoute residue now fail-closed (query failure / malformed JSON / non-list / nonzero -> FAIL).
- Added k8s v1.36.2, compatibility, versions.lock, separate BGP/BFD markers.
- 17 markers all present. Final run changed=0 failed=0 unreachable=0 exit 0.
- 10 fail-closed negative tests PASS (A-J). Static safety audit 0 mutation ops.

## Regression
Post P1-P5: changed=0 failed=0 unreachable=0.
Post P6B: changed=0 failed=0 unreachable=0 (P6B_FINAL_READONLY_VERIFIER_PASS).

EXTERNAL E2E: DEFERRED TO P6D.

Hermes НЕ присваивает статусы. Ждёт независимый GitHub Connector audit.
