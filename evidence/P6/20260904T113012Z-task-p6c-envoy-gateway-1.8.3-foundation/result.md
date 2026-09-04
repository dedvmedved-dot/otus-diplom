# TASK-P6C — result

TASK: TASK-P6C
RUN_ID: 20260904T113012Z
BASELINE: 74e54e39cf96f422338887d7131de2daa4dd3761
MODE: AUTHORIZED IMPLEMENTATION / GATEWAY API FOUNDATION / ENVOY GATEWAY

## Итог: PASS (Envoy Gateway 1.8.3 foundation deployed and verified)

## Artifact / supply-chain (HARD gate)
- Helm chart gateway-helm v1.8.3 OCI digest sha256:cfb34ff4266c87a394cd6be5c13607a2dd47083aef771368302eaeaa99c4a0a9
- CRD chart gateway-crds-helm v1.8.3 OCI digest sha256:99b14db0bc57c8f413023d66145a2c53e8ed47f85fe0163b675c04165ff242d4
- controller image: docker.io/envoyproxy/gateway@sha256:3c3b5b6132002462b5c652cb9f1f72f532d3c848110e669f49690d9e11d9ce6e (linux/amd64)
- envoy proxy data-plane: docker.io/envoyproxy/envoy@sha256:747460ac10544a8c7698d5d958142ffbda740e1ef1f36981b4b0e18f640658b7 (distroless-v1.38.0, linux/amd64)
- ratelimit NOT enabled (no rate limit policy).

## Install
- 16 CRDs Established=True (GatewayClass/Gateway/HTTPRoute/ReferenceGrant + Envoy CRDs).
  envoyproxies CRD required server-side apply (client-side "annotations Too long").
- Controller envoy-gateway 1/1 Ready, runtime imageID == pinned digest.
- GatewayClass eg controllerName gateway.envoyproxy.io/gatewayclass-controller, Accepted=True.

## Validation (temporary, then cleaned)
- Gateway p6c-gateway: Accepted=True, Programmed=True.
- Envoy data plane Ready, runtime imageID == envoy@sha256:747460ac... (pinned).
- Envoy LB Service type=LoadBalancer, IP 172.30.140.110 (approved MetalLB pool).
- HTTPRoute p6c-http: Accepted=True, ResolvedRefs=True.
- Internal HTTP: 200 + body "P6C_ENVOY_GATEWAY_HTTP_OK" (node-02 -> LB .110 -> Envoy -> HTTPRoute -> backend).
- Optional features zero (rate-limit/security/backendtraffic/clienttraffic/tls/tcp/udp/grpc routes = 0; no cert-manager/external-dns).

## Cleanup + final state
- validation namespace p6c-validation NotFound; Gateway=0; HTTPRoute=0; LB services=0; data plane GC'd.
- Envoy Gateway 1.8.3 controller healthy; GatewayClass eg Accepted=True.
- MetalLB 0.16.1 preserved (controller 1/1, speaker 3/3, pool exact, l2adv exact, BGP/BFD=0).
- kube-vip .100 preserved (svc_enable=false).
- images.lock updated with factual envoy-gateway + envoy-proxy-dataplane entries.

## Durable P6C verifier
ansible/playbooks/p6c-final-readonly-verify.yml — read-only, fail-closed.
Markers: P6C_GATEWAY_API_CRDS_OK, P6C_CONTROLLER_READY, P6C_CONTROLLER_IMAGE_OK,
P6C_GATEWAYCLASS_ACCEPTED, P6C_METALLB_INTEGRATION_OK, P6C_P6B_PRESERVED,
P6C_NO_FLOATING_IMAGES, P6C_IMAGES_LOCK_OK, P6C_VALIDATION_RESIDUE_ZERO,
P6C_FINAL_READONLY_VERIFIER_PASS.
Final run: changed=0 failed=0 unreachable=0, exit 0.

## Regression
Post P1-P5: changed=0 failed=0 unreachable=0.
Post P6B: changed=0 failed=0 unreachable=0 (P6B_FINAL_READONLY_VERIFIER_PASS).

## Note
Envoy Gateway v1.8 compatibility matrix lists Kubernetes v1.32-v1.35; this
cluster is v1.36.2. Install succeeded and all gates PASS, but this is recorded
as a factual matrix divergence for Architect awareness (not a P6C blocker per task).

EXTERNAL E2E: DEFERRED TO P6D.

Hermes НЕ присваивает статусы. Ждёт независимый GitHub Connector audit.
