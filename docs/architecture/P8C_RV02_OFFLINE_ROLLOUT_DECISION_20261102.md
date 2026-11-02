# P8C-RV02-OFFLINE-ROLLOUT-DECISION-R1-RESIDUAL — закрытие RR-01…03

Дата: 2026-11-02 (UTC). Исполнитель: PRIMARY HERMES. Только offline-доработка документов по
review f7bf263. Collector 9/9 (c872eed) и source eed114e приняты, не переоткрываются.
Никаких live/SSH/DNS/registry-проб, apply, CI, production.

Authority: docs/architecture/P8C_RV02_REVIEW_f7bf263_20261102.md (REVIEW_HEAD=f7bf263).
```text
AUTHORIZED_READ_SET_COMPLETE=YES · FLOW_MATRIX_COMPLETE=NO · EFFECTIVE_POLICY_UNION=UNKNOWN
NETPOL_APPROVED_FOR_APPLY=NO · CI/PRODUCTION=NOT_AUTHORIZED · P8C=NOT_FINAL_ACCEPTED
```

## 0. Словарь источников и селекторов (однозначные ссылки)

| Ключ | Файл / объект | Blob | Record/факт |
|---|---|---|---|
| R1/R2/R3/R5/R6/R7/R8/R11-13/R14/R15 | evidence/P8/20261026T173244Z-p8c-rv02-live-inventory/inventory.jsonl | — | записи R* (base, 2026-10-26) |
| C1/S1/S2 | evidence/P8/20261027T140000Z-p8c-rv02-phase2-live/result/supplemental.jsonl | — | C1/S1/S2 (Phase-2) |
| F-* (9 чтений) | evidence/P8/20261102T094000Z-p8c-rv02-podlist-onerun/followup.jsonl | — | 2026-11-02T09:35:24–25Z |
| P7-DNS | evidence/P7/20261019T030033Z-…/15-dns-after-demo-pak.txt | 89cd2fe653f09924ede7adcd4a90bbaf515211cc | s3-backup.demo-pak.test → 172.30.143.10 |
| P7-BIND | evidence/P7/20261019T030033Z-…/16-bind-authority-check.txt | 680e504cf1027789d124e8c8bf7b29121e24a23e | BIND authority @172.30.143.10 |
| P7-S3 | evidence/P7/20261019T113205Z-…/09-live-dns-s3-contract.txt | 078398f07263bae41e1f824b609edc7bd03ec24b | CoreDNS forward + POD_DNS_TO_S3/POD_TO_S3_PATH |
| CALICO | ansible/playbooks/files/calico-v3.32.0.yaml | 21ea9b4b163305ea479bc7708965104465ffc716 | CalicoNodeStatus/IPPool schema |
| BARMAND | portal/networkpolicy/supplemental-design.md | a4de674f9b98f7ecc2dc063db15ccfca7195484b | §4 Barman-роли, §5 DNAT |
| NP-YAML | portal/manifests/networkpolicy.yaml | fccb8432135a18f8b7099e131471a48808df1ed7 | candidate policy |
| GW-YAML | portal/manifests/gateway.yaml | 1e1f48a3c6d03c4558f4b4c3cca24bc12c22b763 | Gateway/HTTPRoute |
| DEP-YAML | portal/manifests/deployment.yaml | 2cb27165330fe4b6772af3a06a1940d661efc72f | Deployment/Service/Job |
| EG-VALUES | manifests/envoy-gateway/p6c-envoy-gateway-values.yaml | 6b1ea60d8e4120016f5675771c46f92f96dadc0e | Envoy Gateway 1.9.1, provider Kubernetes |
| EG-GWC | manifests/envoy-gateway/p6c-gatewayclass.yaml | — | GatewayClass `eg`, controller gateway.envoyproxy.io/gatewayclass-controller |
| EG-SRC | Envoy Gateway v1.9.1 (commit 0260554f…) internal/gatewayapi/listener.go | 3d8376553ad570ab22476a7d163053eaf32d3883 | servicePortToContainerPort: privileged → port+10000 |
| P6-LBSVC | evidence/P6/20260909T232839Z-…/25a-loadbalancer-service-raw.json | — | type LoadBalancer, externalTrafficPolicy Local, port 80→10080, MetalLB pool |

Селекторы: ns-label `kubernetes.io/metadata.name` (на Namespace); owning-label
`gateway.envoyproxy.io/owning-gateway-name` + `gateway.envoyproxy.io/owning-gateway-namespace`.

## 1. RR-01 — законченный ingress-дизайн (OD-03)

