# P8C-RV02-OFFLINE-ROLLOUT-DECISION-R1 — доработка OD-01…05

Дата: 2026-11-02 (UTC). Исполнитель: PRIMARY HERMES. Только offline-доработка документов по
review b5d8cab. Collector 9/9 (c872eed) и весь принятый source закрыты; новых live-чтений,
DNS-проб, apply, CI и production НЕ выполняется.

Authority: docs/architecture/P8C_RV02_REVIEW_a9e6fac_20261102.md (TASK=P8C-RV02-OFFLINE-ROLLOUT-DECISION-R1).
```text
AUTHORIZED_READ_SET_COMPLETE=YES · FLOW_MATRIX_COMPLETE=NO · EFFECTIVE_POLICY_UNION=UNKNOWN
NETPOL_APPROVED_FOR_APPLY=NO · CI/PRODUCTION=NOT_AUTHORIZED · P8C=NOT_FINAL_ACCEPTED
```

## 0. OD → исправленное место → источник → проверка

| OD | Исправление | Место (раздел ниже) | Источник | Проверка |
|---|---|---|---|---|
| OD-01 | PR-1 удалён; убрано «iptables/nftables=pre-DNAT»; B1 решён representation-robust правилом | §2 | calico-v3.32.0.yaml (CalicoNodeStatus agent/bgp/lastUpdated/routes, без backend); K8s 1.36 netpol docs (order implementation-dependent); supplemental-design §5 | статическое извлечение схемы |
| OD-02 | PR-2 удалён; S3 = P7 historical + freshness; Barman-роли разложены; control-9090 вне CNPG-policy | §3 | P7 15-dns-after-demo-pak.txt / 09-live-dns-s3-contract.txt / 16-bind-authority-check.txt; supplemental-design §4 | чтение P7 evidence |
| OD-03 | B3 решён по gateway.yaml/deployment.yaml; dataplane-policy Egress-only отражён | §4 | gateway.yaml (blob 1e1f48a3…), deployment.yaml (blob 2cb27165…) | статическое извлечение |
| OD-04 | union-aware state/rollback по 4 стадиям | §5 | networkpolicy.yaml (policyTypes Ingress,Egress) | сопоставление YAML |
| OD-05 | точные селекторы, candidate delta (NOT_APPROVED), MON-9187=NOT_FOUND_IN_SURVEYED_SOURCES, F-NP=Calico NP | §6, §7 | networkpolicy.yaml (blob fccb8432…) | сопоставление YAML |

## 1. Факты без «по памяти» (источник → blob/record)

| Факт | Источник | Blob/record |
|---|---|---|
| s3-backup.demo-pak.test → 172.30.143.10 (historical) | P7 15-dns-after-demo-pak.txt | blob 89cd2fe6… |
| CoreDNS forward demo-pak.test → 172.30.143.10; POD_DNS_TO_S3/POD_TO_S3_PATH accepted | P7 09-live-dns-s3-contract.txt | blob 078398f0… |
| BIND authority @172.30.143.10 | P7 16-bind-authority-check.txt | blob 680e504c… |
| CalicoNodeStatus status = agent(birdV4/birdV6), bgp, lastUpdated, routes — БЕЗ backend | calico-v3.32.0.yaml | blob 21ea9b4b… |
| IPPool = spec (cidr/encap/nat/…) — БЕЗ S3-достижимости status | calico-v3.32.0.yaml | blob 21ea9b4b… |
| Barman: sidecar (in-pod) выполняет backup/WAL/S3; controller=9090 RPC, invoked by CNPG; нет controller→DB5432/S3 | supplemental-design.md §4 | blob a4de674f… |
| K8s 1.36: адрес-rewrite порядок vs policy — implementation-dependent | supplemental-design.md §5 | K8s 1.36 netpol docs |
| Gateway portal-gateway: listener https:443 (HTTPS, TLS Terminate, portal.demo-pak.test, certRef portal-ui-tls, allowedRoutes Same) | gateway.yaml | blob 1e1f48a3… |
| HTTPRoute portal → backendRef Service portal:80; Deployment container http=8080, mgmt=8081 | gateway.yaml + deployment.yaml | blob 2cb27165… |
| Candidate policy: Barman controller→5432, API 172.30.140.0/24:6443, S3 172.30.143.10/32:443, DNS podSelector | networkpolicy.yaml | blob fccb8432… |
| MON-9187: monitoring.coreos.com not served, нет Prometheus pod | base R11-13/R1 | inventory.jsonl |

