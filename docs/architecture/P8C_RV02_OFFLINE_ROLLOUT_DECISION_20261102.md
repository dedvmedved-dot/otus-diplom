# P8C RV-02 — принятый offline rollout design с runtime-ограничениями

Дата: 2026-11-02. Авторский пакет PRIMARY HERMES 1b32e4d проверен и документально нормализован Architect.
Приёмка: docs/architecture/P8C_RV02_ACCEPTANCE_1b32e4d_20261102.md.
OFFLINE_DESIGN=ACCEPTED_WITH_RUNTIME_LIMITS; EXECUTION_GATE_READY=NO. Только документы/evidence.
Collector 9/9 (c872eed) и source eed114e приняты, не переоткрываются. Никаких live/SSH/DNS/registry,
apply, CI, production.

Предыдущие требования: docs/architecture/P8C_RV02_REVIEW_1a0b4c1_20261102.md.
Действующее решение — acceptance 1b32e4d выше; это не разрешение выполнения команд.
```text
AUTHORIZED_READ_SET_COMPLETE=YES · FLOW_MATRIX_COMPLETE=NO · EFFECTIVE_POLICY_UNION=UNKNOWN
NETPOL_APPROVED_FOR_APPLY=NO · CI/PRODUCTION=NOT_AUTHORIZED · P8C=NOT_FINAL_ACCEPTED
```

## 0. Полный словарь источников (path → blob)

Все repo-local пути ниже разрешаются в dedvmedved-dot/otus-diplom при ref
1b32e4d87f9925339f2192c7893fc74f2ddae5eb. Для внешних исходников ref указан отдельно.
INV: UTC 2026-10-26T17:32:44–47Z, номера R1…R15 — порядок записей;
PH2: UTC 2026-10-27T13:57:05–06Z, IDs C1/S1/S2;
ONERUN: UTC 2026-11-02T09:35:24–25Z, IDs F-*.
P7/P6 — исторические факты на даты их evidence directories, не current freshness.