**Exposure model (выбрана одна модель, source-derived + P6 runtime-эталон):**
- Provider: Kubernetes (`config.envoyGateway.provider.type: Kubernetes`, EG-VALUES); GatewayClass `eg`
  controller `gateway.envoyproxy.io/gatewayclass-controller` (EG-GWC).
- Gateway `portal-gateway` (namespace `portal`), listener `https` port 443, protocol HTTPS, hostname
  `portal.demo-pak.test`, TLS mode Terminate, certificateRef `portal/portal-ui-tls`, allowedRoutes Same
  (GW-YAML). HTTPRoute `portal` → backendRef Service `portal` port 80 → container `http` 8080 (DEP-YAML).
- **Port translation** (EG-SRC): privileged 443 → container 10443 (wellKnownPortShift=10000).
  Сгенерированный Service: `port=443`, `targetPort=10443`. (Не выдавать 443→container443.)
- **Сгенерированный Service** (по P6-LBSVC эталону того же инфраструктурного стека): type
  LoadBalancer, `externalTrafficPolicy: Local` (source-address клиента сохраняется до Envoy pod),
  `allocateLoadBalancerNodePorts: true`, `healthCheckNodePort` назначается k8s, MetalLB
  (metallb-system) выделяет VIP из ingress-pool (P6-LBSVC: `metallb.io/ip-allocated-from-pool`,
  `status.loadBalancer.ingress.ip`, ipMode VIP).
- **Dataplane Pod**: namespace `envoy-gateway-system`, labels `app.kubernetes.io/component=proxy`,
  `app.kubernetes.io/managed-by=envoy-gateway`, `app.kubernetes.io/name=envoy`,
  `gateway.envoyproxy.io/owning-gateway-name=portal-gateway`,
  `gateway.envoyproxy.io/owning-gateway-namespace=portal` (P6-LBSVC selector, применённый к нашему Gateway).

**Ingress boundary (выбрана L7-граница, не dataplane NetPol):**
Внешний клиент → MetalLB VIP:443 → NodePort → EnvoyProxy pod:10443 (TLS Terminate, hostname
`portal.demo-pak.test`) → backend Service `portal:80` → Pod container 8080. Контроль доступа —
**Gateway/HTTPRoute L7** (TLS + hostname + route match), НЕ dataplane NetworkPolicy. Dataplane
policy остаётся `policyTypes=[Egress]` (ingress этим объектом НЕ ограничивается — это корректно,
не ошибка). Namespace-wide deny в envoy-gateway-system НЕ вводится.

**Пробе/health-check (разделены):**
- kubelet probes (Portal): startup/readiness/liveness на mgmt 8081 (`/startupz` `/readyz` `/livez`) —
  kubelet→Pod, не через dataplane.
- LB health check: MetalLB L2 не выполняет health-проб; `healthCheckNodePort` (P6-LBSVC) предназначен
  для внешних cloud-LB, в MetalLB L2 не используется.
- Active backend health-check: в принятой конфигурации отсутствует (не изобретать).

**PLANNED generated-runtime (точные будущие field-checks, НЕ угадывать):**
имя сгенерированного Service (`envoy-portal-portal-gateway-…`), его `uid`, `status.loadBalancer.ingress.ip`,
`healthCheckNodePort`, `spec.ports[].targetPort` (должен быть 10443) — проверяются в execute-gate
точными reads (см. §8 PR-5), не в этом документе.

## 2. RR-02 — S0–S4 с условным baseline, union-aware rollback и реальными проверками

**S0 (исходное состояние, условное — не выдавать срез за current):**
Ожидается: CNPG Portal кластер Ready, оператор в cnpg-system reconcile-без ошибок, kube-dns
EndpointSlices ready, F-NP (Calico NetworkPolicy) пуст на срезе 09:35Z. Ограничение: F-NP — только
`crd.projectcalico.org/v1` NetworkPolicy; networking.k8s.io NetworkPolicy, Calico GNP/CNP и прочий
policy-union не доказаны пустыми на текущий момент. **Freshness precheck** (§8 PR-6) сверяет этот
union; любое отличие от ожидаемого → STOP.

**Последовательность операций и union:**

