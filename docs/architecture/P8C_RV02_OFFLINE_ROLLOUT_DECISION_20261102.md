# P8C-RV02-OFFLINE-ROLLOUT-DECISION-R1-FINAL — закрытие A/B/C (review 1a0b4c1)

Дата: 2026-11-02 (UTC). Исполнитель: PRIMARY HERMES. Только offline-доработка документов/evidence.
Collector 9/9 (c872eed) и source eed114e приняты, не переоткрываются. Никаких live/SSH/DNS/registry,
apply, CI, production.

Authority: docs/architecture/P8C_RV02_REVIEW_1a0b4c1_20261102.md (REVIEW_HEAD=1a0b4c1).
```text
AUTHORIZED_READ_SET_COMPLETE=YES · FLOW_MATRIX_COMPLETE=NO · EFFECTIVE_POLICY_UNION=UNKNOWN
NETPOL_APPROVED_FOR_APPLY=NO · CI/PRODUCTION=NOT_AUTHORIZED · P8C=NOT_FINAL_ACCEPTED
```

## 0. Полный словарь источников (path → blob)

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
| EG-SRC | Envoy Gateway v1.9.1 internal/gatewayapi/listener.go (commit 0260554f…) | 3d8376553ad570ab22476a7d163053eaf32d3883 |
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
`app.kubernetes.io/managed-by=envoy-gateway`, `app.kubernetes.io/name=envoy`, owning-gateway-{name,namespace}=portal.

**Ingress boundary:** L7 (TLS + hostname + route + Basic Auth). Dataplane policy `policyTypes=[Egress]`,
ingress объектом НЕ ограничивается; namespace-wide deny в envoy-gateway-system НЕ вводится.

**Момент экспозиции (S4):** когда Gateway становится Programmed + LB IP назначен, listener достижим
для любого клиента с сетевым маршрутом. Механизма удержания нет — экспозиция наступает в момент
Programmed+LB IP. Порядок: dataplane-egress policy и Portal workload создаются ДО Gateway; Gateway —
последним. Rollback S4: сначала удалить Gateway (L7, закрывает экспозицию), затем dataplane policy.

## 2. RR-02/A — S0–S4: условный baseline, union, проверяемые pre/post checks

**S0 (условный baseline):** ожидается — CNPG Portal кластер `spec.instances=3`, `status.instances=3`,
`status.readyInstances=3`, `Ready=True`; operator в cnpg-system reconcile-без ошибок; kube-dns
EndpointSlices с непустым ready-набором; F-NP (Calico NP) пуст на срезе 09:35Z. Ограничение: F-NP —
только Calico NP; весь policy-union не доказан текущим. PR-6 сверяет union; отличие → STOP.

**Последовательность (union = объединение разрешений selecting-политик, не пересечение):**

| Шаг | Операция | Union после | Rollback (UID-precondition) |
|---|---|---|---|
| S0 | — | CNPG/др. portal Pods без наших NetPol | — |
| S1 | apply p8c-cnpg-existing-flows (Ingr+Egr) | CNPG: полный allowlist | delete UID(existing-flows) → S0 |
| S2a | apply baseline-default-deny-all | CNPG: existing-flows ∪ default-deny (не сужается); др. portal: default-deny | delete UID(default-deny) → S1 |
| S2b | apply baseline-allow-dns-egress | др. portal: default-deny ∪ dns-egress; CNPG: не сужается | delete UID(allow-dns) → S2a |
| S3 | apply p8c-portal-flows + p8c-migrator-flows (политики ДО workloads) | Portal/migrator: allowlist | delete UID(portal-flows)+UID(migrator-flows) → S2b; workloads — отдельный deployment-gate |
| S4 | apply p8c-portal-dataplane-flows; затем Gateway (dataplane) последним | dataplane egress; listener экспонируется в момент Programmed+LB IP | delete UID(Gateway) → закрыть экспозицию, затем UID(dataplane-flows) → S3 |

Rollback-порядок: S4→S3→S2b→S2a→S1→S0; **default-deny и allow-dns снимать ДО existing-flows**
(иначе CNPG под default-deny без egress). Workload-удаление — отдельный deployment-gate, не NetPol-gate.

**Pre/post checks (A1/A2/A3 — точные object/field, конечное время, INCONCLUSIVE ≠ PASS ≠ fail):**