| Ключ | Path | Blob |
|---|---|---|
| INV | evidence/P8/20261026T173244Z-p8c-rv02-live-inventory/inventory.jsonl | c1f59c8d0ebcbab1f9cfc40171add6aa2289450c |
| PH2 | evidence/P8/20261027T140000Z-p8c-rv02-phase2-live/result/supplemental.jsonl | 7c6151b490c02a79ecfe2337e6f262addd36519a |
| ONERUN | evidence/P8/20261102T094000Z-p8c-rv02-podlist-onerun/followup.jsonl | 84ceb7cbacb647f2b3cd7fcbbe545992c7e2e35e |
| P7-DNS | evidence/P7/20261019T030033Z-task-p7c-b2-r1-dns1-coredns-resume/15-dns-after-demo-pak.txt | 89cd2fe653f09924ede7adcd4a90bbaf515211cc |
| P7-BIND | evidence/P7/20261019T030033Z-task-p7c-b2-r1-dns1-coredns-resume/16-bind-authority-check.txt | 680e504cf1027789d124e8c8bf7b29121e24a23e |
| P7-S3 | evidence/P7/20261019T113205Z-task-p7c-b2-r2-canonical-reproducibility-closure/09-live-dns-s3-contract.txt | 078398f07263bae41e1f824b609edc7bd03ec24b |
| P6-LBSVC | evidence/P6/20260909T232839Z-task-p6d-r2-final-evidence-contract-closure/25a-loadbalancer-service-raw.json | b71e1453e890bab06b90bdaa697aa18e7c9124c4 |
| EG-GWC | manifests/envoy-gateway/p6c-gatewayclass.yaml | 80b1d683a7193fd1cebc5d29d6f6b0a671f5d1b6 |
| EG-VALUES | manifests/envoy-gateway/p6c-envoy-gateway-values.yaml | 6b1ea60d8e4120016f5675771c46f92f96dadc0e |
| EG-SRC | envoyproxy/gateway internal/gatewayapi/listener.go (ref 0260554fd4f33b787aad77a129fc0ffeb00c1f29, v1.9.1) | 3d8376553ad570ab22476a7d163053eaf32d3883 |
| CALICO | ansible/playbooks/files/calico-v3.32.0.yaml | 21ea9b4b163305ea479bc7708965104465ffc716 |
| BARMAND | portal/networkpolicy/supplemental-design.md | a4de674f9b98f7ecc2dc063db15ccfca7195484b |
| NP-YAML | portal/manifests/networkpolicy.yaml | fccb8432135a18f8b7099e131471a48808df1ed7 |
| GW-YAML | portal/manifests/gateway.yaml | 1e1f48a3c6d03c4558f4b4c3cca24bc12c22b763 |
| DEP-YAML | portal/manifests/deployment.yaml | 2cb27165330fe4b6772af3a06a1940d661efc72f |
| CNPG-TYPES | cloudnative-pg/cloudnative-pg v1.30.1 api/v1/cluster_types.go | 891424dde2287deffcf22b88683f4d8f96376993 |
| BARMAN-TYPES | cloudnative-pg/plugin-barman-cloud v0.13.0 api/v1/objectstore_types.go | 928d52c982b56f11b2eb00f4f88dea4e75916e12 |
| BACKUP-CONTRACT | docs/architecture/P8B_POSTGRES_BACKUP_CONTRACT.md | b1e2b51ff46bda7f172432ce43713b7d1a7415c0 |
| PORTAL-HTTPSRV | portal/internal/httpapi/server.go | c804bf231fc68bb0cfed1b4a0c058a1b938345d4 |
| PORTAL-AUTH | portal/internal/auth/auth.go | 62c7a0586895bfe2a03fd8207daf5641dc664f0c |
| METALLB-L2 | https://metallb.io/concepts/layer2/ | — (doc reference) |

Селекторы: namespace-label `kubernetes.io/metadata.name`; owning-labels
`gateway.envoyproxy.io/owning-gateway-name` / `gateway.envoyproxy.io/owning-gateway-namespace`.

## 1. RR-01/C1 — ingress: разделение transport / routing / auth

**Сетевой путь (без выдуманных hop):** MetalLB L2 объявляет VIP на узле; далее стандартный
Kubernetes Service forwarding к endpoint (EnvoyProxy pod) на `targetPort 10443`. `nodePort` и
`healthCheckNodePort` — выделенные поля Service, НЕ доказанный hop VIP→NodePort; показываются
отдельно (P6-LBSVC: nodePort 31999, healthCheckNodePort 30986 — для эталонного gateway, не нашего).
Source IP: `externalTrafficPolicy: Local` задаёт **ожидаемую** семантику сохранения client IP до
Envoy pod (METALLB-L2 + P6-LBSVC), НЕ измеренный факт.

**Разделение уровней:**
- Transport (TLS): Gateway listener https:443, TLS mode Terminate, certRef portal-ui-tls (GW-YAML).
- Routing: hostname `portal.demo-pak.test` + HTTPRoute → Service `portal:80` → container 8080 (GW-YAML/DEP-YAML).
- Authentication: Portal прикладной **Basic Auth** — Handler включает auth, затем route
  (PORTAL-HTTPSRV), проверка в PORTAL-AUTH. TLS/hostname/route НЕ аутентифицируют клиента;
  аутентификация — прикладная, не сетевой слой. Новый auth не запрашивается.

**Port translation:** 443 → 10443 (EG-SRC wellKnownPortShift=10000; не container443).

**Dataplane Pod:** `envoy-gateway-system`, labels `app.kubernetes.io/component=proxy`,
`app.kubernetes.io/managed-by=envoy-gateway`, `app.kubernetes.io/name=envoy`, `gateway.envoyproxy.io/owning-gateway-name=portal-gateway` и
`gateway.envoyproxy.io/owning-gateway-namespace=portal`.