| Шаг | Операция | Состояние/union после | Rollback (UID-precondition на каждое удаление) |
|---|---|---|---|
| S0 | — | baseline: CNPG/др. portal Pods без наших NetPol | — |
| S1 | apply p8c-cnpg-existing-flows (Ingress+Egress) | CNPG Pods изолированы по full-allowlist; др. portal Pods не ограничены | delete UID(existing-flows) → S0 |
| S2a | apply baseline-default-deny-all (podSelector {}) | union: CNPG=existing-flows (полный) ∩ default-deny (не сужает, т.к. existing-flows полный); др. portal Pods=default-deny (всё закрыто) | delete UID(default-deny) → S1 |
| S2b | apply baseline-allow-dns-egress (podSelector {}, Egress) | др. portal Pods=default-deny + dns-egress; CNPG=existing-flows (не сужается) | delete UID(allow-dns-egress) → S2a |
| S3 | apply p8c-portal-flows + p8c-migrator-flows (вместе с созданием workloads) | Portal/migrator Pods получают allowlist | delete UID(portal-flows)+UID(migrator-flows) → S2b; workloads — отдельный deployment-gate (ниже) |
| S4 | apply p8c-portal-dataplane-flows (envoy-gateway-system) | dataplane egress allowlist; внешний трафик ещё не допущен до успешной S4-проверки | delete UID(dataplane-flows) → S3; внешний трафик — снять через L7/Gateway порядок ниже |

**Rollback-порядок (обратный, union-aware):** S4→S3→(S2b→S2a)→S1→S0. Критично: **baseline-default-deny-all
снимать ДО existing-flows** — удаление только existing-flows при оставшемся default-deny оставит CNPG
под default-deny (без egress) и сломает API/DNS/S3. Также `baseline-allow-dns-egress` — отдельный
selecting policy; его удаление ДО default-deny не восстанавливает состояние. Каждый шаг — UID-precondition:
объект отсутствовал до rollout, UID записан после создания, повторная сверка перед удалением; mismatch → STOP.

**Workload-разделение (S3):** создание/остановка Portal Deployment, migrator Job, Gateway/HTTPRoute —
отдельный deployment-gate, НЕ NetPol/doc-gate. NetPol-rollback НЕ удаляет workloads; если требуется
остановить созданные Portal/Job/Gateway, это отдельная зависимость deployment-gate с собственным
безопасным порядком (сначала снять внешний трафик L7, затем workloads, затем их NetPol). Существующие
CNPG/controller/Velero/cert-manager/MetalLB не трогать.

**Pre/post checks (наблюдаемые, без exec/log/proxy; окно/sвезжесть/исход):**

| Стадия | Проверка (точный object/field) | Ожидание | Окно | Freshness | Исход при недоступности/таймауте | Доказывает НЕ |
|---|---|---|---|---|---|---|
| все | `get clusters.postgresql.cnpg.io/portal-db -n portal` → `.status.conditions[type=Ready].status` и `.status.instances`/`.status.instancesReady` | Ready=True, instances=instancesReady=3 | 60s | <30s | rollback текущей стадии; STOP | не доказывает DNS/API/S3-путь из Pod |
| S1..S4 (S3-прокси) | `.status.firstRecoverabilityPoint` + `.status.conditions[type=ContinuousArchiving].status` | firstRecoverabilityPoint продвигается, ContinuousArchiving=True | 120s | <60s | rollback; STOP | S3-доступ sidecar = прокси через архив/WAL, не прямой ICMP/HTTP |
| S1..S4 (operator) | `.status.conditions` (Cluster) — отсутствие error; operator Pod Ready (cnpg-system) | нет error-condition; operator Ready | 60s | <30s | rollback; STOP | operator→API доступ ≠ Pod→API |
| S1..S4 (DNS backend) | `get endpointslices -n kube-system -l kubernetes.io/service-name=kube-dns` → `endpoints[].conditions.ready` | все ready=true | 30s | <30s | rollback; STOP | DNS backend up ≠ CNPG Pod достигает 53 |
| S3 | `get deployment/portal -n portal` → `.status.readyReplicas` + readinessProbe (`/readyz` mgmt 8081) | readyReplicas=1 (probe отражает DB-связь) | 60s | <30s | rollback S3; STOP | не доказывает S3/API из Portal |
| S4 | `get gateway/portal-gateway -n portal` → `.status.conditions[type=Accepted/Programmed]`; сгенерированный Service `.status.loadBalancer.ingress.ip` | Accepted/Programmed=True, LB IP назначен | 120s | <60s | rollback S4; STOP | не доказывает end-to-end внешний доступ |

Idle/no-progress НЕ превращать ни в PASS, ни автоматически в отказ: зафиксировать как неопределённый
результат, который блокирует дальнейший rollout (STOP до разрешения). Backup/restore/PITR/failover и
destructive probes НЕ запускать повторно. Ready3/3 и старый LastBackupSucceeded=True не подменяют
живую доступность.

