# P8C-R1 — Architect review and bounded resume decision

Дата: 2026-10-20. Автор: Chief Architect.

## Проверенный Source of Truth

GitHub Connector независимо прочитал `main`:

`00b491771230556f061280fb914b6dd6806e2264`, tree `0c8ed4812625db31020903550e61f95b2e6cde2e`.

Цепочка от задания Architect:

1. `6aa27fd8a6fe6b965a27bef1eef93d6050884155` — архитектура и TASK P8C-R1.
2. `ce7b7c5310b4cbccbe2c9f57de20126ca3e5f3cd` — source implementation.
3. `c21242be1623ba96570bde72866171e946449796` — deployment resources.
4. `00b491771230556f061280fb914b6dd6806e2264` — evidence и STOP.

Compare: ahead 3, behind 0, 39 добавленных файлов; существующие контракты и исторические evidence не изменены. Все 39 новых файлов прочитаны Connector. Обнаруженных неожиданных изменений вне Portal/evidence нет. Имена commits не доказывают image pinning: в deployment стоит `REPLACE_WITH_VERIFIED_DIGEST`, в lock — `NOT_VERIFIED`.

Репозиторий public. Это НЕ разрешение сделать container package public. `.github/workflows` в проверенном tree отсутствует. Connector не поддержал запрос `/actions/workflows`; доступность Actions/OIDC/package permissions этим аудитом не доказана.

Runtime из этой сессии не опрашивался. Precheck Hermes — опубликованные краткие результаты, а не независимая текущая runtime-проверка Architect. Не присваивать им новое `CONNECTOR VERIFIED`. Supply chain, migrations, UI/API runtime, TLS и RBAC negative tests не выполнены.

## Решение по статусу

- STOP до runtime был правильным: три заявленных ограничения соответствуют исходному заданию.
- Source package существует и пригоден для доработки/review.
- `G1_IMPLEMENTATION=PASS` не принимается: ниже есть воспроизводимые нарушения обязательного контракта. Компиляция не доказывает функциональную готовность.
- P8C — IN PROGRESS / REWORK REQUIRED / RUNTIME BLOCKED; не FINAL ACCEPTED.
- P8A/P8B и ранее принятые стадии не переоткрываются. P8D–P8G/P9 не разрешены.
- Исходное evidence сохраняется как исторический отчёт Hermes. Исправления/новые факты публикуются новым evidence, не переписыванием прошлого.

## Обязательные findings до runtime

| ID | Факт в проверенном исходнике | Последствие / требуемое исправление |
|---|---|---|
| F01 | `portal/manifests/deployment.yaml`: automount=false, нет projected serviceAccountToken; collector использует `rest.InClusterConfig()` | Нет token/CA wiring для Kubernetes client. Добавить короткоживущий projected token, публичный API CA и namespace в canonical path. Migrator остаётся без token. |
| F02 | `internal/model/model.go` и handlers: nodes data — массив, ready — bool; OpenAPI требует data.items и ready True/False/Unknown; summary overallHealth вместо overall, health и errors имеют иные поля | API не соответствует `docs/architecture/p8c/openapi.json`. Привести все 11 endpoints, error envelopes, queries/cursors и UI к утверждённой схеме; не менять схему под текущий код. |
| F03 | `computeHealth()` возвращает healthy почти всегда; storage/backup collectors теряют ошибки; VolumeSnapshot всегда Phase=ready; UI жёстко задаёт healthy Storage/Velero/Workloads, nodes считает по количеству | Ложная зелёная индикация. Обязательны truthful source-specific freshness, partial, unknown/error и агрегация; snapshot readyToUse — boolean/unknown, не существование объекта. |
| F04 | Во всём source tree отсутствуют вызовы InsertBatch/UpsertEvent/Prune и сбор Kubernetes Events; эти store methods только объявлены | Persistence/timeline не подключены. Реализовать bounded writer, dedup/status transitions, readback, retention и честную деградацию. |
| F05 | `Store.Prune` содержит PostgreSQL `DELETE ... LIMIT 1000`; OFFSET применяется только к уже старым строкам | SQL невалиден; TTL и cap не обеспечиваются. Исправить bounded deletion через CTE/subquery: expired OR over-cap, с отдельными проверками обоих условий. Nullable поля events сканировать безопасно. |
| F06 | ScheduledBackup/ObjectStore/Gateway/HTTPRoute GVR только объявлены; EndpointSlices не читаются; BarmanMetrics не доходят до DTO; pod metrics не извлекаются; timestamp записан в window | Обязательные данные MVP отсутствуют/неверны. Подключить разрешённые named GET/list, safe fields, quantity parser, timestamp/window, backup domains и bounded Barman samples. |
| F07 | DB password и auth verifier передаются файлами, хотя task требует secretKeyRef; config допускает альтернативные DB user/name/port; migration validation только version>=1 | Восстановить точный secretKeyRef contract; фиксированные DB identity/port; exact version+checksum/schema validation. Доказывать verify-full, CA/servername и отсутствие ambient PG overrides. Поздний DB outage не должен закрывать диагностическую UI — это исходный контракт. |
| F08 | `sanitizeErr` возвращает err.Error(); Kubernetes clients не имеют заявленного transport guard; per-request timeout не задан; HTTP servers без timeout/MaxHeaderBytes | Не заявлять sanitization/guard по комментариям. Добавить fixed error codes, host/method/path/redirect allowlist и ограниченные timeout/headers. No raw errors в API/evidence. |
| F09 | Lists по 500 без обработки continue/coverage, Partial не выставляется; cursor — только offset без snapshot binding; UI игнорирует nextCursor | Нельзя выдавать неполные данные как полные. Page<=200, cap500/category, stable ordering/snapshot cursors, cursor expiry, partial warning и работающая UI pagination. |
| F10 | `14-build-tests.txt` — сводка PASS, tests охватывают auth/metrics parser/query helpers; нет contract, persistence, negative-source/transport evidence | Требуются фактические команды/exit codes и meaningful tests против перечисленных рисков. Не выдавать этот review за выполнение Go build/runtime tests. |