**Выбранный Service:** LoadBalancer, externalTrafficPolicy=Local; generated ports/ownership
проверяются PR-5 до дальнейшего допуска. Runtime значения не наследуются из P6 по предположению.

**Ingress boundary:** L7 (TLS + hostname + route + Basic Auth). Dataplane policy `policyTypes=[Egress]`,
ingress объектом НЕ ограничивается; namespace-wide deny в envoy-gateway-system НЕ вводится.

**Граница экспозиции (S4):** механизм удержания отсутствует. Создание Gateway разрешается только
в отдельном deployment-gate после готовности TLS, прикладной auth и всех предшествующих политик.
Programmed+LB IP — признак потенциальной экспозиции, не доказательство end-to-end доступности
и не точная временная граница: status обновляется асинхронно. Считать риск экспозиции начавшимся
с создания Gateway. Listener рассчитан на клиентов с сетевым маршрутом; L3 allowlist не заявлен.
Dataplane-egress policy и Portal создаются ДО Gateway; Gateway — последним.
Rollback S4 в deployment-gate: запрос удаления только нового Gateway с UID-precondition,
дождаться удаления его generated Service и dataplane Pods с обеими owning labels; лишь затем
снимать dataplane policy. Сам факт принятия delete не доказывает прекращение forwarding.
Недоступная проверка/timeout/UID mismatch → STOP, policy сохранить. Это план, не разрешение deletion.

## 2. RR-02/A — S0–S4: условный baseline, union, проверяемые pre/post checks

**S0 (условный baseline):** ожидается — CNPG Portal кластер `spec.instances=3`, `status.instances=3`,
`status.readyInstances=3`, `Ready=True`; operator в cnpg-system reconcile-без ошибок; kube-dns
EndpointSlices с непустым ready-набором; F-NP (Calico NP) пуст на срезе 09:35Z. Ограничение: F-NP —
только Calico NP; весь policy-union не доказан текущим. PR-6 сравнивает конечный исходный policy/label set; не вычисляет effective union. Отличие → STOP.

**Последовательность (union = объединение разрешений selecting-политик, не пересечение):**

| Шаг | Операция | Union после | Rollback (UID-precondition) |
|---|---|---|---|
| S0 | — | CNPG/др. portal Pods без наших NetPol | — |
| S1 | apply p8c-cnpg-existing-flows (Ingr+Egr) | CNPG: полный allowlist | delete UID(existing-flows) → S0 |
| S2a | apply baseline-default-deny-all | CNPG: existing-flows ∪ default-deny (не сужается); др. portal: default-deny | delete UID(default-deny) → S1 |
| S2b | apply baseline-allow-dns-egress | др. portal: default-deny ∪ dns-egress; CNPG: не сужается | delete UID(allow-dns) → S2a |
| S3 | apply p8c-portal-flows + p8c-migrator-flows (политики ДО workloads) | Portal/migrator: allowlist | delete UID(portal-flows)+UID(migrator-flows) → S2b; workloads — отдельный deployment-gate |
| S4 | apply p8c-portal-dataplane-flows; затем Gateway (dataplane) последним | dataplane egress; listener экспонируется в момент Programmed+LB IP | delete UID(Gateway) + подтверждённое завершение cleanup (§1), затем UID(dataplane-flows) → S3 |

Rollback-порядок: S4→S3→S2b→S2a→S1→S0; **default-deny и allow-dns снимать ДО existing-flows**
(иначе CNPG под default-deny без egress). Workload-удаление — отдельный deployment-gate, не NetPol-gate.

### Pre/post checks: конечные правила, а не live-доказательства

