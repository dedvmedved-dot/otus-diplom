# P8C Portal MVP — матрица доказательств результатов §6 (ПОДГОТОВКА, НЕ ИСПОЛНЕНИЕ)

Дата: 2026-11-19, Europe/Moscow.
Исполнитель подготовки: PRIMARY HERMES (engineer, assignee `hermes-5.187.1.37-engineer`).
Тип документа: матрица доказательств (AUTHOR_PROPOSAL), НЕ допуск на исполнение.

Основание: Forgejo #16 (решение владельца по §4.4 tri-state), PR #6
`docs(p8c): CI release gate spec` @ `1b2276673a301c2b04f420a2000a22245c833265`
(ветвь `p8c-ci-release-gate-spec`, base `main`).

```text
EVIDENCE_MATRIX = REVIEW_READY (AUTHOR_PROPOSAL)
PORTAL_UI / PORTAL_API / PORTAL_DB / PLATFORM_STATUS = STATIC_ONLY / RUNTIME_NOT_OBSERVED
RELEASE / SEED / WORKFLOW_PUBLICATION / DISPATCH = NOT_AUTHORIZED
LIVE_READINESS / NETWORKPOLICY_APPLY / DEPLOYMENT = FORBIDDEN
P8C = NOT_FINAL_ACCEPTED   (переход к P8D не разрешён)
```

## 1. Метод и соглашения

1. **Static-only.** Настоящий документ составлен ТОЛЬКО чтением исходников на принятом
   source и подготовкой текста. Никакой helper/pins не правился, workflow не публиковался,
   dispatch/release/seed/live-readiness/NetworkPolicy apply/deployment не выполнялись.