Это targeted source review, не заявление о полном отсутствии других дефектов. Доработка выполняется в существующем MVP scope.

## Решения по трём блокерам

### D1. NetworkPolicy

Разрешена ограниченная подготовка и безопасное введение baseline в `portal` после полного существующего flow inventory. Разрешены только новые NetworkPolicy с точными selectors/ports/peers и сохранением действующих CNPG/Barman/backup/monitoring потоков. Нельзя накрыть работающую БД неполным deny/DNS-only набором.

Критическая деталь: **первая allow-policy, выбирающая существующий Pod, уже включает isolation соответствующего направления**. Порядок «allows, затем deny» сам по себе не гарантирует безопасность. Поэтому первая policy, выбирающая существующие CNPG Pods, должна одним объектом содержать полный проверенный allowlist ingress+egress, включая DNS и все действующие зависимости. При неизвестном потоке — STOP до apply. После неё вводятся namespace baseline и правила новых Portal/migrator. Разрешён rollback только новых policies этого task к зафиксированному исходному состоянию.

В `envoy-gateway-system` не разрешён новый namespace-wide deny или изменение существующего controller. Для нового Portal dataplane — только политики по его точным labels и полной матрице xDS/DNS/listener/backend. Это адресное ограничение P8C, не заявление о закрытии baseline всего system namespace.

### D2. Supply chain

Утверждён путь GitHub Actions -> private GHCR -> Cosign keyless. Разрешена подготовка `.github/workflows/p8c-portal-release.yml` с manual `workflow_dispatch`, только main, проверенным source SHA, job permissions `contents: read`, `packages: write`, `id-token: write`. Без cluster kubeconfig, DB/UI credentials и деплоя из CI. Все используемые actions — immutable upstream commit SHA; tools остаются pinned исходным task. Только уже доступный hosted runner без новых расходов/runner registration.

Утверждённая signing identity:

`https://github.com/dedvmedved-dot/otus-diplom/.github/workflows/p8c-portal-release.yml@refs/heads/main`

OIDC issuer: `https://token.actions.githubusercontent.com`.

Не доверять любой подписи с этого issuer: exact identity + source revision + digest + provenance subject обязательны. Public transparency metadata (repository/workflow identity/digest) допустимы для этого public source repo; image package остаётся private. Никаких bypass signature flags или автоматически доверенного локального signing key.

GitHub Actions GITHUB_TOKEN закрывает CI push, но не долговременный pull private image kubelet. Отдельно подтвердить действующий защищённый read-only package credential и `portal/portal-registry-pull`. Если его нет, Owner создаёт/предоставляет его через защищённый локальный механизм; не через чат. Не сохранять workflow token в Kubernetes. Не переключать package в public и не импортировать образ через root/SSH на узлах.

Это архитектурное разрешение пути, а не фактическое закрытие push/sign/pull gates. Реальные permissions/visibility/run/verify/pull подтверждаются Hermes evidence; если доступ невозможен, остаётся адресный BLOCKED.

### D3. Operator auth

Исправление трактовки: Owner нужен **случайный пароль**, verifier предназначен приложению. Не отправлять Owner хеш как login password.

Утверждён Owner-originated provisioning: Owner генерирует 32 random bytes в своём защищённом password manager, хранит их base64url без padding (43 ASCII символа) и вводит пароль без echo в локальный provisioning helper. Helper вычисляет SHA256 ровно этих 43 ASCII символов и создаёт только `portal/portal-ui-auth` key `password-sha256` через JSON stdin защищённого kubectl/client. Внешний инженер и чат не получают пароль. Никаких argv/env/temporary files/logs с raw password/verifier. Secret exists -> STOP, без неявной ротации.

Hermes подготавливает helper, проверяет его на синтетических данных и отдаёт Owner точную команду с явно выбранным разрешённым context. Owner запускает его сам в защищённой незаписываемой сессии. Наличие такого доступа/manager не предполагается; если недоступно, остаётся BLOCKED_AUTH_PROVISIONING. Это не блокирует исходники, tests, сборку, scans и планирование NetworkPolicy; блокирует auth readiness/runtime exposure. Новую credential инфраструктуру/SSO не вводить.

## Исполнимое продолжение

`docs/tasks/TASK_P8C_R1_RESUME_PORTAL_MVP.md` — единственное дополнение к исходному task. Оно не отменяет исходные G0–G8, DB contract, evidence-first и границы стадий. При коллизии это решение заменяет только явно перечисленные D1–D3; security/DoD требования сохраняются.

## Primary references, checked 2026-10-20

- https://kubernetes.io/docs/concepts/services-networking/network-policies/ — additive policies и начало isolation.
- https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry — GITHUB_TOKEN, private package default, отдельная аутентификация pull.
- https://docs.github.com/en/packages/managing-github-packages-using-github-actions-workflows/publishing-and-installing-a-package-with-github-actions — publish workflow.
- https://docs.sigstore.dev/quickstart/quickstart-ci/ — GitHub OIDC identity/issuer verification.
- https://www.postgresql.org/docs/17/sql-delete.html — DELETE не имеет собственного LIMIT; bounded deletion через subquery/CTE.