Все проверки ниже — DESIGN/NOT_EXECUTED. В S0 отсутствие данных блокирует начало без mutation.
После изменения FAIL означает откат только новых объектов по порядку выше и STOP.
INCONCLUSIVE означает запрет следующей стадии; если безопасная работоспособность после
изоляции не установлена, использовать тот же заранее разрешённый rollback до S0.
Это не объявляет idle отказом. Недоступность API/UID verification запрещает слепой delete:
остановиться и передать оператору; не менять существующие workloads.

Наблюдения используют monotonic deadline W с начала конкретной проверки, максимум N запросов,
минимальный интервал I между началами запросов. Request timeout = min(15s, remaining W);
запрос при remaining<=0 не запускать, sleep за deadline не делать. Поэтому I×N не прибавляется
к N×15s и окно не расширяется. UTC начала/окончания каждого GET фиксируются отдельно.
Возраст последнего успешного GET при оценке должен быть <=30s (Gateway <=60s).
GET-time — время чтения состояния, не время бизнес-успеха или успешной WAL-доставки.

| ID / стадия | Точный источник и ожидаемое состояние | W / I / N | Исход и предел доказательства |
|---|---|---|---|
| HC-DB / S0–S4 | GET /apis/postgresql.cnpg.io/v1/namespaces/portal/clusters/portal-db; spec.instances=3, status.instances=3, status.readyInstances=3; ровно одна condition type=Ready со status=True | 60s / 10s / 6 | Отсутствие/null/Unknown/неправильный тип → INCONCLUSIVE; явный False или уменьшение ready → FAIL. Не доказывает Pod→DNS/API/S3 |
| HC-ARCH-STATE / S0–S4 | Тот же ответ: ровно одна condition type=ContinuousArchiving, status=True. Сохранять только type/status/reason/lastTransitionTime (не message); сравнить с S0 | общее окно HC-DB, дополнительный GET не нужен | Любой False → FAIL независимо от текста reason; Unknown/absence → INCONCLUSIVE. reason — диагностика, не незаполненный allowlist. Старый True не является новым успехом |
| HC-WAL-PROGRESS / до S1 и каждого следующего шага | В данном разрешённом read-set источник свежего timestamp/counter успешной WAL-доставки не предусмотрен. firstRecoverabilityPoint не использовать | запросов 0 | INCONCLUSIVE/STOP. Это runtime verification dependency, не утверждение отсутствия подходящих метрик в продукте. До её отдельного решения S1 не начинать; после изменения без достаточного подтверждения использовать rollback-правило выше |
| HC-OP / S0–S4 | GET /api/v1/namespaces/cnpg-system/pods?labelSelector=app.kubernetes.io%2Fname%3Dcloudnative-pg&limit=200; полный непустой PodList; у каждого выбранного не terminating Pod Ready=True, минимум один; неизвестные/неожиданные Pod identities → STOP | 60s / 10s / 6 | False → FAIL; отсутствие/Unknown/пусто/неполно → INCONCLUSIVE. Не использовать выдуманное имя Deployment. Pod Ready показывает состояние оператора, но не доказывает успешность каждого reconcile/API-вызова |
| HC-DNS / S0–S4 | GET /apis/discovery.k8s.io/v1/namespaces/kube-system/endpointslices?labelSelector=kubernetes.io%2Fservice-name%3Dkube-dns&limit=200; полный непустой набор адресов ready=true и объявленные UDP/TCP53 | 30s / 5s / 6 | ready absent/null/неполно → INCONCLUSIVE; явный false/неожиданное изменение → FAIL/STOP. Не доказывает DNS-запрос из CNPG |
| HC-PORTAL / S3–S4, после создания | GET /apis/apps/v1/namespaces/portal/deployments/portal; spec.replicas=1, status.observedGeneration=metadata.generation, readyReplicas=updatedReplicas=availableReplicas=1 | 60s / 10s / 6 | Сходимость до deadline, затем FAIL или INCONCLUSIVE по наличию данных. Probe /readyz:8081 задан source; GET Deployment не вызывает probe и не доказывает внешний доступ |
| HC-GW / S4 | GET /apis/gateway.networking.k8s.io/v1/namespaces/portal/gateways/portal-gateway; Accepted=True и Programmed=True, обе observedGeneration=metadata.generation; PR-5 Service с LB IP | 120s / 10s / 12 | Неоднозначность/absence/ошибка → INCONCLUSIVE; явный отказ → FAIL. Не является E2E smoke test; потенциальная экспозиция начинается раньше завершения этого check |