| Стадия | Проверка (object/field) | Ожидание | request-timeout / интервал×число | Freshness | Исход |
|---|---|---|---|---|---|
| все | `clusters.postgresql.cnpg.io/portal-db -n portal` → `spec.instances`, `status.instances`, `status.readyInstances`, `status.conditions[type=Ready].status` | 3/3/3 + Ready=True; отсутствие поля/condition → INCONCLUSIVE | 15s / 10s×6 (60s окно) | GET-time <30s | timeout/≠ → rollback стадии + STOP |
| все (state) | `.status.conditions[type=ContinuousArchiving]` + `.status.conditions[type=Ready]` reason — сравнение до/после стадии | нет НОВОЙ error-condition с момента старта стадии; reason-перечень перечисляется, не «нет ошибки» | 15s / 10s×6 | GET-time <30s | new error → rollback + STOP |
| все (WAL/S3, честно) | точный источник свежего timestamp/counter архивирования в закреплённой версии **отсутствует** (firstRecoverabilityPoint deprecated + не заполняется для backup-плагинов, BARMAN-TYPES/CNPG-TYPES) | n/a | n/a | n/a | **INCONCLUSIVE/STOP перед следующей стадией**; НЕ изобретать timestamp, НЕ считать старый True свежим |
| все (operator) | `deployments/cloudnative-pg-controller-manager -n cnpg-system` (или pod label `app.kubernetes.io/name=cloudnative-pg`) → `.status.readyReplicas`/`.status.conditions` | Ready + отсутствие error-reason | 15s / 10s×6 | GET-time <30s | ≠ → rollback + STOP |
| S1..S4 (DNS) | `endpointslices.discovery.k8s.io -n kube-system -l kubernetes.io/service-name=kube-dns` → `endpoints[].conditions.ready` | непустой набор endpoints, все present ready=true; ready absent/null → INCONCLUSIVE | 15s / 5s×6 | GET-time <30s | пусто/≠ → rollback + STOP |
| S3 | `deployments/portal -n portal` → `.status.readyReplicas` (+ readinessProbe `/readyz` mgmt 8081) | readyReplicas=1 | 15s / 10s×6 | GET-time <30s | ≠ → rollback S3 + STOP |
| S4 | `gateways.gateway.networking.k8s.io/portal-gateway -n portal` → `.status.conditions[type=Accepted/Programmed].{status,observedGeneration,reason}` + Service `status.loadBalancer.ingress.ip` | Accepted+Programmed=True при observedGeneration==metadata.generation; LB IP назначен | 15s / 10s×12 (120s окно) | GET-time <60s | ≠/неоднозначность → rollback S4 + STOP |

Времена: request-timeout 15s; «GET-time» — время запроса, НЕ время наблюдаемого успеха; старый
lastTransitionTime не обесценивает стабильный Ready; observedGeneration проверяется только где поле
существует. Idle/no-progress = INCONCLUSIVE/STOP (не PASS, не автоматический отказ). Backup/restore/
PITR/failover и destructive probes НЕ запускать.

## 3. 14-flow таблица (восстановлена, полные ссылки на §0)

