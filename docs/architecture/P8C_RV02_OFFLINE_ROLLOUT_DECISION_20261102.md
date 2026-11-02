# P8C-RV02-OFFLINE-ROLLOUT-DECISION — единый offline-план развёртывания

Дата: 2026-11-02 (UTC). Исполнитель: PRIMARY HERMES. Только offline-реконсиляция по уже
собранному evidence и закреплённым источникам. Новых live-чтений, доработки collector,
NetworkPolicy apply, CI и production-действий НЕ выполняется.

Authority: docs/architecture/P8C_RV02_ACCEPTANCE_c872eed_20261102.md (reviewed main c872eed).
```text
AUTHORIZED_READ_SET_COMPLETE=YES (9/9 успешных чтений, EXIT=0)
FLOW_MATRIX_COMPLETE=NO
EFFECTIVE_POLICY_UNION=UNKNOWN
NEW_GATE_RUN_BUDGET=CONSUMED
NETPOL_APPROVED_FOR_APPLY=NO · P8C=NOT_FINAL_ACCEPTED
```

## 1. Сводка фактов, на которых строится решение

| Факт | Источник (record/time) | Статус |
|---|---|---|
| 3 calico-node pod в kube-system, identity принят (v3.32.0 + pinned digest) | F-I1, 2026-11-02T09:35:24Z | OBSERVED |
| CNP v1alpha2 схема = пин ff433d34… (compatible=true) | F-CS | OBSERVED |
| CNP / NP / GNP / HEP = 0 объектов (полные пустые списки) | F-CNP/F-NP/F-GNP/F-HEP | OBSERVED (пусто на момент сбора) |
| default FelixConfiguration nftablesMode=Auto (остальные поля null) | F-FELIX | OBSERVED (только default) |
| 3 Tier: default(1000000/Deny), kube-admin(1000/Pass), kube-baseline(10000000/Pass) | F-TIER | OBSERVED (конфигурация, не эффект) |
| 23 Calico API resource descriptors (вкл. status subresource) | F-D1 | OBSERVED (не 23 CRD) |
| CNPG pods: 5432/8000 (репликация/instance-manager), 9187 (metrics) | base R1 | OBSERVED_CONFIG |
| kube-dns 10.96.0.10:53; eps 10.244.254.65/.66 | base R2/R3 | OBSERVED_CONFIG |
| default/kubernetes 10.96.0.1:443→6443; eps 172.30.140.101/102/103:6443 ready | base R2/R3 | OBSERVED_CONFIG; DNAT UNKNOWN |
| S3 ObjectStore endpointURL https://s3-backup.demo-pak.test; destinationPath s3://portal-postgres-backup | Phase-2 C1 | OBSERVED_CONFIG (routing UNKNOWN) |
| barman-cloud sidecar (per-instance) + plugin controller (cnpg-system), 9090 | Phase-2 S1/S2 + R3 | OBSERVED identity; direction UNKNOWN |
| GatewayClass `eg`; Gateways/EnvoyProxies пустые (dataplane NOT_CREATED) | base R6/R7/R8 | OBSERVED / NOT_CREATED |
| monitoring.coreos.com не served; нет Prometheus/Grafana pod | base R11-13/R1 | NOT FOUND |
| kubeadm + kube-vip HA (API VIP), kubeconfig context kubernetes-admin@pak-portal | memory / repo | DOCUMENTARY |

## 2. 14 FLOW-IDs: факт → селекторы → правило → блокирует ли UNKNOWN

Легенда: `EXISTING` — уже работающая нагрузка, требующая ПРИОРИТЕТНОГО сохранения;
`PLANNED` — создаётся при развёртывании; `blocking` — UNKNOWN реально блокирует безопасный apply.