HTTP/API errors, invalid shape, truncation, timeout не конвертировать в пустой список или PASS.
Стабильный Ready не обязан иметь свежий lastTransitionTime. observedGeneration требовать только
в указанных типах с этим полем, не добавлять его к CNPG по аналогии.
API transport этих чтений доказывает operator-client→API, не CNPG/Portal→API.
Не форсировать WAL, backup, restore, PITR, failover; не запускать принятые тесты.

## 3. 14-flow таблица (восстановлена, полные ссылки на §0)

Aliases: CNPG instance = namespace portal + cnpg.io/cluster=portal-db AND cnpg.io/podRole=instance;
CNPG sidecar использует тот же Pod/network namespace. Operator = cnpg-system + app.kubernetes.io/name=cloudnative-pg.
Dataplane = envoy-gateway-system + все пять labels из §1. Portal = portal + app.kubernetes.io/name=pak-portal;
migrator = portal + app.kubernetes.io/name=pak-portal-migrator. Namespace selector использует
kubernetes.io/metadata.name; namespaceSelector и podSelector одного peer объединяются AND.
API разрешается только CNPG instances и Portal, не migrator. DNS нужен всем перечисленным
workloads; dataplane DNS включается в dataplane-policy. ✓ означает согласованность candidate
дизайна со строкой, не разрешённый YAML/apply и не runtime PASS.