| FLOW-ID | src → dst (namespace + selector) | Направление / enforcement | proto:port (pre/post Service) | Evidence/source-manifest | Candidate rule / delta | UNKNOWN / влияние |
|---|---|---|---|---|---|---|
| REP-5432 (EXISTING) | portal `cnpg.io/cluster=portal-db`,`cnpg.io/podRole=instance` → same | ingress+egress (peer↔peer) | TCP 5432 | INV R1 pods 5432; R3 eps | existing-flows ingress+egress 5432 | ✓ |
| IM-8000 (EXISTING) | portal CNPG instance → same | ingress+egress | TCP 8000 | INV R1 port 8000 | existing-flows ingress+egress 8000 | ✓ |
| OP-IM-8000 (EXISTING) | cnpg-system `app.kubernetes.io/name=cloudnative-pg` → portal CNPG instance | ingress (к CNPG) | TCP 8000 | INV R1 operator | existing-flows ingress 8000 | ✓ |
| BAR-5432 legacy (EXISTING) | (a) cnpg-system operator → cnpg-system `app=barman-cloud`:9090 (вне CNPG-policy); (b) portal CNPG sidecar → 172.30.143.10:443 | (a) вне; (b) egress CNPG Pod | TCP 9090 (control) / 443 (S3) | PH2 S1/S2; P7-DNS/P7-S3; BARMAND §4 | existing-flows sidecar S3 egress 172.30.143.10/32:443 ✓; controller→5432 ingress **NOT_APPROVED** | необходимость controller→DB5432 не установлена → в дизайн не входит |
| MON-9187 | (нет источника) → portal CNPG `cnpg.io/cluster=portal-db`:9187 | — | TCP 9187 | INV R11-13/R1 NOT_FOUND_IN_SURVEYED_SOURCES | нет | нет скрейпера; отметить для будущего |
| DNS-53 (EXISTING) | portal workloads → kube-system `k8s-app=kube-dns` | egress (selector-robust) | UDP+TCP 53 | INV R2 svc 10.96.0.10; R3 eps | egress podSelector 53 ✓ | DNAT-представление снято selector-правилом |
| API-6443 (EXISTING) | portal workloads → API | egress | TCP 443 (ClusterIP 10.96.0.1) / 6443 (endpoints) | INV R2 svc; R3 eps | egress **отдельные tuple**: 10.96.0.1/32:443 + 172.30.140.101/32:6443 + .102/32:6443 + .103/32:6443 (не /24, не декартово) | enforcement point UNKNOWN → representation-robust tuple |
| S3-443 (EXISTING) | portal CNPG sidecar → 172.30.143.10 | egress CNPG Pod | TCP 443 | P7-DNS/P7-S3/P7-BIND (historical); PH2 C1 | existing-flows egress 172.30.143.10/32:443 ✓ | freshness stale → precheck |
| APP-DB-5432 (PLANNED) | portal `app.kubernetes.io/name=pak-portal` → portal CNPG `cnpg.io/cluster=portal-db` | ingress (к CNPG) + egress (Portal) | TCP 5432 | DEP-YAML (manifest) | existing-flows ingress 5432 + portal-flows egress 5432 | ✓ |
| APP-MET-9187 (PLANNED) | portal `app.kubernetes.io/name=pak-portal` → portal CNPG `cnpg.io/cluster=portal-db` | ingress + egress | TCP 9187 | DEP-YAML (manifest) | ingress 9187 + portal egress 9187 | ✓ |
| MIG-DB-5432 (PLANNED) | portal `app.kubernetes.io/name=pak-portal-migrator` → portal CNPG `cnpg.io/cluster=portal-db` | ingress + egress | TCP 5432 | DEP-YAML (manifest) | ingress 5432 + migrator egress 5432 | ✓ |
| ENV-XDS-18000 (PLANNED) | envoy-gateway-system dataplane (owning-gateway-name=portal-gateway, owning-gateway-namespace=portal) → envoy-gateway-system `control-plane=envoy-gateway` | egress | TCP 18000 | INV R1/R2 control-plane; EG-VALUES | dataplane egress 18000 | ✓ |
| ENV-BACK-8080 (PLANNED) | envoy dataplane → portal `app.kubernetes.io/name=pak-portal` | egress (dataplane) + ingress (Portal) | TCP 8080 (container; Service portal:80→8080) | DEP-YAML/GW-YAML (manifest) | dataplane egress 8080 + portal ingress 8080 | Service DNAT 80→8080 задокументирован |
| ENV-LISTENER (PLANNED) | external → Gateway portal-gateway listener https:443 (TLS Terminate, portal.demo-pak.test) | L7 (transport/routing/auth), не dataplane NetPol | TCP 443 → 10443 | GW-YAML; EG-SRC; P6-LBSVC; PORTAL-AUTH | dataplane Egress-only; ingress НЕ моделируется в NetPol | экспозиция в момент Programmed+LB IP (§1) |

## 4. Candidate delta (NOT_APPROVED, YAML не меняется)

1. Barman controller→DB5432 (NP-YAML ingress `cnpg-system`+`app=barman-cloud`→5432) — NOT_APPROVED
   (необходимость не установлена, BARMAND §4).
2. API `172.30.140.0/24:6443` (NP-YAML egress existing-flows + portal-flows) — NOT_APPROVED: заменить
   на отдельные tuple 10.96.0.1/32:443 + три /32:6443 (без декартова расширения).