| FLOW-ID | Направление | Селекторы (src → dst) | proto:port | Факт | Правило-кандидат | Блокирующий UNKNOWN |
|---|---|---|---|---|---|---|
| REP-5432 (EXISTING) | CNPG↔CNPG | portal: cnpg.io/cluster=portal-db → same | TCP 5432 | R1 pods 5432; R3 eps | p8c-cnpg-existing-flows | нет (сохранить) |
| IM-8000 (EXISTING) | CNPG↔CNPG | portal: cnpg.io/cluster=portal-db → same | TCP 8000 | R1 port 8000 | p8c-cnpg-existing-flows | нет (сохранить) |
| OP-IM-8000 (EXISTING) | operator→CNPG | cnpg-system: app.kubernetes.io/name=cloudnative-pg → portal: cnpg.io/cluster=portal-db | TCP 8000 | R1 operator + VERSIONED_DESIGN | p8c-cnpg-existing-flows ingress | нет (селектор из pinned manifest) |
| BAR-5432 legacy (EXISTING) | controller→control-9090; sidecar→S3 | cnpg-system/barman-cloud + per-instance sidecar → control endpoint / ObjectStore | TCP 9090 (control); S3 443 (sidecar) | S1/S2 identity + R3 9090; direction UNKNOWN | НЕ валидирован: отделить control от sidecar; без controller→DB5432 | **да**: sidecar S3 route (B2) |
| MON-9187 (нет скрейпера) | scraper→CNPG | (нет источника) → portal: cnpg.io/cluster=portal-db | TCP 9187 | NOT FOUND (R11-13/R1) | не требуется до появления scraper | нет (нет источника; отметить для будущего) |
| DNS-53 (EXISTING) | CNPG/Portal/migrator→kube-dns | portal workloads → kube-system kube-dns | UDP+TCP 53 | R2 svc 10.96.0.10; R3 eps 10.244.254.65/.66 | dns baseline egress | **да**: DNAT-представление (B1) |
| API-6443 (EXISTING) | CNPG/Portal→API | portal workloads → default/kubernetes (10.96.0.1:443→6443) | TCP 6443 | R2 svc + R3 eps 172.30.140.101/102/103 | cnpg/portal egress ipBlock | **да**: DNAT/enforcement point (B1) |
| S3-443 (EXISTING) | CNPG→ObjectStore | portal: cnpg.io/cluster=portal-db → s3-backup.demo-pak.test | TCP 443 | C1 endpointURL/destinationPath; routing UNKNOWN | cnpg egress ipBlock | **да**: IP-резолюция + reachability (B2) |
| APP-DB-5432 (PLANNED) | Portal→CNPG | portal: pak-portal → portal: cnpg.io/cluster=portal-db | TCP 5432 | PLANNED (Portal NOT_CREATED) | p8c-portal-flows | нет (PLANNED) |
| APP-MET-9187 (PLANNED) | Portal→CNPG metrics | portal: pak-portal → portal: cnpg.io/cluster=portal-db | TCP 9187 | PLANNED | p8c-portal-flows | нет (PLANNED) |
| MIG-DB-5432 (PLANNED) | migrator→CNPG | portal: pak-portal-migrator → portal: cnpg.io/cluster=portal-db | TCP 5432 | PLANNED | p8c-migrator-flows | нет (PLANNED) |
| ENV-XDS-18000 (PLANNED) | dataplane→control-plane | envoy-gateway-system (dataplane) → envoy-gateway-system control-plane | TCP 18000 | R1/R2 control-plane 18000; dataplane NOT_CREATED | p8c-portal-dataplane-flows | нет (PLANNED; селекторы из Gateway) |
| ENV-BACK-8080 (PLANNED) | dataplane→Portal | envoy dataplane → portal: pak-portal | TCP 8080 | PLANNED | p8c-portal-dataplane-flows | нет (PLANNED) |
| ENV-LISTENER (PLANNED) | external→dataplane | external → envoy dataplane | listener (не смоделирован) | PLANNED (NOT_CREATED) | NOT modeled | **да**: дизайн listener/backend/health-check (B3) |

## 3. Блокирующие UNKNOWN — конкретный эффект и способ закрытия

### B1 — Service DNAT / enforcement point (API-6443, DNS-53)
Эффект: правило egress должно указывать либо ClusterIP (10.96.0.1:443 / 10.96.0.10:53 —
pre-DNAT, стандартный Calico+kube-proxy), либо endpoint/VIP CIDR (172.30.140.0/24:6443 /
10.244.254.x:53 — post-DNAT). Неверный выбор молча блокирует API/DNS и ломает CNPG.
Класс: не требует наблюдения трафика — определяется активным dataplane-режимом.
Предложение (proposal only): наименьшее чтение `get --raw /apis/crd.projectcalico.org/v1/caliconodestatuses`
(поля: per-node `status`/активный backend iptables|nftables|ebpf|DSR; scope cluster, single GET,
без пагинации, error → STOP). При eBPF/DSR представление меняется; при iptables/nftables —
ClusterIP pre-DNAT. Затрагивает API-6443, DNS-53.

### B2 — S3 endpoint резолюция и достижимость из CNPG (S3-443, BAR-5432 sidecar)
Эффект: ipBlock S3 egress (кандидат 172.30.143.10/32 или /24) не подтверждён — FQDN
`s3-backup.demo-pak.test` должен резолвиться в IP, достижимый из pod-сети (10.244.x), а не
через отдельный Service. Также не разделены направления sidecar→S3 vs controller→S3.
Класс: частично документарный (pinned BIND9 demo-pak.test zone в репозитории), частично live.
Предложение: (a) документарно сверить закреплённую BIND9-зону на A-запись s3-backup; (b) при
необходимости одно наименьшее чтение `get --raw /apis/crd.projectcalico.org/v1/ippools` +
один read-only DNS-запрос с node-01 (proposal only, требует отдельного допуска). Затрагивает S3-443, BAR-5432.

