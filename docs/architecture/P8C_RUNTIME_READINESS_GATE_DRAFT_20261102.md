# P8C Runtime-Readiness Gate — DRAFT (NOT_AUTHORIZED_FOR_EXECUTION)

Дата: 2026-11-03. Исполнитель подготовки: PRIMARY HERMES. Status: DRAFT.
METRIC_SOURCE_CHOICE=ACCEPTED_SOURCE_ONLY (cnpg_pg_stat_archiver_*).

```text
RUNTIME_READINESS_GATE=NOT_AUTHORIZED_FOR_EXECUTION
PHASE2_NEW_RUN_APPROVED=NO · NETPOL_APPROVED_FOR_APPLY=NO
```

## RD-01 — WAL observation: DESIGN_SELECTED / EXECUTION_NOT_AUTHORIZED

```text
DESIGN_CHOICE=OPERATOR_PRIMARY_BOUND_DIRECT_EXPORTER
ACCESS_METHOD=DESIGN_SELECTED / EXECUTION_NOT_AUTHORIZED
```

- actor: авторизованный operator на node-01 (НЕ Portal application), через принятый key-only path.
- binding: named `portal/portal-db` Cluster `.status.currentPrimary` → named Pod в portal → валидация
  cluster identity/UID/текущего Pod IP → фиксированный HTTP `9187/metrics`. Каждый metric-sample
  обрамляется metadata GET (Cluster + Pod); role/UID/IP/restart/reset change инвалидирует сравнение.
- transport: HTTP (source-backed, config.go MetricsServiceURL + P8B). TLS НЕ подразумевается; DB TLS
  contract (Service:5432 verify-full) НЕ ослабляется. Без redirects/exec/port-forward/SQL/new
  Service/new collector/Secret read. Connectivity failure = INCONCLUSIVE/STOP (без альтернативных путей).

**Согласованный бюджет (одна таблица):**

| Параметр | Значение |
|---|---|
| stages | S0 (baseline) + S1, S2a, S2b, S3, S4 (post-step) = 6 |
| samples | 1 metric sample/stage = 6 metric GET; 2 metadata GET (Cluster+Pod) на sample = 12 metadata GET |
| total GET | 18 (12 metadata + 6 metrics) |
| per-request timeout | 5s (metrics + metadata) |
| per-stage hard deadline | 30s (от первого metadata GET до завершения metric GET) |
| retry | НЕТ (каждый GET один attempt; timeout → INCONCLUSIVE/STOP стадии) |
| max body | metadata GET ≤ 256 KiB (typed projection), metric GET ≤ 1 MiB |
| total bytes | 6×1 MiB + 12×256 KiB = 9 MiB |
| total wall-time | ≤ 6 × 30s = 180s (при последовательных стадиях) |
| projected metadata | Cluster: name/uid/status.currentPrimary/conditions; Pod: name/uid/labels(role)/status.podIP/status.containerStatuses |

**Verdict (серии cnpg_pg_stat_archiver_*):**
- PASS: archived_count вырос И last_archived_time > baseline-значение этапа, И last_archived_time
  свидетельствует о СВЕЖЕМ post-step архиве (GET-time ≠ archive-time; clock/freshness tolerance: last_archived_time
  в пределах (baseline, now], иначе INCONCLUSIVE).
- FAIL: failed_count вырос ИЛИ last_failed_time продвинулся (не маскировать за ростом archived_count).
- INCONCLUSIVE/STOP: parse error/NaN; HTTP/network timeout; stats_reset_time изменился; role/UID/restart;
  idle (нет роста — не force WAL, не бесконечное ожидание).
- primary-only sampling — выбранная политика сравнения; pinned query также допускает archive_mode=always
  (не утверждать «meaningful ТОЛЬКО на primary»). CNPG ARCH-STATE остаётся отдельным от свежего WAL progress.
- archive_command = ограниченный proxy; НЕ независимый S3 readback, НЕ DNS proof.

## RD-02 — baseline (PR-3/5/6 + HC-*) — без изменений

PR-3/5/6 + HC-* по accepted plan; bounds наследуются (request timeout min(15s, remaining W); W=60/30/120s;
I=10/5/10s; N≤6; Gateway W=120s/I=10s/N≤12 в одном окне). NOT_AUTHORIZED. Execution wrapper — отдельный prerequisite.

## Статус
```text
RUNTIME_READINESS_GATE_DRAFT=REVIEW_READY (DRAFT)
METRIC_SOURCE_CHOICE=ACCEPTED_SOURCE_ONLY
ACCESS_METHOD=DESIGN_SELECTED (OPERATOR_PRIMARY_BOUND_DIRECT_EXPORTER) / EXECUTION_NOT_AUTHORIZED
EXTERNAL_PREREQUISITES: безопасный execution wrapper (metadata+metric GET projection).
PHASE2_NEW_RUN_APPROVED=NO · NETPOL_APPROVED_FOR_APPLY=NO · P8C=NOT_FINAL_ACCEPTED
```