| FLOW-ID | src → dst (namespace + selector) | Направление / enforcement | proto:port (pre/post Service) | Evidence/source-manifest | Candidate rule / delta | UNKNOWN / влияние |
|---|---|---|---|---|---|---|
| REP-5432 (EXISTING) | portal `cnpg.io/cluster=portal-db`,`cnpg.io/podRole=instance` → same | ingress+egress (peer↔peer) | TCP 5432 | INV R1 pods 5432; R3 eps | existing-flows ingress+egress 5432 | ✓ |
| IM-8000 (EXISTING) | portal CNPG instance → same | ingress+egress | TCP 8000 | INV R1 port 8000 | existing-flows ingress+egress 8000 | ✓ |
| OP-IM-8000 (EXISTING) | cnpg-system `app.kubernetes.io/name=cloudnative-pg` → portal CNPG instance | ingress (к CNPG) | TCP 8000 | INV R1 operator | existing-flows ingress 8000 | ✓ |
| BAR-5432 legacy (EXISTING) | (a) cnpg-system operator → cnpg-system `app=barman-cloud`:9090 (вне CNPG-policy); (b) portal CNPG sidecar → 172.30.143.10:443 | (a) вне; (b) egress CNPG Pod | TCP 9090 (control) / 443 (S3) | PH2 S1/S2; P7-DNS/P7-S3; BARMAND §4 | existing-flows sidecar S3 egress 172.30.143.10/32:443 ✓; controller→5432 ingress **NOT_APPROVED** | необходимость controller→DB5432 не установлена → в дизайн не входит |
| MON-9187 | (нет источника) → portal CNPG `cnpg.io/cluster=portal-db`:9187 | — | TCP 9187 | INV R11-13/R1 NOT_FOUND_IN_SURVEYED_SOURCES | нет | скрейпер не найден в surveyed sources; не доказательство полного отсутствия |
| DNS-53 (EXISTING) | portal workloads → kube-system `k8s-app=kube-dns` | egress (selector-robust) | UDP+TCP 53 | INV R2 svc 10.96.0.10; R3 eps | egress podSelector 53 ✓ | selector candidate принят; runtime path/enforcement не доказан |
| API-6443 (EXISTING) | portal CNPG instance + Portal → API | egress | TCP 443 (ClusterIP 10.96.0.1) / 6443 (endpoints) | INV R2 svc; R3 eps | egress **отдельные tuple**: 10.96.0.1/32:443 + 172.30.140.101/32:6443 + .102/32:6443 + .103/32:6443 (не /24, не декартово) | enforcement point UNKNOWN → representation-robust tuple |
| S3-443 (EXISTING) | portal CNPG sidecar → 172.30.143.10 | egress CNPG Pod | TCP 443 | P7-DNS/P7-S3/P7-BIND (historical); PH2 C1 | existing-flows egress 172.30.143.10/32:443 ✓ | freshness stale → precheck |
| APP-DB-5432 (PLANNED) | portal `app.kubernetes.io/name=pak-portal` → portal CNPG `cnpg.io/cluster=portal-db` | ingress (к CNPG) + egress (Portal) | TCP 5432 | DEP-YAML (manifest) | existing-flows ingress 5432 + portal-flows egress 5432 | ✓ |
| APP-MET-9187 (PLANNED) | portal `app.kubernetes.io/name=pak-portal` → portal CNPG `cnpg.io/cluster=portal-db` | ingress + egress | TCP 9187 | DEP-YAML (manifest) | ingress 9187 + portal egress 9187 | ✓ |
| MIG-DB-5432 (PLANNED) | portal `app.kubernetes.io/name=pak-portal-migrator` → portal CNPG `cnpg.io/cluster=portal-db` | ingress + egress | TCP 5432 | DEP-YAML (manifest) | ingress 5432 + migrator egress 5432 | ✓ |
| ENV-XDS-18000 (PLANNED) | envoy-gateway-system dataplane (owning-gateway-name=portal-gateway, owning-gateway-namespace=portal) → envoy-gateway-system `control-plane=envoy-gateway` | egress | TCP 18000 | INV R1/R2 control-plane; EG-VALUES | dataplane egress 18000 | ✓ |
| ENV-BACK-8080 (PLANNED) | envoy dataplane → portal `app.kubernetes.io/name=pak-portal` | egress (dataplane) + ingress (Portal) | TCP 8080 (container; Service portal:80→8080) | DEP-YAML/GW-YAML (manifest) | dataplane egress 8080 + portal ingress 8080 | Service DNAT 80→8080 задокументирован |
| ENV-LISTENER (PLANNED) | external → Gateway portal-gateway listener https:443 (TLS Terminate, portal.demo-pak.test) | L7 (transport/routing/auth), не dataplane NetPol | TCP 443 → 10443 | GW-YAML; EG-SRC; P6-LBSVC; PORTAL-AUTH | dataplane Egress-only; ingress НЕ моделируется в NetPol | риск экспозиции с создания Gateway; status не E2E proof (§1) |

## 4. Candidate delta (NOT_APPROVED, YAML не меняется)

1. Barman controller→DB5432 (NP-YAML ingress `cnpg-system`+`app=barman-cloud`→5432) — NOT_APPROVED
   (необходимость не установлена, BARMAND §4).
2. API `172.30.140.0/24:6443` (NP-YAML egress existing-flows + portal-flows) — NOT_APPROVED: заменить
   на отдельные tuple 10.96.0.1/32:443 + три /32:6443 (без декартова расширения).

## 5. Read proposals — точные пути, пределы и доказательная сила

NOT_AUTHORIZED/NOT_EXECUTED. Это конечный дизайн будущих чтений, не готовый execute-gate
и не указание выводить raw objects. Каждый HTTP body допустим только во временной памяти
локального обработчика: typed projection до evidence, без env/args/annotations/managedFields,
Secret/ConfigMap, токенов, сырых stdout/stderr. Будущий execute-gate должен закрепить способ
обработки/проверки; новые collectors в этом задании не разрабатываются.