## 2. OD-01 — B1 (DNAT/enforcement) решён документально, без PR-1

CalicoNodeStatus не несёт активного backend (iptables/nftables/eBPF/DSR) и точки DNAT — PR-1 удалён.
Утверждение «iptables/nftables ⇒ ClusterIP pre-DNAT» удалено как недоказанное: K8s 1.36 оставляет
порядок address-rewrite относительно policy implementation-dependent. Противоречие снято: effective
mode и DNAT-представление — разные факты; mode не выводит DNAT-представление, поэтому «per-node
mode не влияет на правила» было неверно сформулировано — mode не влияет на СОДЕРЖАНИЕ selector-правил,
но DNAT-представление влияет на IP-правила, и оно НЕ выводится из mode.

Разделение tuple-ов:
- **API Service tuple**: ClusterIP `default/kubernetes` 10.96.0.1:443 (R2); **API endpoint tuple**:
  172.30.140.101/102/103:6443 (R3). API VIP 172.30.140.100 — отдельная сущность, НЕ смешивать с endpoints.
- **DNS**: представление selector-независимо — podSelector `kube-system` + `k8s-app=kube-dns`
  (резолвится в фактический pod IP в момент оценки). IP-представление (10.96.0.10 / 10.244.254.65/.66)
  не нужно для правила.

Проектное решение B1 (candidate, не apply):
- **DNS-53**: podSelector (как уже в candidate) — representation-robust, закрыт.
- **API-6443**: точный ограниченный вариант, устойчивый к обоим представлениям:
  `ipBlock` 10.96.0.1/32:443 (ClusterIP, pre-DNAT) **и** 172.30.140.101/32, 172.30.140.102/32,
  172.30.140.103/32 :6443 (endpoints, post-DNAT). Это НЕ /24: разрешаются ровно 4 адреса
  (1 ClusterIP + 3 endpoint-узла). Предел дополнительных разрешений: без этого набора pod
  теряет API-доступ при post-DNAT enforcement; набор не открывает никакой иной порт/подсеть.
  При внедрении требуется будущий runtime-допуск на подтверждение одного из представлений
  (см. §8), но правило не блокирует rollout.
- S3/DNS/backend представления Service 80→8080 фиксируются в §4.

## 3. OD-02 — B2 (S3) решён через P7 + Barman-роли, без PR-2

- **Historical resolution**: `s3-backup.demo-pak.test → 172.30.143.10` зафиксировано P7
  (15-dns-after / 09-live-dns-s3-contract / 16-bind-authority). Это факт на момент P7, не сегодня.
- **Freshness**: отделена от отсутствия доказательства — текущее резолвление не проверялось
  заново; нужен precheck на rollout (не new read).
- **Role/direction** (supplemental-design §4): S3-трафик выполняет per-instance **sidecar внутри
  CNPG Pod** (backup/WAL), НЕ controller. Controller `barman-cloud` (cnpg-system) — RPC-сервер 9090,
  вызываемый CNPG operator (control-9090 живёт в cnpg-system, вне CNPG-pod policy).
- **Декомпозиция**: (a) operator→plugin:9090 — cnpg-system internal, в CNPG-pod policy НЕ входит;
  (b) sidecar→S3:443 — egress CNPG Pod (candidate ipBlock 172.30.143.10/32:443 — корректно по P7).
  Controller→DB5432/S3 из наличия сервиса НЕ выводится.
