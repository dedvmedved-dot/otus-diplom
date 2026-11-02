# P8C Deployment Gate — DRAFT (NOT_AUTHORIZED_FOR_EXECUTION)

Дата: 2026-11-02. Исполнитель подготовки: PRIMARY HERMES. Status: DRAFT.
Источники: portal/manifests/{networkpolicy,deployment,gateway}.yaml, P8_PORTAL_DB_CONTRACT.md,
принятый offline design (S0–S4, UID-precondition rollback).

```text
DEPLOYMENT_GATE=NOT_AUTHORIZED_FOR_EXECUTION
NETPOL_APPROVED_FOR_APPLY=NO · PRODUCTION_MIGRATION_DEPLOYMENT=NOT_AUTHORIZED
```

## DEP-01 — порядок и ownership (единый dependency-план)

Prerequisites (до S1):
1. accepted candidate SHA + current baseline/S3/WAL proof (PR-3/6 + HC-ARCH-STATE; HC-WAL-PROGRESS unresolved → S1 заблокирован).
2. accepted CI run + verified source/image digest + private pull readiness (release gate).
3. Owner-provisioned UI auth/pull credentials (только безопасный локальный механизм; здесь не запускать).
4. разрешённые RBAC/CA/Service/миграция/Deployment/Gateway объекты и их names/namespaces.

Порядок (каждый шаг — HC-* проверка до/после, UID-precondition на rollback):
```text
S0  baseline (условный): CNPG readyInstances=3/3/3, operator Ready, kube-dns ready; PR-6 policy-set freshness.
S1  apply p8c-cnpg-existing-flows (полный CNPG allowlist) → HC-DB/ARCH-STATE/OP/DNS.
S2a apply baseline-default-deny-all → union: CNPG не сужается.
S2b apply baseline-allow-dns-egress.
S3  apply p8c-portal-flows + p8c-migrator-flows (политики ДО workloads) → затем Deployment/Job.
    migrator ДО application readiness; migration → application readiness.
S4  apply p8c-portal-dataplane-flows → затем Gateway ПОСЛЕДНИМ (после TLS/auth/backend prerequisites).
```

DB contract (без изменений): `portal-db-rw.portal.svc:5432`, database `portal`, role `portal_app`,
schema `portal`, TLS verify-full, пароль только `secretKeyRef` (portal-db-app). Primary Pod/Pod IP не
искать; superuser не выдавать. Deployment и migration Job — pin ОДНОГО verified image digest; до CI
digest держать UNAVAILABLE (не подставлять fake hex в deployment.yaml).

Rollback: только вновь созданные объекты по UID-precondition, no-overwrite; порядок S4→S3→S2b→S2a→S1→S0;
default-deny/allow-dns снимать ДО existing-flows; migrations НЕ откатывать произвольным destructive SQL;
CNPG инфраструктуру не трогать. NetPol-scope и deployment-scope остаются отдельными.

## DEP-02 — конечные acceptance критерии (matrix: proof → command/endpoint → expected → error/STOP → artifact)

| Proof | command/endpoint | expected | error/STOP | artifact |
|---|---|---|---|---|
| migration ledger/schema | migrator Job `migrate` exit + ledger row | exit 0, schema `portal` в ledger | ≠0/отсутствие → STOP | migration ledger artifact |
| DB TLS | Portal `/readyz` (mgmt 8081) с TLS verify-full к portal-db-rw | CONNECTED (verify-full доказан) | не CONNECTED → STOP | readyz result |
| API health | `GET /healthz`, `/readyz` | 200, RUNNING | ≠200 → STOP | API health capture |
| UI/assets | Portal `/` + static assets | 200, assets served | ≠200 → STOP | UI capture |
| Service/Gateway/HTTPRoute/TLS hostname | Gateway Accepted+Programmed (observedGeneration), PR-5 Service LB IP, TLS hostname portal.demo-pak.test | Accepted+Programmed, LB IP, cert hostname match | неоднозначность/≠ → STOP | gateway status + PR-5 |
| 11 API responses | 11 read-only endpoints (platform API contract R0 sources) | каждый 200/expected shape | ≠ → STOP | API response matrix |
| actual platform data | nodes 3, CNPG 3/3, workloads visible | наблюдаемые данные (не hardcoded) | stale/unknown видимы | platform summary |
| bounded event persistence | event timeline store | bounded, persisted | overflow/loss → STOP | event ledger |
| RBAC allowed reads / denied mutations | authz-test: denied verbs (без реальной mutation) | allowed reads OK, denied verbs rejected | mutation прошла → STOP | authz result |
| secret scan | scan затронутых manifests | нет secret-значений | hit → STOP | scan report |
| platform postcheck | HC-* набор | PASS/INCONCLUSIVE по правилам | FAIL/INCONCLUSIVE → rollback/STOP | postcheck transcript |

```text
PORTAL_UI=RUNNING
PORTAL_API=RUNNING
PORTAL_DB=CONNECTED (TLS verify-full доказан)
PLATFORM_STATUS=VISIBLE
PORTAL_URL=<фактически проверенный URL>
```
Это будущие критерии, НЕ текущий результат. failover/backup/restore/PITR не повторять.

## Статус
```text
DEPLOYMENT_GATE_DRAFT=REVIEW_READY (DRAFT)
IMAGE_DIGEST=UNAVAILABLE (до CI release; deployment.yaml не правится fake hex)
PRODUCTION_MIGRATION_DEPLOYMENT=NOT_EXECUTED · NETPOL_APPROVED_FOR_APPLY=NO · P8C=NOT_FINAL_ACCEPTED
```