## 5. Read proposals (C2/C3 — точные argv/scope/проекция/limits)

- **PR-3 (API endpoint-tuple freshness)** — proposal-only, execute-gate:
  `kubectl get endpointslices.discovery.k8s.io/v1 -n default -l kubernetes.io/service-name=kubernetes -o json`,
  `--request-timeout=15s`, single GET (объект целиком, не paginated list — EndpointSlice по имени через
  список с единственным selectable label; при >1 slice/truncated/unsupported → STOP). Проекция:
  `endpoints[].addresses[]`, `endpoints[].conditions.ready`, `ports[].{name,port,protocol}`; ожидание —
  непустой набор с адресами 172.30.140.101/102/103:6443 и ready=true. НЕ доказывает enforcement.
- **PR-4 (S3 freshness)** — исторический P7 факт **stale**; без runtime-допуска свежее наблюдение
  NOT_EXECUTABLE/NOT_AUTHORIZED (не изобретать «timeout/attempts» placeholder). В execute-gate:
  STOP-прекондиция на сверку S3 до продолжения. Не предлагать неисполнимый probe.
- **PR-5 (generated dataplane Service, S4)** — proposal-only:
  `kubectl get service -n envoy-gateway-system -l gateway.envoyproxy.io/owning-gateway-name=portal-gateway,gateway.envoyproxy.io/owning-gateway-namespace=portal -o json`,
  `--request-timeout=15s`, single GET. Selector ДОЛЖЕН включать оба owning-ключа; ожидаемая
  cardinality=1; при >1/неоднозначности → STOP. Поля: `spec.type`, `spec.externalTrafficPolicy`,
  `spec.ports[].{name,port,targetPort,nodePort}`, `spec.healthCheckNodePort`, `metadata.uid`,
  `spec.selector`, `status.loadBalancer.ingress.ip`; targetPort ожидается 10443. Runtime-имена/IP/UID не угадывать.
- **PR-6 (S0 policy-set freshness)** — proposal-only: сверка полного исходного policy-set
  (НЕ доказательство EFFECTIVE_POLICY_UNION): GVR/scope — `networkpolicies.networking.k8s.io` (все ns),
  `networkpolicies.crd.projectcalico.org` (все ns), `globalnetworkpolicies`, `hostendpoints`,
  `tiers`, `felixconfigurations` (crd.projectcalico.org), `clusternetworkpolicies` (policy.networking.k8s.io/v1alpha2).
  Проекция имени/ns/UID + **typed projection семантических полей** (принятые контракты
  followup-typed-contract.json / NP_SPEC_ALLOWED) для обнаружения изменения rules при сохранённом UID;
  unknown/truncation/change → STOP (fail-closed), без raw export. Проверка default Felix НЕ доказывает
  effective per-node mode.

## 6. Авторский vs Architect статус

- **ARCHITECT_ACCEPTED**: 9/9 сбор, удаление PR-1/PR-2, P7 historical S3, точные API /32-кандидаты,
  UID-precondition, egress-only dataplane, разделение NetPol/deployment, полные label-ключи.
- **AUTHOR_PROPOSAL** (настоящий документ): ingress-модель (§1), S0–S4 rollback/checks (§2),
  14-flow table + delta (§3–4), read proposals (§5). Не Architect-accepted.

## 7. Итог
```text
TASK=P8C-RV02-OFFLINE-ROLLOUT-DECISION-R1-FINAL-CORRECTION
A=RESOLVED (readyInstances, убран firstRecoverabilityPoint-as-WAL, executable checks/INCONCLUSIVE)
B=RESOLVED (14-flow таблица восстановлена, полные path/blob, API tuple разделены)
C=RESOLVED (transport/routing/auth разделены, момент экспозиции определён, PR-3/5/6 bounded, PR-4 stale/STOP)
AUTHOR_PROPOSAL (не Architect-accepted): все проектные выводы выше
AUTHORIZED_READ_SET_COMPLETE=YES · FLOW_MATRIX_COMPLETE=NO · EFFECTIVE_POLICY_UNION=UNKNOWN
NETPOL_APPROVED_FOR_APPLY=NO · CI/PRODUCTION=NOT_AUTHORIZED · P8C=NOT_FINAL_ACCEPTED
```
STOP для Architect review. Candidate policy YAML не изменялся.