- PR-2 (ippool + DNS с node-01) удалён: IPPool не измеряет S3-достижимость/инициатора; DNS с
  node-01 проверяет resolver/network path node-01, не путь CNPG sidecar. Отдельное чтение IPPool
  не требуется — ни одно его поле не меняет candidate-правило.
- Остаток B2 = только freshness (precheck на rollout), не блокирующий offline-решение.

## 4. OD-03 — B3 (ingress) решён по манифестам

- **Listener** (логический): Gateway `portal-gateway` (namespace `portal`) listener `https`
  port 443, protocol HTTPS, hostname `portal.demo-pak.test`, TLS mode Terminate, certificateRef
  `portal/portal-ui-tls`, allowedRoutes `Same` → HTTPRoute `portal` → backendRef Service `portal` port 80.
- **Backend**: Service `portal` (ClusterIP, selector `app.kubernetes.io/name=pak-portal`) port 80 →
  targetPort `http` = container 8080. Deployment `portal` container `portal` http=8080, mgmt=8081.
- **Dataplane Pod**: namespace `envoy-gateway-system`, labels `gateway.envoyproxy.io/owning-gateway-name=portal-gateway`
  + `gateway.envoyproxy.io/owning-gateway-namespace=portal`.
- **Потоки dataplane** (candidate p8c-portal-dataplane-flows, policyTypes=[Egress]):
  xDS → `envoy-gateway-system` `control-plane=envoy-gateway`:18000; backend → `portal`
  `app.kubernetes.io/name=pak-portal`:8080; DNS → kube-system kube-dns:53.
- **Пробе**: kubelet startup/readiness/liveness на Portal mgmt 8081 (`/startupz` `/readyz` `/livez`)
  — не выходят к dataplane. LB health-check генерируемого Gateway Service (type LB, MetalLB) —
  PLANNED (precheck на rollout). Активного backend health-check в принятой конфигурации нет — не изобретать.
- **Ingress к dataplane**: candidate dataplane-policy — Egress-only, ingress этим объектом НЕ
  ограничен. Внешний listener→dataplane НЕ моделируется в policy (требует будущего design-reшение);
  namespace-wide deny в envoy-gateway-system НЕ вводится.
- **PLANNED (generated-runtime, precheck на rollout)**: фактический containerPort Envoy proxy и
  имя/тип генерируемого Gateway Service, LB IP, owning-label UID.

## 5. OD-04 — union-aware state/rollback (4 стадии)

p8c-cnpg-existing-flows = policyTypes [Ingress,Egress] ⇒ применение СРАЗУ изолирует CNPG Pods.
«Первым до изоляции» неверно: полный allowlist + preconditions должны быть готовы ДО шага 1.

| Стадия | Применяется | Состояние после | Rollback (порядок) |
|---|---|---|---|
| S0 baseline | — | portal: CNPG/др. Pods не ограничены (F-NP пусто на срезе) | — |
| S1 | p8c-cnpg-existing-flows | CNPG изолированы по full-allowlist; др. portal Pods не ограничены | удалить объект → S0 (безопасно) |
| S2 | baseline-default-deny-all + baseline-allow-dns-egress | union: CNPG = existing-flows (полный), др. portal Pods = default-deny+dns | 1) удалить baseline-default-deny-all + allow-dns-egress → S1; 2) удалить existing-flows → S0. НЕ удалять existing-flows первым (иначе CNPG останется под default-deny без egress) |
| S3 | p8c-portal-flows + p8c-migrator-flows | Portal/migrator Pods получают allowlist (вместе с их workloads) | удалить portal/migrator flows + workloads → S2 |
| S4 | p8c-portal-dataplane-flows | dataplane egress allowlist (envoy-gateway-system) | удалить объект → S3 |

- Для каждого нового объекта: до rollout отсутствует; после создания записать UID; в будущем
  execute-gate повторно сверить UID и поставить UID-precondition на удаление; mismatch → STOP без
  удаления чужого объекта.
- Существующие controller/CNPG/Velero/cert-manager/MetalLB не трогать; сохранять независимый
  operator management path (OP-IM-8000 остаётся в allowlist).
