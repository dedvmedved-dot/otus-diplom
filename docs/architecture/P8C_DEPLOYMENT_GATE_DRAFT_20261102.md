# P8C Deployment Gate — DRAFT (NOT_AUTHORIZED_FOR_EXECUTION)

Дата: 2026-11-02. Исполнитель подготовки: PRIMARY HERMES. Status: DRAFT.
Источники: portal/manifests/{networkpolicy,deployment,gateway}.yaml, P8_PORTAL_DB_CONTRACT.md,
portal/cmd/portal/main.go, portal/internal/httpapi/server.go, принятый offline design.

```text
DEPLOYMENT_GATE=NOT_AUTHORIZED_FOR_EXECUTION
NETPOL_APPROVED_FOR_APPLY=NO · PRODUCTION_MIGRATION_DEPLOYMENT=NOT_AUTHORIZED
```

## Уточнение endpoint (source-derived)

- Management: `/livez`, `/readyz`, `/startupz` на MgmtAddr 8081 (main.go). **`/healthz` отсутствует**.
- API: 11 защищённых Basic-Auth `GET/HEAD` маршрутов (server.go apiRoutes):
  `/api/v1/health`, `/api/v1/summary`, `/api/v1/nodes`, `/api/v1/workloads`, `/api/v1/pods`,
  `/api/v1/services`, `/api/v1/storage`, `/api/v1/backups`, `/api/v1/database`, `/api/v1/metrics`,
  `/api/v1/events`. mgmt 8081 НЕ открывается через внешний Service.

## DEP-01 — порядок и ownership (единый dependency-план)

Prerequisites (до S1):
1. accepted candidate SHA + current baseline/S3/WAL proof (PR-3/6 + HC-ARCH-STATE + RD-01 pg_stat_archiver).
2. accepted CI run + verified source/image digest + private pull readiness (release gate).
3. Owner-provisioned UI auth/pull credentials (безопасный локальный механизм; здесь не запускать).
4. разрешённые RBAC/CA/Service/миграция/Deployment/Gateway объекты и их names/namespaces.

Порядок (каждый шаг — HC-* до/после, UID-precondition):
```text
S0  baseline (условный): spec.instances=3, status.instances=3, status.readyInstances=3, Ready=True
    (по accepted plan); operator Ready; kube-dns ready; PR-6 policy-set freshness.
S1  apply p8c-cnpg-existing-flows → HC-DB/ARCH-STATE/OP/DNS.
S2a apply baseline-default-deny-all; S2b apply baseline-allow-dns-egress.
S3  apply p8c-portal-flows + p8c-migrator-flows (политики ДО workloads) → Deployment/Job;
    migrator ДО application readiness; migration → application readiness.
S4  apply p8c-portal-dataplane-flows → Gateway ПОСЛЕДНИМ. Граница экспозиции — из accepted design:
    риск начинается с создания Gateway; Programmed/LB IP не гарантия отсутствия внешнего доступа;
    cleanup generated Service/Pods (обе owning labels) проверяется ДО снятия dataplane egress.
```

DB contract: `portal-db-rw.portal.svc:5432`, database `portal`, role `portal_app`, schema `portal`,
TLS verify-full, пароль только secretKeyRef. Primary Pod/Pod IP не искать; superuser не выдавать.
Deployment и migration Job — pin ОДНОГО verified image digest; до CI digest = UNAVAILABLE (не fake hex).

Rollback: только вновь созданные объекты по UID-precondition, no-overwrite; S4→S3→S2b→S2a→S1→S0;
default-deny/allow-dns ДО existing-flows; migration без destructive down-SQL; CNPG не трогать;
NetPol rollback НЕ удаляет existing workloads.

## DEP-02 — конечные acceptance критерии (source-derived proposals)

| Proof | Источник / команда | expected | error/STOP | artifact |
|---|---|---|---|---|
| migration success + версия/checksum + schema | `portal migrate` exit + migration ledger (version/checksum) + `VerifySchema` (main.go) | version=0001 + checksum0001 + schema verify | ≠/нет → STOP | migration ledger |
| readiness (не DB TLS proof) | `GET /readyz` (mgmt 8081) | 200 = migration+collector OK | ≠200 → STOP | readyz result |
| DB TLS (verify-full, отдельно от readiness) | pinned config/CA/SNI/no-fallback + observed app DB connection | CONNECTED с verify-full; `ssl=true` ≠ hostname verification | не CONNECTED/no-fallback → STOP | sanitized conn evidence |
| API health | `GET /api/v1/health` (Basic Auth) | 200 | ≠200 → STOP | API capture |
| 11 API responses | 11 маршрутов из server.go (список выше) | каждый 200/expected shape | ≠ → STOP | API matrix |
| UI/assets | `/` + `/assets/*` | 200 + assets served | ≠200 → STOP | UI capture |
| Service/Gateway/HTTPRoute/TLS hostname | Gateway Accepted+Programmed (observedGeneration), PR-5 Service LB IP, hostname portal.demo-pak.test | Accepted+Programmed + LB IP + cert hostname | неоднозначность → STOP | gateway status + PR-5 |
| auth (missing/wrong vs success) | Basic Auth: неверный/отсутствующий credentials → 401; верный → 200 (secret-safe ввод без argv/log) | 401 vs 200 | утечка/неверный → STOP | auth result |
| actual platform data | nodes 3, CNPG 3/3, workloads visible | наблюдаемые данные (не hardcoded) | stale/unknown видимы | platform summary |
| bounded event persistence | event timeline store | bounded, persisted (без создания искусственных K8s событий) | overflow/loss → STOP | event ledger |
| RBAC named ServiceAccount + allowed/denied | SA + verb/resource/scope matrix; authz-only mechanism (без destructive mutation; authorization-review API вызовы в scope явно) | allowed reads OK, denied verbs rejected | mutation прошла → STOP | authz result |
| secret scan | scan затронутых manifests (scanner/version/scope/exit; значения не выводить) | нет secret-значений | hit → STOP | scan report |
| platform postcheck | HC-* набор | PASS/INCONCLUSIVE по правилам | FAIL/INCONCLUSIVE → rollback/STOP | postcheck transcript |

```text
PORTAL_UI=RUNNING
PORTAL_API=RUNNING
PORTAL_DB=CONNECTED (TLS verify-full доказан, отдельно от /readyz)
PLATFORM_STATUS=VISIBLE
PORTAL_URL=<фактически проверенный URL>
```
Будущие runtime-доказательства НЕ подменяются текущими source tests. failover/backup/restore/PITR не повторять.

## Статус
```text
DEPLOYMENT_GATE_DRAFT=REVIEW_READY (DRAFT)
IMAGE_DIGEST=UNAVAILABLE (до CI release; deployment.yaml не правится fake hex)
PRODUCTION_MIGRATION_DEPLOYMENT=NOT_EXECUTED · NETPOL_APPROVED_FOR_APPLY=NO · P8C=NOT_FINAL_ACCEPTED
```