Форма argv: kubectl --context kubernetes-admin@pak-portal --request-timeout=15s get --raw '<path>'.
Для каждого list: один HTTP GET, автоматической пагинации/повтора нет; continue absent/пустая
строка, правильный typed List и непустой resourceVersion обязательны. Явный null/неправильный
тип, nonempty continue, over-limit, unsupported или transport error → STOP.
Нельзя заменять raw endpoint на resource.group/v1: kubectl интерпретирует slash как type/name.
Raw response не должен печататься в терминал или попадать в возвращаемый пакет.

### PR-3 — API endpoint-tuple freshness (максимум 1 GET)
Path:
`/apis/discovery.k8s.io/v1/namespaces/default/endpointslices?labelSelector=kubernetes.io%2Fservice-name%3Dkubernetes&limit=200`

Typed EndpointSliceList discovery.k8s.io/v1; 1..200 slices допустимы, не требовать один slice.
Каждый item привязан к namespace default и label kubernetes.io/service-name=kubernetes.
Проекция: identity/UID, addresses, ready, port/name/protocol. Неиспользуемые поля отбрасываются.
Непустой полный ready=true набор TCP tuples должен совпасть с
172.30.140.101:6443, 172.30.140.102:6443, 172.30.140.103:6443.
Неожиданные addresses/ports/ready/shape → STOP, не автоматически расширять allowlist.
Не доказывает enforcement или DNS/API доступ из CNPG.

### PR-4 — S3 freshness
Историческое P7 resolution/path остаётся stale. Свежий CNPG-sidecar→S3 результат не получен.
PR-4 NOT_EXECUTABLE/NOT_AUTHORIZED; STOP до S1, пока отдельное решение не определит допустимое
наблюдение. Отсутствие метода в этом read-set не означает отсутствие метрик/инструментов вообще.
Node DNS не заменяет Pod-путь. Новый probe/exec/log/backup не предлагается как уже разрешённый.

### PR-5 — generated dataplane Service (максимум 1 GET)
Path:
`/api/v1/namespaces/envoy-gateway-system/services?labelSelector=gateway.envoyproxy.io%2Fowning-gateway-name%3Dportal-gateway%2Cgateway.envoyproxy.io%2Fowning-gateway-namespace%3Dportal&limit=2`

Typed ServiceList/v1, metadata.continue пуст, ровно один item, namespace и оба owning labels
совпадают. 0/2 items или ambiguity → STOP. Проекция metadata.name/namespace/uid/двух owning labels,
spec.type/externalTrafficPolicy/allocateLoadBalancerNodePorts/healthCheckNodePort,
spec.ports[].name/protocol/port/targetPort/nodePort, spec.selector,
status.loadBalancer.ingress[].ip/ipMode. IP/UID/назначенные порты фиксируются, не угадываются.
Ожидания: LoadBalancer, Local, allocateLoadBalancerNodePorts=true; отдельный TCP443→10443;
назначенные nodePort/healthCheckNodePort в допустимом Kubernetes диапазоне портов,
не конфликтуют с наблюдаемым Service; непустой LB IP и selectors dataplane из §1.
Имена/числа из P6 не использовать как expected. Проверка не доказывает E2E доступность.

### PR-6 — конечный policy/label-set freshness (максимум 9 GET, по 200 items)
Только сравнение конфигурации, НЕ доказательство EFFECTIVE_POLICY_UNION.
Все paths — version-pinned; auto-discovery, fallback API и follow-continue запрещены.

