# P8C-RV02-OFFLINE-ROLLOUT-DECISION-R1-RESIDUAL — documentary source extractions

Date: 2026-11-02 (UTC). Offline verification of repository sources referenced in the decision.
No live/SSH/DNS/registry; static file/blob extraction only.

## Extracted facts (file → blob → fact)

| # | File | Blob | Extracted fact (verbatim-consistent) |
|---|---|---|---|
| 1 | ansible/playbooks/files/calico-v3.32.0.yaml | 21ea9b4b163305ea479bc7708965104465ffc716 | CalicoNodeStatus.status = agent(birdV4/birdV6), bgp, lastUpdated, routes — no backend field |
| 2 | same | 21ea9b4b… | IPPool = spec (cidr/encapsulation/nat/…) — no S3-reachability status |
| 3 | portal/manifests/networkpolicy.yaml | fccb8432135a18f8b7099e131471a48808df1ed7 | candidate has: Barman `app=barman-cloud`→5432; API `172.30.140.0/24`→6443; S3 `172.30.143.10/32`→443; DNS podSelector kube-system/k8s-app=kube-dns; existing-flows policyTypes [Ingress,Egress] |
| 4 | portal/manifests/gateway.yaml | 1e1f48a3c6d03c4558f4b4c3cca24bc12c22b763 | Gateway portal-gateway listener https:443 HTTPS hostname portal.demo-pak.test TLS Terminate certRef portal-ui-tls allowedRoutes Same; HTTPRoute portal → Service portal:80 |
| 5 | portal/manifests/deployment.yaml | 2cb27165330fe4b6772af3a06a1940d661efc72f | Deployment portal label app.kubernetes.io/name=pak-portal container http=8080 mgmt=8081; Service portal 80→http; Job migrator label pak-portal-migrator |
| 6 | manifests/envoy-gateway/p6c-envoy-gateway-values.yaml | 6b1ea60d8e4120016f5675771c46f92f96dadc0e | Envoy Gateway 1.9.1; provider.type Kubernetes; controller gateway.envoyproxy.io/gatewayclass-controller; service.type ClusterIP (control-plane) |
| 7 | manifests/envoy-gateway/p6c-gatewayclass.yaml | — | GatewayClass eg, controllerName gateway.envoyproxy.io/gatewayclass-controller |
| 8 | evidence/P6/20260909T232839Z-…/25a-loadbalancer-service-raw.json | — | generated Gateway Service: type LoadBalancer, externalTrafficPolicy Local, allocateLoadBalancerNodePorts true, healthCheckNodePort set, port 80→targetPort 10080, selector component=proxy/managed-by=envoy-gateway/name=envoy + owning-gateway-{name,namespace}, MetalLB pool annotation, status.loadBalancer.ingress.ip ipMode VIP |
| 9 | Envoy Gateway v1.9.1 internal/gatewayapi/listener.go | 3d8376553ad570ab22476a7d163053eaf32d3883 | servicePortToContainerPort: privileged port → port+10000 (wellKnownPortShift) |
| 10 | evidence/P7/…/15-dns-after-demo-pak.txt | 89cd2fe653f09924ede7adcd4a90bbaf515211cc | s3-backup.demo-pak.test → 172.30.143.10 |
| 11 | evidence/P7/…/16-bind-authority-check.txt | 680e504cf1027789d124e8c8bf7b29121e24a23e | BIND authority @172.30.143.10 |
| 12 | evidence/P7/…/09-live-dns-s3-contract.txt | 078398f07263bae41e1f824b609edc7bd03ec24b | CoreDNS forward demo-pak.test → 172.30.143.10; POD_DNS_TO_S3/POD_TO_S3_PATH accepted |
| 13 | portal/networkpolicy/supplemental-design.md | a4de674f9b98f7ecc2dc063db15ccfca7195484b | §4: sidecar (in-pod) backup/WAL/S3; controller=9090 RPC (cnpg-system); no controller→DB5432/S3 inference; §5: address-rewrite order implementation-dependent |

## Verification method
Static reads (`git show <blob>` / `read_file`) of the pinned files; facts are cross-checked against the
review-provided blobs. No unit tests fabricated; no runtime assertion. This supports the decision
document §0 dictionary and §1–§3, not any live claim.
