# P8C Runtime-Readiness Gate — DRAFT (NOT_AUTHORIZED_FOR_EXECUTION)

Дата: 2026-11-02. Исполнитель подготовки: PRIMARY HERMES. Status: DRAFT.
Опирается на принятый offline design (docs/architecture/P8C_RV02_OFFLINE_ROLLOUT_DECISION_20261102.md).

```text
RUNTIME_READINESS_GATE=NOT_AUTHORIZED_FOR_EXECUTION
PHASE2_NEW_RUN_APPROVED=NO · NETPOL_APPROVED_FOR_APPLY=NO
```

## RD-01 — источник свежего естественного WAL-архивирования (source-bound)

Отсутствие Prometheus НЕ означает отсутствие metrics endpoint. Принятый P8B доказал endpoint
PostgreSQL instance `9187/metrics` (postgres container); sidecar plugin-barman-cloud метрики слиты в
тот же instance-manager endpoint (evidence/P8/20261020T052255Z-…/11-barman-metrics-endpoint-discovery.md,
blob 6fe4745774f0eac12fece655c69a6f312a6d73ec). portal/internal/collectors/metrics.go (blob
73cb6a887f615ee0bcbc1067397e924b1b53a829) выполняет прямой HTTP scrape, без обязательного Prometheus.

CNPG v1.30.1 config/manager/default-monitoring.yaml (blob 91fc65b07b0b69c218c6eb407df004b808b510f7)
закрепляет pg_stat_archiver-запрос с series:
- `cnpg_pg_stat_archiver_archived_count`
- `cnpg_pg_stat_archiver_failed_count`
- `cnpg_pg_stat_archiver_last_archived_time`
- `cnpg_pg_stat_archiver_last_failed_time`
- `cnpg_pg_stat_archiver_stats_reset_time`
(predicate: primary либо archive_mode=always).

Три `barman_*` backup timestamp из P8B НЕ являются доказательством свежего WAL и НЕ подменяют
pg_stat_archiver. firstRecoverabilityPoint — deprecated и не заполняется для плагинов.

**Единый минимальный source-bound proposal (PROPOSAL_ONLY / NOT_AUTHORIZED):**
| Аспект | Значение |
|---|---|
| actor / access | read-only HTTP GET, без argv-секретов; транспорт как metrics.go (no redirects, 5s timeout, 1MiB cap) |
| endpoint discovery | CNPG instance Pod metrics `9187/metrics`; binding к **primary** instance по UID/роли (не случайный Service endpoint) |
| transport/TLS/CA | ClusterIP-метрики; точный CA/SNI закрепляется в future execute-gate, не здесь |
| series | ровно пять `cnpg_pg_stat_archiver_*` (mapping сверен с default-monitoring.yaml) |
| fresh natural progress | `last_archived_time` (timestamp) + `archived_count` (counter): рост между baseline/post-sample = свежий архив |
| bounds | ≤N GET, window W, interval I (как принятый HC-*): max bytes/requests задаются в execute-gate |
| reset/restart/role change | `stats_reset_time` изменился / backend сменился / counter уменьшился → INCONCLUSIVE, не сравнивать как одну series |
| error/idle | `-1`/отсутствие series/last_archived_time без роста → INCONCLUSIVE (не PASS, не FAIL) |
| запрет | без искусственного WAL switch/write/backup |

Стабильный backend между samples обязателен (случайные endpoints одного Service нельзя сравнивать).
Успешный `archive_command` — ограниченный proxy результата архивирования, НЕ независимый S3 readback
и НЕ DNS proof. DNS resolution и успешность S3-operation — разные факты.

Разделение: наличие в продукте (доказано P8B/upstream) ≠ исторический endpoint ≠ текущая доступность
и экспорт конкретных families (ещё NOT_EXECUTED). Если точный access path нельзя выбрать по источникам,
назвать именно недостающий механизм/допуск (сейчас: точный CA/SNI + execute-gate wrapper).

## RD-02 — текущий baseline (PR-3/5/6 + HC-* из принятого плана)

PR-3/5/6 и HC-DB/ARCH-STATE/WAL-PROGRESS/OP/DNS/PORTAL/GW из принятого плана не перепроектируются.

| Проверка | Когда | Future pinned read mechanism | Статус |
|---|---|---|---|
| PR-6 policy/label-set freshness | ДО S1 (baseline) | 9 raw GVR paths (P6-KNP..P6-PODS) | NEW_PROPOSAL / NOT_AUTHORIZED |
| PR-3 API endpoint-tuple freshness | ДО S1 | EndpointSlice discovery.k8s.io/v1 | NEW_PROPOSAL / NOT_AUTHORIZED |
| HC-DB / HC-ARCH-STATE / HC-OP / HC-DNS | S0–S4 | raw CNPG/pods/endpointslices | NEW_PROPOSAL / NOT_AUTHORIZED |
| HC-WAL-PROGRESS | до S1 и каждого шага | `cnpg_pg_stat_archiver_*` на instance 9187/metrics (RD-01) | PROPOSAL_ONLY / NOT_AUTHORIZED |
| PR-5 dataplane Service | ПОСЛЕ создания Gateway (S4) | raw Service list (both owning labels) | NEW_PROPOSAL / NOT_AUTHORIZED |
| HC-GW | ПОСЛЕ создания Gateway (S4) | raw Gateway | NEW_PROPOSAL / NOT_AUTHORIZED |

Готового безопасного execution wrapper нет — честно указывается отдельным prerequisite. Read-set не
выдаётся за effective policy union. Старые evidence dates не обновляются чтением Git.

## Статус
```text
RUNTIME_READINESS_GATE_DRAFT=REVIEW_READY (DRAFT)
S3_WAL_OBSERVATION_METHOD=SOURCE_BOUND_PROPOSAL
  (cnpg_pg_stat_archiver_* via instance 9187/metrics, direct scrape, primary-bound)
EXTERNAL_PREREQUISITES: точный CA/SNI для metrics endpoint; безопасный execution wrapper
                       для PR-3/5/6 + HC-* + pg_stat_archiver чтений.
PHASE2_NEW_RUN_APPROVED=NO · NETPOL_APPROVED_FOR_APPLY=NO · P8C=NOT_FINAL_ACCEPTED
```