| ID | Literal path | Scope / безопасное сравнение |
|---|---|---|
| P6-KNP | /apis/networking.k8s.io/v1/networkpolicies?limit=200 | Все namespaces; ожидается complete empty по historical INV R5; любое появление → STOP |
| P6-NP | /apis/crd.projectcalico.org/v1/networkpolicies?limit=200 | Все namespaces; complete empty по ONERUN F-NP; появление → STOP |
| P6-GNP | /apis/crd.projectcalico.org/v1/globalnetworkpolicies?limit=200 | Cluster; complete empty F-GNP; появление → STOP |
| P6-HEP | /apis/crd.projectcalico.org/v1/hostendpoints?limit=200 | Cluster; complete empty F-HEP; появление → STOP |
| P6-CNP | /apis/policy.networking.k8s.io/v1alpha2/clusternetworkpolicies?limit=200 | Cluster; complete empty F-CNP; появление → STOP |
| P6-TIER | /apis/crd.projectcalico.org/v1/tiers?limit=200 | Cluster; принятая typed projection Tier: labels/order/defaultAction + identity, сравнить с F-TIER |
| P6-FELIX | /apis/crd.projectcalico.org/v1/felixconfigurations?limit=200 | Cluster; только default сравнивается по принятой Felix projection с F-FELIX. Любой иной объект → STOP, не оценивать overrides |
| P6-NS | /api/v1/namespaces?limit=200 | Только name/uid + kubernetes.io/metadata.name; для выбранных namespaces label должен равняться name |
| P6-PODS | /api/v1/pods?limit=200 | Только name/namespace/uid и ключи labels, реально используемые selector aliases §1/§3; другие поля не экспортируются |

Непустой policy list, ранее принятый пустым, уже достаточен для STOP без чтения/export его rules.
Для существующих Tier/Felix требуется semantic comparison принятой projection, не только UID.
Unknown semantic fields/непокрытая schema → STOP. Отсутствующие исторические поля/UID не
превращать в ожидаемые значения: freshness comparison тогда INCONCLUSIVE, gate требует
отдельно проверяемую исходную привязку. Неизвестные label changes или состав selected peers → STOP.
Сравнение default Felix не устанавливает effective per-node mode; node env/annotations,
прочие источники enforcement и реальные traffic paths не покрываются.
Не утверждать полноту всего policy union даже при успешности этих девяти чтений.
## 6. Architect decision и границы приёмки

A/B/C закрыты как offline document design после точечных исправлений Architect в этой редакции.
Авторская редакция 1b32e4d сама по себе не объявляется безошибочной: исправления и provenance
зафиксированы в docs/architecture/P8C_RV02_ACCEPTANCE_1b32e4d_20261102.md.

Приняты: конечная topology/flow model, bounded read proposals, конкретные status checks,
условный S0/union/rollback, historical-versus-fresh distinction. Не приняты как выполненные:
runtime checks, policy YAML, image release, auth provisioning, deployment, E2E acceptance.
Runtime blockers остаются отдельными от законченного документа: S3 freshness/WAL-progress,
current policy/peer baseline и будущий generated runtime. Без их gate S1 запрещён.

```text
OFFLINE_DESIGN=ACCEPTED_WITH_RUNTIME_LIMITS
DOCUMENT_REWORK_REQUIRED=NO
AUTHORIZED_READ_SET_COMPLETE=YES
FLOW_MATRIX_COMPLETE=NO
EFFECTIVE_POLICY_UNION=UNKNOWN
EXECUTION_GATE_READY=NO
PHASE2_NEW_RUN_APPROVED=NO
OWNER_PHASE2_HANDOFF_ALLOWED=NO
NETPOL_APPROVED_FOR_APPLY=NO
CI / WORKFLOW / OWNER_HELPERS / PRODUCTION=NOT_AUTHORIZED
P8C=NOT_FINAL_ACCEPTED
P8D–P8G/P9=NOT_AUTHORIZED
```

Candidate policy YAML не изменялся. Коллектор, S1 и 9/9 inventory не переоткрываются.
Следующий инженерный этап — отдельный согласованный offline candidate YAML/release/deploy
package; этот документ не является разрешением на его live-исполнение.