- pre/post checks (будущий execute-gate): command/field/time-window/timeout/STOP/rollback. Ready3/3
  и LastBackupSucceeded=True сами по себе НЕ доказывают текущую DNS/API/S3-доступность после изоляции;
  использовать свежесть/reconcile/WAL, НЕ запускать новый backup/restore/PITR/failover или destructive probes.

## 6. OD-05 — 14-flow точная таблица (селекторы, источники, candidate delta)

Сокращения: `pn=podNamespace`, `ps=podSelector` (label key=value), `ns=namespaceSelector`.
`k8s.io/metadata.name` — label на Namespace. Порт указан до/после Service, где различается.

| FLOW-ID | Направление | Селекторы (src → dst) | proto:port | Факт (record/time) | Candidate object/rule | Delta |
|---|---|---|---|---|---|---|
| REP-5432 (EXISTING) | CNPG↔CNPG | ps `cnpg.io/cluster=portal-db`,`cnpg.io/podRole=instance` → same | TCP 5432 | R1 pods 5432; R3 eps | existing-flows ingress+egress 5432 | ✓ aligned |
| IM-8000 (EXISTING) | CNPG↔CNPG | ps `cnpg.io/cluster=portal-db`,`cnpg.io/podRole=instance` → same | TCP 8000 | R1 port 8000 | existing-flows ingress+egress 8000 | ✓ aligned |
| OP-IM-8000 (EXISTING) | operator→CNPG | ns `cnpg-system` + ps `app.kubernetes.io/name=cloudnative-pg` → ps `cnpg.io/cluster=portal-db`,`cnpg.io/podRole=instance` | TCP 8000 | R1 operator | existing-flows ingress 8000 | ✓ aligned |
| BAR-5432 legacy (EXISTING) | operator→plugin; sidecar→S3 | (a) ns `cnpg-system` operator → ps `app=barman-cloud`:9090 (вне CNPG-policy); (b) ps `cnpg.io/cluster=portal-db` sidecar → 172.30.143.10:443 | TCP 9090 (control) / 443 (S3) | S1/S2 identity; P7 S3; suppl-design §4 | existing-flows: sidecar S3 egress 172.30.143.10/32:443 ✓; **controller→5432 ingress — NOT_APPROVED** | удалить controller→5432 |
| MON-9187 | scraper→CNPG (нет источника) | (нет) → ps `cnpg.io/cluster=portal-db` | TCP 9187 | R11-13/R1 NOT_FOUND_IN_SURVEYED_SOURCES | нет | отметить для будущего |
| DNS-53 (EXISTING) | CNPG/Portal/migrator→kube-dns | portal workloads → ns `kube-system` + ps `k8s-app=kube-dns` | UDP+TCP 53 | R2 svc 10.96.0.10; R3 eps | egress podSelector 53 ✓ (representation-robust) | ✓ aligned |
| API-6443 (EXISTING) | CNPG/Portal→API | portal workloads → `default/kubernetes` 10.96.0.1:443 + eps 172.30.140.101/102/103:6443 | TCP 443 (ClusterIP) / 6443 (endpoint) | R2 svc + R3 eps | egress ipBlock **172.30.140.0/24:6443 — NOT_APPROVED (broad /24)** | заменить на 10.96.0.1/32:443 + 172.30.140.101/102/103/32:6443 |
| S3-443 (EXISTING) | sidecar→S3 | ps `cnpg.io/cluster=portal-db` → 172.30.143.10 | TCP 443 | P7 (historical) + C1 endpointURL | egress ipBlock 172.30.143.10/32:443 ✓ | freshness precheck |
| APP-DB-5432 (PLANNED) | Portal→CNPG | ps `app.kubernetes.io/name=pak-portal` → ps `cnpg.io/cluster=portal-db` | TCP 5432 | PLANNED | existing-flows ingress 5432 + portal-flows egress 5432 ✓ | ✓ aligned |
| APP-MET-9187 (PLANNED) | Portal→CNPG | ps `app.kubernetes.io/name=pak-portal` → ps `cnpg.io/cluster=portal-db` | TCP 9187 | PLANNED | ingress 9187 + portal egress 9187 ✓ | ✓ aligned |
| MIG-DB-5432 (PLANNED) | migrator→CNPG | ps `app.kubernetes.io/name=pak-portal-migrator` → ps `cnpg.io/cluster=portal-db` | TCP 5432 | PLANNED | ingress 5432 + migrator egress 5432 ✓ | ✓ aligned |
| ENV-XDS-18000 (PLANNED) | dataplane→control-plane | ns `envoy-gateway-system` + ps `gateway.envoyproxy.io/owning-gateway-name=portal-gateway`,`owning-gateway-namespace=portal` → ns `envoy-gateway-system` + ps `control-plane=envoy-gateway` | TCP 18000 | R1/R2 control-plane 18000 | dataplane egress 18000 ✓ | ✓ aligned |
| ENV-BACK-8080 (PLANNED) | dataplane→Portal | dataplane → ns `portal` + ps `app.kubernetes.io/name=pak-portal` | TCP 8080 (container; Service portal:80→8080) | PLANNED | dataplane egress 8080 + portal ingress (from dataplane) 8080 ✓ | Service DNAT 80→8080 задокументирован |
| ENV-LISTENER (PLANNED) | external→dataplane | external → Gateway portal-gateway listener https:443 (TLS Terminate) | TCP 443 | PLANNED (Gateway class eg R6; dataplane NOT_CREATED R7/R8) | dataplane-policy Egress-only; ingress НЕ моделируется | future design-reшение |

