# P8C-RV02-OFFLINE-ROLLOUT-DECISION-R1-FINAL — documentary source extractions

Date: 2026-11-02 (UTC). Offline verification of repository/pinned sources referenced in the final
decision document. No live/SSH/DNS/registry; static path/blob extraction only (blobs from the
review-provided source-facts.json and repository tree).

## Extracted facts (path → blob → fact)

| # | Path | Blob | Extracted fact |
|---|---|---|---|
| 1 | ansible/playbooks/files/calico-v3.32.0.yaml | 21ea9b4b163305ea479bc7708965104465ffc716 | CalicoNodeStatus.status = agent(birdV4/birdV6), bgp, lastUpdated, routes — no backend; IPPool = spec only |
| 2 | portal/manifests/networkpolicy.yaml | fccb8432135a18f8b7099e131471a48808df1ed7 | candidate: Barman `app=barman-cloud`→5432; API `172.30.140.0/24`→6443; S3 `172.30.143.10/32`→443; DNS podSelector; existing-flows [Ingress,Egress] |
| 3 | portal/manifests/gateway.yaml | 1e1f48a3c6d03c4558f4b4c3cca24bc12c22b763 | Gateway portal-gateway https:443 HTTPS hostname portal.demo-pak.test TLS Terminate certRef portal-ui-tls allowedRoutes Same; HTTPRoute → Service portal:80 |
| 4 | portal/manifests/deployment.yaml | 2cb27165330fe4b6772af3a06a1940d661efc72f | Deployment portal label pak-portal http=8080 mgmt=8081; Service 80→http; Job migrator pak-portal-migrator |
| 5 | manifests/envoy-gateway/p6c-envoy-gateway-values.yaml | 6b1ea60d8e4120016f5675771c46f92f96dadc0e | Envoy Gateway 1.9.1; provider.type Kubernetes; controller gatewayclass-controller; control-plane service ClusterIP |
| 6 | manifests/envoy-gateway/p6c-gatewayclass.yaml | 80b1d683a7193fd1cebc5d29d6f6b0a671f5d1b6 | GatewayClass eg, controllerName gateway.envoyproxy.io/gatewayclass-controller |
| 7 | Envoy Gateway v1.9.1 internal/gatewayapi/listener.go | 3d8376553ad570ab22476a7d163053eaf32d3883 | servicePortToContainerPort: privileged → port+10000 |
| 8 | evidence/P6/.../25a-loadbalancer-service-raw.json | b71e1453e890bab06b90bdaa697aa18e7c9124c4 | generated Service: LoadBalancer, externalTrafficPolicy Local, nodePort/healthCheckNodePort, port 80→10080, selector component/managed-by/name + owning-{name,namespace}, MetalLB pool, LB ip |
| 9 | evidence/P7/.../15-dns-after-demo-pak.txt | 89cd2fe653f09924ede7adcd4a90bbaf515211cc | s3-backup.demo-pak.test → 172.30.143.10 |
| 10 | evidence/P7/.../16-bind-authority-check.txt | 680e504cf1027789d124e8c8bf7b29121e24a23e | BIND authority @172.30.143.10 |
| 11 | evidence/P7/.../09-live-dns-s3-contract.txt | 078398f07263bae41e1f824b609edc7bd03ec24b | CoreDNS forward demo-pak.test → 172.30.143.10; POD_DNS_TO_S3/POD_TO_S3_PATH |
| 12 | portal/networkpolicy/supplemental-design.md | a4de674f9b98f7ecc2dc063db15ccfca7195484b | §4 Barman-роли (sidecar in-pod S3; controller 9090; нет controller→DB5432/S3); §5 rewrite order implementation-dependent |
| 13 | cloudnative-pg/cloudnative-pg v1.30.1 api/v1/cluster_types.go | 891424dde2287deffcf22b88683f4d8f96376993 | `ReadyInstances int json:"readyInstances,omitempty"`; printcolumn Ready=.status.readyInstances; firstRecoverabilityPoint deprecated/not-set for backup plugins |
| 14 | cloudnative-pg/plugin-barman-cloud v0.13.0 api/v1/objectstore_types.go | 928d52c982b56f11b2eb00f4f88dea4e75916e12 | firstRecoverabilityPoint = earliest recovery point, not last archived WAL |
| 15 | docs/architecture/P8B_POSTGRES_BACKUP_CONTRACT.md | b1e2b51ff46bda7f172432ce43713b7d1a7415c0 | archive_timeout=300s |
| 16 | portal/internal/httpapi/server.go | c804bf231fc68bb0cfed1b4a0c058a1b938345d4 | Handler: auth before route |
| 17 | portal/internal/auth/auth.go | 62c7a0586895bfe2a03fd8207daf5641dc664f0c | Portal Basic Auth verifier |
| 18 | https://metallb.io/concepts/layer2/ | — (doc) | L2: node announces VIP; K8s Service forwards to endpoints |

## Verification method
Static reads (`git show <blob>` / `read_file`) of the pinned files; facts cross-checked against the
review-provided source-facts.json. No unit tests fabricated; no runtime assertion. Supports the
decision document §0 dictionary and §1–§5, not any live claim.
