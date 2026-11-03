# P8C Runtime-Readiness Gate — DRAFT (NOT_AUTHORIZED_FOR_EXECUTION)

Дата: 2026-11-03. Исполнитель подготовки: PRIMARY HERMES. Status: DRAFT.
METRIC_SOURCE_CHOICE=ACCEPTED_SOURCE_ONLY (cnpg_pg_stat_archiver_*).

```text
RUNTIME_READINESS_GATE=NOT_AUTHORIZED_FOR_EXECUTION
PHASE2_NEW_RUN_APPROVED=NO · NETPOL_APPROVED_FOR_APPLY=NO
DESIGN_CHOICE=OPERATOR_PRIMARY_BOUND_DIRECT_EXPORTER (source-only)
```

## RD-01 — WAL observation (normative DRAFT budget)

Actor/access: авторизованный operator на node-01 (key-only path), НЕ Portal. Binding: named
`portal/portal-db` Cluster `.status.currentPrimary` → named Pod в portal → UID/IP/owner validation →
фиксированный HTTP `Pod IP:9187/metrics`, без redirects. Не infer primary из `cnpg.io/podRole=instance`.
Нет fallback на другой Pod, dynamic retry, exec, port-forward, SQL, Secret read.

**Чтения одного sample (5 запросов, строго по порядку):**
1. GET named Cluster → currentPrimary + Cluster UID.
2. GET named currentPrimary Pod в portal → Pod UID/IP, owner-binding к этому Cluster, container name/restartCount/running.startedAt.
3. HTTP GET fixed Pod IP:9187/metrics (no redirects).
4. GET ТОТ ЖЕ Pod → сравнить identity/IP/container restart/start.
5. GET ТОТ ЖЕ Cluster → сравнить UID/currentPrimary.

Raw response size валидируется ДО персиста; raw objects в evidence не попадают. Metadata projection
ограничена полями выше + name/namespace + required cluster labels. Счётчики/timestamps/reset — из
accepted pg_stat_archiver series.

| Bound | Normative DRAFT value |
|---|---|
| Observation windows | S0, S1, S2a, S2b, S3, S4 — максимум 6 |
| Sample slots в окне | offsets 0, 300, 600s — максимум 3 |
| Per sample | 4 metadata GET + 1 metrics GET = 5 запросов |
| Per request | timeout ≤5s и remaining deadline; один attempt, без retry |
| Per sample deadline | ≤30s (5 запросов ≤25s nominal) |
| Per window hard deadline | 660s от первого slot, monotonic clock |
| Metadata body cap | 256 KiB каждый (до projection) |
| Metric body cap | 1 MiB |
| Per sample body cap | 2 MiB total |
| Per window cap | 15 requests / 6 MiB |
| All six windows cap | 90 requests / 36 MiB / 3960s observation time |
| Total rollout elapsed | observation cap ПЛЮС отдельно bounded action time; НЕ утверждать 3960s |
| Abort | timeout, malformed/nonfinite, missing series, role/UID/IP/restart/reset change → INCONCLUSIVE/STOP |
| Retry distinction | только later planned slots для valid-but-idle; transport/parse failure НЕ retry |

**Verdict:**
- S0 первый valid sample = baseline; later valid slot должен показать fresh natural progress.
- Для каждого post-operation window: retain последний accepted pre-operation sample (same Cluster/Pod
  identity) + записать operation-end UTC. Сравнить failed_count/last_failed_time/reset markers против
  этого retained baseline: рост ошибки побеждает любой рост архивов. Затем require archived_count growth
  И fresh last_archived_time.
- Idle разрешён только до исчерпания оставшихся planned slots, затем INCONCLUSIVE/STOP. Без force WAL/
  writes/backup/искусственного трафика.

**Clock:** future gate должен evidence абсолютный exporter/observer UTC skew bound ≤5s; если неизвестен →
freshness INCONCLUSIVE (без silent clock assumption). PASS: `last_archived_time > operation_end_UTC + 5s`
И `<= sample_end_UTC + 5s` (для S0 — first-sample-end UTC вместо operation-end). Clock evidence сам НЕ
authorized здесь — explicit future gate prerequisite.

Bracketing фиксирует observed changes, не absolute absence transient role change. Не atomic snapshot,
не full S3 readback, не DNS proof. Primary-only — выбранная политика сравнения; archive_mode=always note
остаётся. ContinuousArchiving = ARCH-STATE, отдельно от fresh WAL progress.

## RD-02 — baseline (PR-3/5/6 + HC-*) — без изменений

PR-3/5/6 + HC-* по accepted plan; bounds (request timeout min(15s, remaining W); W=60/30/120s; I=10/5/10s;
N≤6; Gateway W=120s/I=10s/N≤12). NOT_AUTHORIZED. Execution wrapper — отдельный prerequisite.

## Статус
```text
RUNTIME_READINESS_GATE_DRAFT=REVIEW_READY (DRAFT)
METRIC_SOURCE_CHOICE=ACCEPTED_SOURCE_ONLY
ACCESS_METHOD=DESIGN_SELECTED (OPERATOR_PRIMARY_BOUND_DIRECT_EXPORTER) / EXECUTION_NOT_AUTHORIZED
EXTERNAL_PREREQUISITES: clock skew evidence (≤5s bound); безопасный execution wrapper.
PHASE2_NEW_RUN_APPROVED=NO · NETPOL_APPROVED_FOR_APPLY=NO · P8C=NOT_FINAL_ACCEPTED
```