## 7. Candidate delta (NOT_APPROVED, YAML не меняется)

1. **Barman controller→DB5432** (networkpolicy.yaml ingress `cnpg-system` + `app=barman-cloud` → 5432) —
   NOT_APPROVED: по supplemental-design §4 controller = RPC 9090, DB5432 не установлен. Убрать из дизайна.
2. **API 172.30.140.0/24:6443** (egress existing-flows и portal-flows) — NOT_APPROVED (broad /24):
   заменить на точный набор 10.96.0.1/32:443 + 172.30.140.101/102/103/32:6443 (§2).
3. Остальные правила aligned; «полное сохранение существующих потоков» в прежней редакции было
   со ссылкой на несогласованный candidate — отозвано; теперь фиксируется фактический delta.

## 8. Минимальный proposal только для оставшихся свежих фактов (НЕ исполняется)

- **PR-3 (API DNAT представление, post-apply precheck)**: перед/после S1 — один read-only
  `kubectl get endpoints/default/kubernetes` (field: subsets.addresses.ip + ports.port) для
  свежей сверки endpoint-tuple, и подтверждение active enforcement через будущий runtime-допуск
  (Calico NodeStatus не даёт backend — см. §2). Только в будущем execute-gate; сейчас proposal.
- **PR-4 (S3 freshness)**: на rollout — сверить FQDN→IP по P7-зафиксированному контракту
  (POD_DNS_TO_S3/POD_TO_S3_PATH), НЕ новый DNS-проб; resolver/qname/type/source/timeout/attempts/
  allowlisted output/errors/output-limit задаются в execute-gate. Не исполняется.
- Все прочие прежние «PR» удалены. Новый collector НЕ пишется.

## 9. Итоговые поля
```text
TASK=P8C-RV02-OFFLINE-ROLLOUT-DECISION-R1
OD-01..05=RESOLVED (документально)
PR-1/PR-2=REMOVED · PR-3/PR-4=PROPOSAL_ONLY (future execute-gate)
CANDIDATE_DELTA=NOT_APPROVED: Barman controller→5432, API /24 (YAML не менялся)
AUTHORIZED_READ_SET_COMPLETE=YES · FLOW_MATRIX_COMPLETE=NO · EFFECTIVE_POLICY_UNION=UNKNOWN
NETPOL_APPROVED_FOR_APPLY=NO · CI/PRODUCTION=NOT_AUTHORIZED · P8C=NOT_FINAL_ACCEPTED
```
STOP для Architect review.
