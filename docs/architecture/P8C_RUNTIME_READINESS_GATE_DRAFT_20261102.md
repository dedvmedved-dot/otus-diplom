# P8C Runtime-Readiness Gate — DRAFT (NOT_AUTHORIZED_FOR_EXECUTION)

Дата: 2026-11-03. Исполнитель подготовки: PRIMARY HERMES. Status: DRAFT.
METRIC_SOURCE_CHOICE=ACCEPTED_SOURCE_ONLY (cnpg_pg_stat_archiver_*).

```text
RUNTIME_READINESS_GATE=NOT_AUTHORIZED_FOR_EXECUTION
PHASE2_NEW_RUN_APPROVED=NO · NETPOL_APPROVED_FOR_APPLY=NO
```

## RD-01 — WAL observation (cnpg_pg_stat_archiver_*) — числа и verdict

Series (CNPG v1.30.1 default-monitoring.yaml, blob 91fc65b07b0b69c218c6eb407df004b808b510f7):
`cnpg_pg_stat_archiver_archived_count`, `_failed_count`, `_last_archived_time`, `_last_failed_time`, `_stats_reset_time`.

| Аспект | Значение (проектное, source-only) |
|---|---|
| endpoint (source-backed) | `http://portal-db-metrics.portal.svc:9187/metrics` (config.go default `MetricsServiceURL`; P8B historical HTTP). TLS в текущей конфигурации НЕ доказан → CA/SNI не изобретать; future compatibility: если endpoint станет TLS, verify без opportunistic HTTP fallback / verify=false, несовпадение → STOP |
| actor | основной Hermes через принятый key-only operator path (не Portal Pod-IP) |
| per-request timeout | 5s (metrics.go) |
| max body / total bytes | 1 MiB на ответ (metrics.go) / ≤ 5 MiB всего |
| N (samples) | 2 на стадию: baseline (до) + post-step (после); максимум 3 при неоднозначности |
| W (hard deadline) | 5s на запрос; общая стадия-срок = deployment stage, не отдельный wall-clock |
| I (interval baseline→post) | max(300s, длительность стадии), верхняя граница 600s (archive_timeout=300s; без бесконечного ожидания) |
| freshness | last_archived_time сравнивается с baseline-значением этапа (не с GET-time) |
| verdict PASS | archived_count вырос И last_archived_time > baseline last_archived_time |
| verdict FAIL | failed_count вырос ИЛИ last_failed_time продвинулся (не маскировать за ростом archived_count) |
| parse error/NaN | INCONCLUSIVE (не PASS, не FAIL) |
| HTTP/network timeout | INCONCLUSIVE (retry в пределах W, затем INCONCLUSIVE) |
| counter reset (stats_reset_time изменился) | INCONCLUSIVE (series restarted) |
| role/UID/restart change | INCONCLUSIVE (backend сменился, не сравнивать как одну series) |
| idle (нет роста) | INCONCLUSIVE/STOP (не force WAL, не бесконечное ожидание) |
| запрет | без искусственного WAL switch/write/backup |

Стабильный backend между samples обязателен. archive_command = ограниченный proxy результата
архивирования, НЕ независимый S3 readback и НЕ DNS proof; DNS resolution и S3-operation — разные факты.

**ACCESS_METHOD=UNRESOLVED** (частично): endpoint и series определены, но привязка к стабильному
primary backend не решена. Метрика pg_stat_archiver meaningful только на primary; Service
`portal-db-metrics` (selector `cnpg.io/cluster=portal-db`, deployment.yaml, PLANNED) round-robins и
НЕ дискриминирует primary. Точный вопрос для Architect/Owner: механизм primary-bound metrics read —
(a) первичный-selector Service/EndpointSlice, либо (b) operator-side read primary Pod metrics —
без Portal Pod-IP pinning (DB contract) и без нового collector. До этого выбора read остаётся NOT_AUTHORIZED;
все bounds/verdict/series выше завершены независимо.

## RD-02 — baseline (PR-3/5/6 + HC-*), без изменений

PR-3/5/6 и HC-DB/ARCH-STATE/WAL-PROGRESS/OP/DNS/PORTAL/GW — по accepted plan; численные bounds
наследуются (request timeout min(15s, remaining W); W=60/30/120s; I=10/5/10s; N=6; Gateway 120s×12).
Эти проверки остаются NEW_PROPOSAL / NOT_AUTHORIZED. Execution wrapper — отдельный prerequisite.

## Статус
```text
RUNTIME_READINESS_GATE_DRAFT=REVIEW_READY (DRAFT)
METRIC_SOURCE_CHOICE=ACCEPTED_SOURCE_ONLY
S3_WAL_OBSERVATION_METHOD=SOURCE_BOUND_PROPOSAL (bounds/verdict заполнены)
ACCESS_METHOD=UNRESOLVED (primary-bound metrics read path; точный вопрос выше)
EXTERNAL_PREREQUISITES: primary-bound metrics binding; безопасный execution wrapper.
PHASE2_NEW_RUN_APPROVED=NO · NETPOL_APPROVED_FOR_APPLY=NO · P8C=NOT_FINAL_ACCEPTED
```
