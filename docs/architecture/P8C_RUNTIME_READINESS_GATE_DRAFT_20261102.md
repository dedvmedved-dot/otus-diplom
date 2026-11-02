# P8C Runtime-Readiness Gate — DRAFT (NOT_AUTHORIZED_FOR_EXECUTION)

Дата: 2026-11-02. Исполнитель подготовки: PRIMARY HERMES. Status: DRAFT.
Опирается на принятый offline design (docs/architecture/P8C_RV02_OFFLINE_ROLLOUT_DECISION_20261102.md).

```text
RUNTIME_READINESS_GATE=NOT_AUTHORIZED_FOR_EXECUTION
PHASE2_NEW_RUN_APPROVED=NO · NETPOL_APPROVED_FOR_APPLY=NO
```

## RD-01 — источник свежего естественного S3/WAL-архивирования (source-bound)

Исследовано offline по pinned CNPG v1.30.1 (CNPG-TYPES) и Barman Cloud v0.13.0 (BARMAN-TYPES):

- `Cluster.status.conditions[type=ContinuousArchiving]` — **состояние** (True/False), НЕ timestamp/counter
  свежей доставки WAL. Подходит только для «нет новой ошибки» (HC-ARCH-STATE), не для прогресса.
- `Cluster.status.firstRecoverabilityPoint` — **deprecated** и НЕ заполняется для backup-плагинов;
  это самая ранняя точка восстановления, а не последний архивированный WAL. НЕ использовать.
- `Cluster.status.lastSuccessfulBackup`/`lastFailedBackup` — про backup, не про WAL-архивирование.
- CNPG operator публикует Prometheus-метрики (`/metrics`), НО `monitoring.coreos.com` не served и
  скрейпера нет (INV R11-13/R1). Свежий timestamp/counter успешного архивирования доступен только
  через metrics endpoint, которого в текущем окружении нет.

Вывод: **в разрешённом read-only API свежего источника прогресса WAL-архивирования нет**.
`S3_WAL_OBSERVATION_METHOD=SOURCE_BOUND_PROPOSAL`:
- HC-ARCH-STATE (state/no-new-error) — доступно через `ContinuousArchiving` condition.
- HC-WAL-PROGRESS (fresh timestamp/counter) — НЕ доступно; требует либо (a) появления скрейпера
  CNPG-метрик (внешнее условие), либо (b) отдельного runtime-допуска на чтение метрик/логов sidecar.
- DNS resolution и успешность S3-operation — **разные факты**; одно не доказывает другое.
- firstRecoverabilityPoint, старый LastBackupSucceeded, node-DNS — НЕ использовать как Pod→S3 proof.

Это runtime verification dependency; НЕ утверждение «источника нет в продукте». До её отдельного
решения S1 не начинается (по принятому плану). Новых collector/probe/exec/log НЕ создавать.

## RD-02 — текущий baseline (PR-3/5/6 + HC-* из принятого плана)

PR-3/5/6 и HC-DB/ARCH-STATE/WAL-PROGRESS/OP/DNS/PORTAL/GW из принятого плана не перепроектируются.
Какие нужны ДО политики, какие ПОСЛЕ создания объекта:

| Проверка | Когда | Future pinned read mechanism | Статус |
|---|---|---|---|
| PR-6 policy/label-set freshness | ДО S1 (baseline) | 9 raw GVR paths (P6-KNP..P6-PODS) | NEW_PROPOSAL / NOT_AUTHORIZED |
| PR-3 API endpoint-tuple freshness | ДО S1 | EndpointSlice discovery.k8s.io/v1 | NEW_PROPOSAL / NOT_AUTHORIZED |
| HC-DB / HC-ARCH-STATE / HC-OP / HC-DNS | S0–S4 (до/после каждого шага) | raw CNPG/pods/endpointslices | NEW_PROPOSAL / NOT_AUTHORIZED |
| HC-WAL-PROGRESS | до S1 и каждого шага | отсутствует (RD-01) | UNRESOLVED dependency |
| PR-5 dataplane Service | ПОСЛЕ создания Gateway (S4) | raw Service list (both owning labels) | NEW_PROPOSAL / NOT_AUTHORIZED |
| HC-GW | ПОСЛЕ создания Gateway (S4) | raw Gateway | NEW_PROPOSAL / NOT_AUTHORIZED |

Готового безопасного execution wrapper (обработка raw body в памяти, typed projection, sanitization,
STOP-семантика) в этом задании нет — честно указывается как отдельный prerequisite; универсальный
collector не реализуется. Read-set НЕ выдаётся за effective policy union. Старые evidence dates не
обновляются и freshness не продлевается чтением Git.

## Статус
```text
RUNTIME_READINESS_GATE_DRAFT=REVIEW_READY (DRAFT)
S3_WAL_OBSERVATION_METHOD=SOURCE_BOUND_PROPOSAL (HC-ARCH-STATE available; HC-WAL-PROGRESS UNRESOLVED)
EXTERNAL_PREREQUISITES: CNPG-metrics scraper (или отдельный runtime-допуск на sidecar logs/metrics);
                       безопасный execution wrapper для PR-3/5/6 + HC-* чтений.
PHASE2_NEW_RUN_APPROVED=NO · NETPOL_APPROVED_FOR_APPLY=NO · P8C=NOT_FINAL_ACCEPTED
```
