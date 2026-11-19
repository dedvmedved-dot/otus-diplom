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

## Актуализация #29 — после решения владельца А

Блок выше и §§1–4 ниже — историческая статическая оценка. Действующие границы и preflight: [наряд #29](P8C_RUNTIME_29.md). Ограниченный тестовый deployment/live-readiness разрешён; фактический rollout пока не начат. PORTAL_UI, PORTAL_API, PORTAL_DB и PLATFORM_STATUS остаются STATIC_ONLY / RUNTIME_NOT_OBSERVED. Наличие допуска не является evidence. P8C = NOT_FINAL_ACCEPTED; P8D закрыт.

## 1. Метод и соглашения

1. **Static-only.** Настоящий документ составлен ТОЛЬКО чтением исходников на принятом
   source и подготовкой текста. Никакой helper/pins не правился, workflow не публиковался,
   dispatch/release/seed/live-readiness/NetworkPolicy apply/deployment не выполнялись.

2. **SHA = git blob SHA-1** (40 hex, объектный SHA содержимого файла), снятый с принятого
   source `d22aa8f1170deaf09580518916ea02c7c4d8bfba` (Forgejo `origin/main`). Это НЕ SHA
   коммита и НЕ sha256 (sha256 для gate-помощников закреплён отдельно в §1.2 спеки PR #6).
   Любое байтовое изменение файла меняет blob SHA и инвалидирует ссылку. В тексте ниже
   приведены ПОЛНЫЕ относительные пути; ПОЛНЫЕ 40-hex blob SHA по каждому файлу собраны
   в **Приложении A** (результат `git rev-parse d22aa8f:<полный путь>`).

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
| **Статическое свидетельство (пути; blob SHA — Приложение A.1 @ d22aa8f)** | `portal/web/index.html`, `portal/web/app.js`, `portal/web/style.css`, `portal/web/embed.go`; smoke-тесты рендера `portal/web/renderer-smoke.test.mjs`, `portal/web/fixture-smoke.test.mjs`, `portal/web/dataflow-smoke.test.mjs`; маршрут ingress `portal/manifests/gateway.yaml`. |
| **Чего НЕ доказывает** | Наличие статики и smoke-тестов (jsdom/Node на fixtures) НЕ доказывает, что (а) Pod собран и поднят, (б) `/` и `/assets/` реально отдаются, (в) Envoy Gateway маршрутизирует до Pod, (г) UI связан с live API (smoke использует fixtures/mocks, не live кластер), (д) Basic Auth/TLS работают в боевом контуре. Сборка не подтверждена, digest в манифесте не закреплён: `deployment.yaml` содержит `REPLACE_WITH_VERIFIED_DIGEST`. |
| **Недостающее runtime-свидетельство** | Live `GET /` → 200 + index.html; `GET /assets/*` → 200; браузерный рендер реального (не mock) снапшота по каждой вкладке; отсутствие 5xx и отсутствие 401 для авторизованных запросов в логах; `GET /readyz` (mgmt) → 200. |
| **Условие STOP** | Сборка не подтверждена, digest в манифесте не закреплён (плейсхолдер не заменён); ingress/Gateway не разрешён к apply; live `GET` авторизованным запросом возвращает 5xx/401/404; UI рендерит константный, а не фактический статус — STOP. |

### 2.2 PORTAL_API = RUNNING

| Поле | Значение |
|---|---|
| **Критерий** | HTTP API отвечает GET/HEAD по фиксированному allowlist из 11 маршрутов `/api/v1/{health,summary,nodes,workloads,pods,services,storage,backups,database,metrics,events}` корректным envelope (`sources`/`warnings` — не-null массивы, `data` — не-null), Basic Auth верифицирует оператора, rate-limit/concurrency работают; `/readyz` (mgmt) = 200 только при подтверждённой версии+checksum миграции и непустом снапшоте. |
| **Статическое свидетельство (пути; blob SHA — Приложение A.2 @ d22aa8f)** | `portal/cmd/portal/main.go`, `portal/internal/httpapi/server.go`, `portal/internal/httpapi/handlers.go`, `portal/internal/httpapi/event_views.go`, `portal/internal/httpapi/contract_test.go`; `portal/internal/auth/auth.go`; `portal/internal/config/config.go`; `portal/internal/model/model.go`; контракт `docs/architecture/p8c/openapi.json`. |
| **Чего НЕ доказывает** | Contract/unit-тесты на `httptest`+mocks НЕ доказывают, что (а) бинарь собран и запущен, (б) `InClusterConfig` поднялся (SAToken/K8s credentials доступны), (в) collectors реально вернули данные, (г) Basic Auth verifier совпадает с секретом `portal-ui-auth` в кластере, (д) `/readyz` в проде = 200 (зависит от миграции и первого снапшота). |
| **Недостающее runtime-свидетельство** | Live GET по каждому из 11 маршрутов с Basic Auth → 200 + валидный JSON envelope; негативы: 401 без auth (ОЖИДАЕМЫЙ отказ негативного сценария, НЕ ошибка и НЕ STOP), 404 неизвестный путь, 405 на POST (Allow: GET, HEAD); `/readyz` = 200 при подтверждённой миграции; `/livez` = 200. |
| **Условие STOP** | Бинарь не собран/не запущен; `/readyz` устойчиво 503 (миграция не подтверждена ИЛИ `col.Latest()==nil`); авторизация не проходит для авторизованного запроса (401 при валидных креденшелах — в отличие от ожидаемого 401 «без auth»); envelope приходит с `null` там, где требуется массив — STOP. |

### 2.3 PORTAL_DB = CONNECTED

| Поле | Значение |
|---|---|
| **Критерий** | Portal подключён к `portal-db-rw.portal.svc:5432` как `portal_app` (non-superuser) с TLS `verify-full` (без не-TLS fallback); миграция версии 1 с точным checksum применена и `VerifySchema` проходит; persistence реально пишет `observation_batches`/`timeline_events`; `Ping` OK. |
| **Статическое свидетельство (пути; blob SHA — Приложение A.3 @ d22aa8f)** | `portal/internal/store/store.go`, `portal/internal/store/integration_test.go`; `portal/migrations/0001_portal_observations.sql`, `portal/migrations/migrations.go`; `portal/cmd/portal/persistence.go`; контракт `docs/architecture/P8_PORTAL_DB_CONTRACT.md`; манифест кластера `manifests/cnpg/v1.30.1/portal-db-cluster.yaml`. |
| **Чего НЕ доказывает** | Наличие кода подключения и integration-теста НЕ доказывает соединение с БОЕВЫМ CNPG-кластером `portal-db`: по CI-спеке (§2.1.4 PR #6) integration идёт против loopback `postgres:17.10-bookworm`, а НЕ против кластера. Не доказано: секрет `portal-db-app` содержит рабочий пароль; CA `portal-db-ca` валиден; миграция применена к боевой БД; `target_session_attrs=read-write` доходит до primary. |
| **Недостающее runtime-свидетельство** | Успешный `migrate` Job (exit 0, версия 1, checksum == `Checksum0001`); live `Ping` OK; реальные (не пустые) строки в `observation_batches`/`timeline_events`; `/api/v1/database` возвращает фактическое состояние CNPG; подтверждение TLS `verify-full` (отказ при недоверенном CA). |
| **Условие STOP** | TLS `verify-full` не проходит; версия/checksum миграции не совпадают; credential недоступен (нет `portal-db-app`); запись в боевую БД не подтверждена — STOP. |

### 2.4 PLATFORM_STATUS = VISIBLE

| Поле | Значение |
|---|---|
| **Критерий** | Portal отображает ФАКТИЧЕСКОЕ (не выдуманное) состояние платформы — nodes/workloads/pods/services/storage/backups/database/metrics/events — из read-only Kubernetes API + Metrics Server + Barman metrics, с честным per-source registry (`partial`/`warnings` при ошибках чтения, никогда выдуманный «green»). Честный `partial`/warnings подтверждает ВИДИМОСТЬ деградации (платформа видима), но НЕ является подтверждением полноты данных: видимость деградации и подтверждение полноты — РАЗНЫЕ свидетельства и оцениваются раздельно. Поле `data.overall` в `/api/v1/summary` (а НЕ столбец БД `overall_health`) выводится из снапшота, а не константа (base: `portal/internal/model/model.go:83–88`, `portal/web/app.js:131`). |
| **Статическое свидетельство (пути; blob SHA — Приложение A.4 @ d22aa8f)** | `portal/internal/collectors/collector.go`, `portal/internal/collectors/collect_methods.go`, `portal/internal/collectors/metrics.go`, `portal/internal/collectors/continuation.go`, `portal/internal/collectors/transport.go`; RBAC `portal/manifests/rbac.yaml` (get/list, no wildcard, no mutation); `portal/manifests/deployment.yaml`; `portal/manifests/networkpolicy.yaml`; офлайн-аудит `portal/networkpolicy/inventory.py`. |
| **Чего НЕ доказывает** | Наличие read-only коллектора и RBAC-манифеста НЕ доказывает, что (а) RBAC реально применён и запросы к K8s разрешены (apply запрещён), (б) коллектор прочитал live кластер и вернул данные, (в) отображаемое совпадает с фактическим, (г) Metrics Server / Barman metrics реально доступны. Офлайн-инвентарь NetworkPolicy — это аудит проекций, а не live-чтение кластера. |
| **Недостающее runtime-свидетельство** | Live снапшот с непустыми nodes/workloads/pods и source registry в статусе OK по каждому источнику; `/api/v1/summary` с корректным `data.overall`, выведенным из снапшота; подтверждение read-only через проверку ЭФФЕКТИВНЫХ прав без записи (например `kubectl auth can-i --list --as=system:serviceaccount:portal:portal-reader` либо SelfSubjectAccessReview: get/list разрешены, мутирующие verbs create/update/patch/delete — НЕ разрешены), без попытки реальной мутации; сверка отображаемого с фактическим (например, `kubectl get nodes`). |
| **Условие STOP** | Если Metrics Server недоступен или RBAC запрещает чтение, а Portal показывает отказ соответствующего источника (`partial`/warnings), деградация видима: это НЕ STOP для видимости, но STOP для подтверждения полноты (§4). Если Portal скрывает отказ, показывает выдуманное состояние или не показывает состояние вовсе — STOP и для видимости. |

## 3. Release vs необязательный seed (разделение и оговорка про digest)

1. **Release и seed — независимые scope с независимыми допусками** (спека PR #6 §2). Seed —
   НЕОБЯЗАТЕЛЬНЫЙ one-shot bootstrap; отсутствие seed-допуска означает «seed не выполняется»
   и НЕ блокирует release-scope.

2. **Статическое свидетельство release** (только шаблоны/подготовка, НЕ факт сборки):
   `portal/tools/p8c-portal-release.yml.template`, `portal/tools/release-check.py`,
   `portal/tools/pins.lock.json`, `portal/tools/install-verified-go.sh`, `portal/Containerfile`;
   спецификация gate — `docs/architecture/P8C_CI_RELEASE_GATE_SPEC_20261118.md` на ветви
   PR #6 @ `1b2276673a301c2b04f420a2000a22245c833265` (blob
   `e385cc4c17f107e22da4415c8aba0c78e6cc35bd`, НЕ на main). Полные blob SHA — Приложение A.5.
   Workflow НЕ опубликован, dispatch НЕ выполнен, поэтому application digest на момент
   подготовки НЕИЗВЕСТЕН (в `deployment.yaml` — плейсхолдер `REPLACE_WITH_VERIFIED_DIGEST`).

3. **Статическое свидетельство seed** (опциональный bootstrap, НЕ deployable):
   `portal/tools/p8c-portal-seed.yml.template`, `portal/tools/Seed.Containerfile`. Полные blob
   SHA — Приложение A.5.

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

## Приложение A — полные пути и полные blob SHA (40 hex)

Все blob SHA ниже получены командой `git rev-parse d22aa8f1170deaf09580518916ea02c7c4d8bfba:<путь>`
на принятом source `origin/main` (base PR #20). Формат: полный относительный путь репозитория →
полный git blob SHA-1 (40 hex). Спецификация gate в A.5 привязана к СВОЕМУ коммиту PR #6, НЕ к main.

### A.1 PORTAL_UI (§2.1)

| Файл (полный путь) | blob SHA-1 (40 hex) |
|---|---|
| `portal/web/index.html` | `2d28a3ab3093a09ef0874ff7d4299a4a0b5840dc` |
| `portal/web/app.js` | `25ac1236732b5dc9753b2cd3ed67c7c557dc19aa` |
| `portal/web/style.css` | `70c5af2644ade9075181bedb1f4c04c488c91e0c` |
| `portal/web/embed.go` | `d95fcfa909cb882e22d5148a2987b99a518b23c7` |
| `portal/web/renderer-smoke.test.mjs` | `c0031be6d6bb3eb738277a11a202807b51a19f68` |
| `portal/web/fixture-smoke.test.mjs` | `1120f9f931fecb42b244ae830621b88bcf1cd4ed` |
| `portal/web/dataflow-smoke.test.mjs` | `9122b536c3c733d214c35764452d68336928c2af` |
| `portal/manifests/gateway.yaml` | `1e1f48a3c6d03c4558f4b4c3cca24bc12c22b763` |

### A.2 PORTAL_API (§2.2)

| Файл (полный путь) | blob SHA-1 (40 hex) |
|---|---|
| `portal/cmd/portal/main.go` | `d9e8022098f01d777c2fe66e0a13f4742ad04a8f` |
| `portal/internal/httpapi/server.go` | `c804bf231fc68bb0cfed1b4a0c058a1b938345d4` |
| `portal/internal/httpapi/handlers.go` | `e5975b62fadefc538ce4d262dffa392a70eca684` |
| `portal/internal/httpapi/event_views.go` | `fa84fb51aff3b70d8e393b7061e5ecb83c1ffc22` |
| `portal/internal/httpapi/contract_test.go` | `4f8b05d6bac2b2373f3db2b96f821a1f97162d98` |
| `portal/internal/auth/auth.go` | `62c7a0586895bfe2a03fd8207daf5641dc664f0c` |
| `portal/internal/config/config.go` | `e90a44eca2983f2eee51656ce80fba07674b08dd` |
| `portal/internal/model/model.go` | `8d144d9e5ef9a05b3b45cf5a9383bfd8639cc3b6` |
| `docs/architecture/p8c/openapi.json` | `74dd9743fb99f922506e30cff0f632f2f018ca37` |

### A.3 PORTAL_DB (§2.3)

| Файл (полный путь) | blob SHA-1 (40 hex) |
|---|---|
| `portal/internal/store/store.go` | `305fd99fa57fc839c726ffb9ed4712b7d4c6a0e5` |
| `portal/internal/store/integration_test.go` | `004227073b943609b046f1fa90c9289755ebe319` |
| `portal/migrations/0001_portal_observations.sql` | `1c18b84a18e48e1b6c1a1ecfe84a9a95412becd5` |
| `portal/migrations/migrations.go` | `084f9ee38ffb93dcdf2daf671ebcf09de9e9d37d` |
| `portal/cmd/portal/persistence.go` | `5f719febd02a40074ac09f21b14f5845f355d52c` |
| `docs/architecture/P8_PORTAL_DB_CONTRACT.md` | `8e2ca99794be49a43f538bf1a40e01d74e842e95` |
| `manifests/cnpg/v1.30.1/portal-db-cluster.yaml` | `e60a92353194fda60f34dacb56273ed7048af14c` |

### A.4 PLATFORM_STATUS (§2.4)

| Файл (полный путь) | blob SHA-1 (40 hex) |
|---|---|
| `portal/internal/collectors/collector.go` | `d8885a233c5f09b17518af2a4ca4b0f6401c7c51` |
| `portal/internal/collectors/collect_methods.go` | `af67e72000545596334b07a0a2ce8413cfc4556a` |
| `portal/internal/collectors/metrics.go` | `73cb6a887f615ee0bcbc1067397e924b1b53a829` |
| `portal/internal/collectors/continuation.go` | `7d1ad07013783a2593c84918f7781cfdfd2606b3` |
| `portal/internal/collectors/transport.go` | `5aa05a103dc3a91cfae09963a12fac88593fcc40` |
| `portal/manifests/rbac.yaml` | `036e90b40a44701c04b145af4c987ae962648477` |
| `portal/manifests/deployment.yaml` | `2cb27165330fe4b6772af3a06a1940d661efc72f` |
| `portal/manifests/networkpolicy.yaml` | `15f0b3245586bf5086e5a24ed02b0460121f7712` |
| `portal/networkpolicy/inventory.py` | `5f0e2450358bfd9b08b542f013be5a914b9195a4` |

### A.5 Release / seed / спецификация gate (§3)

| Файл (полный путь) | blob SHA-1 (40 hex) |
|---|---|
| `portal/tools/p8c-portal-release.yml.template` | `a86521accc76f94dca9380e3b8805a319aa2668f` |
| `portal/tools/release-check.py` | `ad49113c36eb7369fb3c6bfb25e1f6f0db2e150f` |
| `portal/tools/pins.lock.json` | `4fb6f3531247c016d1d4d414eb7729988967e254` |
| `portal/tools/install-verified-go.sh` | `2b6e0c9a0127ac0a641feef791f017d287719543` |
| `portal/Containerfile` | `e158e2f77d76a0e775b853c0968b38167fc02078` |
| `portal/tools/p8c-portal-seed.yml.template` | `b631ed64ce543e0619e75cc2f95626a02ec87a75` |
| `portal/tools/Seed.Containerfile` | `44277837983b847ca03280774b2ff124aafc0ca5` |
| `docs/architecture/P8C_CI_RELEASE_GATE_SPEC_20261118.md` @ `1b2276673a301c2b04f420a2000a22245c833265` (PR #6, НЕ main) | `e385cc4c17f107e22da4415c8aba0c78e6cc35bd` |