### B3 — ENV-LISTENER дизайн (внешний ingress)
Эффект: внешний listener→dataplane не смоделирован; до явного описания listener/backend/
health-check нельзя валидировать ingress-правило и порядок допуска внешнего трафика.
Класс: проектное решение (не live-данные). Закрывается offline-проектированием, не чтением.

### Не-блокирующие (задокументировать, не запрашивать чтения)
- Per-node Felix mode (только default Auto) — влияет на траблшутинг, не на содержимое правил.
- MON-9187 — нет скрейпера, правило не требуется до его появления.
- BAR-5432 controller→DB5432 — НЕ предполагается и не выводится из 9090.

## 4. Порядок развёртывания и отката (план, apply НЕ авторизован)

Предварительные условия (prerequisites):
1. supply-chain/auth readiness (R3/R4 по D1/R2) закрыта;
2. B1 (DNAT-представление) и B2 (S3-резолюция) закрыты документарно/минимальным чтением;
3. B3 (ENV-LISTENER) спроектирован явно.

Порядок (каждый шаг — read-only health-check после apply):
1. **p8c-cnpg-existing-flows** (portal) — ПОЛНОЕ сохранение существующих CNPG-потоков
   (REP-5432, IM-8000, OP-IM-8000, DNS-53, API-6443, S3-443, control-9090) ПЕРВЫМ и до любой изоляции.
   Health-check: CNPG Ready 3/3, WAL/архив, BSL; деградация → немедленный rollback только этого объекта.
2. **baseline-default-deny-all** + **baseline-allow-dns-egress** (portal) — только после (1).
3. **p8c-portal-flows** (portal) + **p8c-migrator-flows** (portal) — ДО создания Portal/migrator workloads.
4. **p8c-portal-dataplane-flows** (envoy-gateway-system) — ДО допуска внешнего трафика.

Откат (только вновь созданные объекты, по UID/имени):
- Зафиксировать имена/UID до rollout; существующий объект с тем же именем → STOP (не перезаписывать).
- Откат удаляет ТОЛЬКО объекты этого rollout (перечень из PLAN.md D1); никогда не трогать существующие controller/CNPG/Velero/cert-manager/MetalLB.
- STOP-условия: любой health-check degradation, несовпадение UID, имя уже существует, неразрешённый B1/B2/B3.

## 5. Stale-факты, требующие precheck перед rollout (без перезапуска принятых тестов)
- Актуальный IP-состав API endpoints (172.30.140.101/102/103) и S3 VM (172.30.143.10) на момент rollout.
- Актуальность FQDN s3-backup.demo-pak.test → IP (не менять BIND9, только сверить).
- Наличие новых объектов NP/GNP/CNP/HEP после 2026-11-02T09:35Z (текущие списки пусты).
- Появление Prometheus/скрейпера (сейчас NOT FOUND) до включения MON-9187.

## 6. Трассируемость requirement → fact → source → decision → gate
| Requirement | Fact | Source | Decision | Оставшийся gate |
|---|---|---|---|---|
| Сохранить существующие CNPG-потоки | REP/IM/OP/DNS/API/S3 config | base R1-R3, F-* | p8c-cnpg-existing-flows первым | B1, B2 |
| Не изолировать CNPG без полного allowlist | CNP/NP/GNP/HEP пусты | F-CNP/F-NP/F-GNP/F-HEP | порядок (1)→(2) | apply-допуск |
| Portal/migrator только после baseline | Portal/migrator NOT_CREATED | base + PLANNED | шаги 3-4 | deploy-допуск |
| Внешний ingress явно | GatewayClass eg, dataplane NOT_CREATED | base R6-R8 | B3 дизайн | design-допуск |

## 7. Итоговые поля
```text
TASK_ID=P8C-RV02-OFFLINE-ROLLOUT-DECISION
AUTHORIZED_READ_SET_COMPLETE=YES · FLOW_MATRIX_COMPLETE=NO · EFFECTIVE_POLICY_UNION=UNKNOWN
BLOCKING_UNKNOWNS=B1(DNAT API/DNS), B2(S3 resolution+reachability), B3(ENV-LISTENER design)
SMALLEST_READ_PROPOSAL=PR-1(caliconodestatuses), PR-2(ippools+DNS) — PROPOSAL ONLY, NOT AUTHORIZED
ROLLOUT_ORDER=cnpg-existing-flows → baseline-deny → portal/migrator → dataplane
ROLLBACK=only newly-created UIDs; preexisting name → STOP
NETPOL_APPROVED_FOR_APPLY=NO · CI/PRODUCTION=NOT_AUTHORIZED
P8C=NOT_FINAL_ACCEPTED · P8D–P8G/P9=NOT_AUTHORIZED
```
STOP для Architect review. Кандидатный policy-YAML не изменялся.