2. **SHA = git blob SHA-1** (40 hex, объектный SHA содержимого файла), снятый с принятого
   source `d22aa8f1170deaf09580518916ea02c7c4d8bfba` (Forgejo `origin/main`). Это НЕ SHA
   коммита и НЕ sha256 (sha256 для gate-помощников закреплён отдельно в §1.2 спеки PR #6).
   Любое байтовое изменение файла меняет blob SHA и инвалидирует ссылку.

3. **Различие статического и runtime.** Наличие файла по пути с данным SHA доказывает
   ТОЛЬКО то, что на принятом source существуют именно эти байты. Оно НЕ доказывает ни
   сборку, ни запуск, ни соединение, ни отображение. Для каждого результата §6 ниже
   разграничено: что уже есть статически, чего оно НЕ доказывает, какое runtime-
   свидетельство отсутствует и при каком условии следует STOP.

4. **Результаты §6** (docs/architecture/P8_PORTAL_IMPLEMENTATION_ROADMAP.md, blob
   `b034e5f628583b15709737203a8b909609ac259c`) рассматриваются как целевые статусы P8C,
   ни один из которых на момент подготовки НЕ наблюдался в рантайме.

## 2. Матрица по четырём результатам §6

### 2.1 PORTAL_UI = RUNNING

| Поле | Значение |
|---|---|
| **Критерий** | Frontend Портала отдаётся и рендерится через утверждённый ingress (Envoy Gateway → `portal` Service → Pod). Браузер получает `/` (index.html) и `/assets/*`, вкладки (Обзор / Kubernetes / Хранилище / Резервное копирование / PostgreSQL / Метрики / События) наполняются данными ЖИВОГО API; общий статус и предупреждения выводятся из снапшота, без захардкоженного «зелёного». |
| **Статическое свидетельство (путь + blob SHA @ d22aa8f)** | `portal/web/index.html` `2d28a3ab…`, `portal/web/app.js` `25ac1236…`, `portal/web/style.css` `70c5af26…`, `portal/web/embed.go` `d95fcfa9…`; smoke-тесты рендера `portal/web/renderer-smoke.test.mjs` `c0031be6…`, `fixture-smoke.test.mjs` `1120f9f9…`, `dataflow-smoke.test.mjs` `9122b536…`; маршрут ingress `portal/manifests/gateway.yaml` `1e1f48a3…`. |
| **Чего НЕ доказывает** | Наличие статики и smoke-тестов (jsdom/Node на fixtures) НЕ доказывает, что (а) Pod собран и поднят, (б) `/` и `/assets/` реально отдаются, (в) Envoy Gateway маршрутизирует до Pod, (г) UI связан с live API (smoke использует fixtures/mocks, не live кластер), (д) Basic Auth/TLS работают в боевом контуре. Образ ещё не собран: `deployment.yaml` содержит `REPLACE_WITH_VERIFIED_DIGEST`. |
| **Недостающее runtime-свидетельство** | Live `GET /` → 200 + index.html; `GET /assets/*` → 200; браузерный рендер реального (не mock) снапшота по каждой вкладке; отсутствие 5xx/401 в логах; `GET /readyz` (mgmt) → 200. |
| **Условие STOP** | Образ не собран (digest-плейсхолдер не заменён); ingress/Gateway не разрешён к apply; live `GET` возвращает 5xx/401/404; UI рендерит константный, а не фактический статус — STOP. |

### 2.2 PORTAL_API = RUNNING

| Поле | Значение |
|---|---|
| **Критерий** | HTTP API отвечает GET/HEAD по фиксированному allowlist из 11 маршрутов `/api/v1/{health,summary,nodes,workloads,pods,services,storage,backups,database,metrics,events}` корректным envelope (`sources`/`warnings` — не-null массивы, `data` — не-null), Basic Auth верифицирует оператора, rate-limit/concurrency работают; `/readyz` (mgmt) = 200 только при подтверждённой версии+checksum миграции и непустом снапшоте. |
| **Статическое свидетельство (путь + blob SHA @ d22aa8f)** | `portal/cmd/portal/main.go` `d9e80220…`, `portal/internal/httpapi/server.go` `c804bf23…`, `handlers.go` `e5975b62…`, `event_views.go` `fa84fb51…`, `contract_test.go` `4f8b05d6…`; `portal/internal/auth/auth.go` `62c7a058…`; `portal/internal/config/config.go` `e90a44ec…`; `portal/internal/model/model.go` `8d144d9e…`; контракт `docs/architecture/p8c/openapi.json` `74dd9743…`. |
| **Чего НЕ доказывает** | Contract/unit-тесты на `httptest`+mocks НЕ доказывают, что (а) бинарь собран и запущен, (б) `InClusterConfig` поднялся (SAToken/K8s credentials доступны), (в) collectors реально вернули данные, (г) Basic Auth verifier совпадает с секретом `portal-ui-auth` в кластере, (д) `/readyz` в проде = 200 (зависит от миграции и первого снапшота). |
| **Недостающее runtime-свидетельство** | Live GET по каждому из 11 маршрутов с Basic Auth → 200 + валидный JSON envelope; негативы: 401 без auth, 404 неизвестный путь, 405 на POST (Allow: GET, HEAD); `/readyz` = 200 при подтверждённой миграции; `/livez` = 200. |
| **Условие STOP** | Бинарь не собран/не запущен; `/readyz` устойчиво 503 (миграция не подтверждена ИЛИ `col.Latest()==nil`); авторизация не проходит; envelope приходит с `null` там, где требуется массив — STOP. |

### 2.3 PORTAL_DB = CONNECTED

| Поле | Значение |
|---|---|
| **Критерий** | Portal подключён к `portal-db-rw.portal.svc:5432` как `portal_app` (non-superuser) с TLS `verify-full` (без не-TLS fallback); миграция версии 1 с точным checksum применена и `VerifySchema` проходит; persistence реально пишет `observation_batches`/`timeline_events`; `Ping` OK. |
| **Статическое свидетельство (путь + blob SHA @ d22aa8f)** | `portal/internal/store/store.go` `305fd99f…`, `integration_test.go` `00422707…`; `portal/migrations/0001_portal_observations.sql` `1c18b84a…`, `migrations.go` `084f9ee3…`; `portal/cmd/portal/persistence.go` `5f719feb…`; контракт `docs/architecture/P8_PORTAL_DB_CONTRACT.md` `8e2ca997…`; манифест кластера `manifests/cnpg/v1.30.1/portal-db-cluster.yaml` `e60a9235…`. |
| **Чего НЕ доказывает** | Наличие кода подключения и integration-теста НЕ доказывает соединение с БОЕВЫМ CNPG-кластером `portal-db`: по CI-спеке (§2.1.4 PR #6) integration идёт против loopback `postgres:17.10-bookworm`, а НЕ против кластера. Не доказано: секрет `portal-db-app` содержит рабочий пароль; CA `portal-db-ca` валиден; миграция применена к боевой БД; `target_session_attrs=read-write` доходит до primary. |
| **Недостающее runtime-свидетельство** | Успешный `migrate` Job (exit 0, версия 1, checksum == `Checksum0001`); live `Ping` OK; реальные (не пустые) строки в `observation_batches`/`timeline_events`; `/api/v1/database` возвращает фактическое состояние CNPG; подтверждение TLS `verify-full` (отказ при недоверенном CA). |
| **Условие STOP** | TLS `verify-full` не проходит; версия/checksum миграции не совпадают; credential недоступен (нет `portal-db-app`); запись в боевую БД не подтверждена — STOP. |

### 2.4 PLATFORM_STATUS = VISIBLE

| Поле | Значение |
|---|---|
| **Критерий** | Portal отображает ФАКТИЧЕСКОЕ (не выдуманное) состояние платформы — nodes/workloads/pods/services/storage/backups/database/metrics/events — из read-only Kubernetes API + Metrics Server + Barman metrics, с честным per-source registry (`partial`/`warnings` при ошибках чтения, никогда выдуманный «green»); `overall_health` выводится из снапшота, а не константа. |
| **Статическое свидетельство (путь + blob SHA @ d22aa8f)** | `portal/internal/collectors/collector.go` `d8885a23…`, `collect_methods.go` `af67e720…`, `metrics.go` `73cb6a88…`, `continuation.go` `7d1ad070…`, `transport.go` `5aa05a10…`; RBAC `portal/manifests/rbac.yaml` `036e90b4…` (get/list, no wildcard, no mutation); `portal/manifests/deployment.yaml` `2cb27165…`; `networkpolicy.yaml` `15f0b324…`; офлайн-аудит `portal/networkpolicy/inventory.py` `5f0e2450…`. |
| **Чего НЕ доказывает** | Наличие read-only коллектора и RBAC-манифеста НЕ доказывает, что (а) RBAC реально применён и запросы к K8s разрешены (apply запрещён), (б) коллектор прочитал live кластер и вернул данные, (в) отображаемое совпадает с фактическим, (г) Metrics Server / Barman metrics реально доступны. Офлайн-инвентарь NetworkPolicy — это аудит проекций, а не live-чтение кластера. |
| **Недостающее runtime-свидетельство** | Live снапшот с непустыми nodes/workloads/pods и source registry в статусе OK по каждому источнику; `/api/v1/summary` с корректным `overall_health`, выведенным из снапшота; подтверждение read-only (mutation отклонён); сверка отображаемого с фактическим (например, `kubectl get nodes`). |
| **Условие STOP** | Коллектор не читает кластер (FORBIDDEN из-за неприменённого RBAC); Metrics Server недоступен; отображаемое состояние захардкожено/выдумано, а не выведено из снапшота — STOP. |

## 3. Release vs необязательный seed (разделение и оговорка про digest)

1. **Release и seed — независимые scope с независимыми допусками** (спека PR #6 §2). Seed —
   НЕОБЯЗАТЕЛЬНЫЙ one-shot bootstrap; отсутствие seed-допуска означает «seed не выполняется»
   и НЕ блокирует release-scope.

2. **Статическое свидетельство release** (только шаблоны/подготовка, НЕ факт сборки):
   `portal/tools/p8c-portal-release.yml.template` `a86521ac…`, `release-check.py` `ad49113c…`,
   `pins.lock.json` `4fb6f353…`, `install-verified-go.sh` `2b6e0c9a…`, `Containerfile`
   `e158e2f7…`; спецификация gate — `docs/architecture/P8C_CI_RELEASE_GATE_SPEC_20261118.md`
   на ветви PR #6 @ `1b2276673a301c2b04f420a2000a22245c833265` (blob `e385cc4c…`, НЕ на main).
   Workflow НЕ опубликован, dispatch НЕ выполнен, поэтому application digest на момент
   подготовки НЕИЗВЕСТЕН (в `deployment.yaml` — плейсхолдер `REPLACE_WITH_VERIFIED_DIGEST`).

3. **Статическое свидетельство seed** (опциональный bootstrap, НЕ deployable):
   `portal/tools/p8c-portal-seed.yml.template` `b631ed64…`, `Seed.Containerfile` `44277837…`.

4. **Оговорка про digest (основание #16, §4.4 спеки PR #6).** Поле
   `seed_not_application_digest` обязано быть ТРЁХЗНАЧНЫМ (true / false / unknown), а НЕ
   булевым:
   - `true`  — оба digest известны и различаются;
   - `false` — оба digest известны и совпадают (STOP);
   - `unknown` — хотя бы один digest неизвестен (в т.ч. при пустом/отсутствующем
     application digest — обязательно `unknown`, НЕ `true`).

   **Вывод для матрицы:** на момент подготовки release НЕ выполнялся, следовательно
   application digest НЕИЗВЕСТЕН. Любое сравнение `seed_digest != application_digest` в этих
   условиях есть `unknown` и НЕ доказывает различие digest. Отсутствие известного
   application digest — состояние «неприменимо/неизвестно», а НЕ прохождение проверки
   различия. Это требование к будущей реализации helper'а (правка helper/pins отложена на
   фазу исполнения gate, #16).

## 4. Глобальные границы и STOP

- Правка helper/pins, публикация workflow, dispatch, release, live-readiness, NetworkPolicy
  apply и deployment — НЕ выполнялись и НЕ разрешены.
- Ни один результат §6 не считается достигнутым: все четыре — STATIC_ONLY /
  RUNTIME_NOT_OBSERVED. Наличие кода/шаблона/манифеста не выдаётся за факт работы.
- STOP: если в ходе будущего исполнения любой пункт из «Недостающее runtime-свидетельство»
  любого результата не может быть получен, либо выполнен запрещённый переход (deployment/
  NetworkPolicy apply/live-readiness без допуска), либо application digest остаётся неизвестен
  и при этом требуется доказать различие digest — STOP и отчёт Архитектору.

```text
PREPARATION = COMPLETE (REVIEW_READY, offline)
EXECUTION    = NOT_AUTHORIZED
```