## 3. RR-03 — точные selectors/provenance и исполнимые proposals

Исправления точности:
- namespace-label = `kubernetes.io/metadata.name` (не `k8s.io/metadata.name`); owning-namespace =
  `gateway.envoyproxy.io/owning-gateway-namespace`.
- PLANNED-строки ссылаются на source-manifest (DEP-YAML/GW-YAML), НЕ на выдуманный runtime record/time.
- «контроллер→DB/S3» формулируется как «необходимость такого permission НЕ установлена, в дизайн не
  включается» — не как доказанное отсутствие трафика.

**14-flow (та же, что в R1, с точными ссылками на §0-словарь):** 14 строк сохранены из R1 §6 с
исправленным namespace-label; candidate delta (Barman controller→5432, API /24) остаётся NOT_APPROVED.
(Полная таблица не дублируется здесь — она в R1 §6, ссылки сверены со словарём §0.)

**PR-3 (API endpoint-tuple freshness) — исполнимый proposal:**
`kubectl get endpointslices.discovery.k8s.io -n default -l kubernetes.io/service-name=kubernetes`
(точный GVR + service-name selector), проекция `endpoints[].addresses[]` + `ports[].port`,
scope default-namespace, single GET, no pagination; error → STOP. Проверяет свежесть endpoint-tuple
(172.30.140.101/102/103:6443), НЕ доказывает active enforcement. Выполняется только в execute-gate.

**PR-4 (S3 freshness) — честный выбор:**
Свежий факт S3-достижимости из Pod НЕ получить без exec/log (запрещено). Поэтому: (a) если нужна
свежая проверка, она требует отдельного runtime-допуска (source=CNPG Pod, qname=s3-backup.demo-pak.test,
type=A, resolver=10.96.0.10, timeout/attempts, allowlisted output, error→STOP, путь Pod≠node); (b) без
такого допуска факт остаётся **stale** (P7 2026-10-19) и в execute-gate ставится STOP-прекондиция на
сверку. Не предлагать «не новый DNS-проб» без действия.

**PR-5 (generated-runtime dataplane, S4) — proposal:**
`kubectl get service -n envoy-gateway-system -l gateway.envoyproxy.io/owning-gateway-name=portal-gateway`
(поле `spec.type`, `spec.externalTrafficPolicy`, `spec.ports[].port`/`.targetPort` (ожидание 10443),
`status.loadBalancer.ingress.ip`, `uid`). Scope envoy-gateway-system, single GET; error → STOP.

**PR-6 (S0 baseline freshness) — proposal:**
Сверка union на текущий момент: `get networkpolicies.networking.k8s.io -A`, `get networkpolicies.crd.projectcalico.org -A`,
`get globalnetworkpolicies`, `get clusternetworkpolicies`, `get felixconfigurations`, `get tiers`.
Проекция имени/namespace/UID/selectors; error → STOP. Проверяет исходное состояние S0, не запускает traffic.

## 4. Авторский vs Architect статус (не выдавать RESOLVED за Architect)

- **AUTHOR_PROPOSAL** (настоящий документ): RR-01 модель, RR-02 rollback/проверки, RR-03 selector/proposal —
  это авторское проектное предложение, НЕ принятое Architect-решение.
- **ARCHITECT_ACCEPTED**: только то, что зафиксировано в review c872eed/b5d8cab/f7bf263
  (9/9 сбор, удаление PR-1/PR-2, P7 historical S3, /32 вместо /24 как offline-кандидат, UID-precondition).
- PLAN.md / flow-matrix.md / gaps.md синхронизированы с этим разделением.

## 5. Итог
```text
TASK=P8C-RV02-OFFLINE-ROLLOUT-DECISION-R1-RESIDUAL
RR-01=RESOLVED (ingress модель: LB+MetalLB L2, Local, 443→10443, L7-граница)
RR-02=RESOLVED (условный S0, union-aware S1..S4, UID-safe rollback, заполненные pre/post checks)
RR-03=RESOLVED (namespace-label, словарь источников, executable PR-3..6, автор/архитектор разделены)
AUTHOR_PROPOSAL (не Architect-accepted): все проектные выводы выше
AUTHORIZED_READ_SET_COMPLETE=YES · FLOW_MATRIX_COMPLETE=NO · EFFECTIVE_POLICY_UNION=UNKNOWN
NETPOL_APPROVED_FOR_APPLY=NO · CI/PRODUCTION=NOT_AUTHORIZED · P8C=NOT_FINAL_ACCEPTED
```
STOP для Architect review. Candidate policy YAML не изменялся.
