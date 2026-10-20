# TASK: P8C-R1 RESUME-R3 — завершить correctness и доказать closure

Дата: 2026-10-20 (Europe/Moscow). Chief Architect.
STATUS: AUTHORIZED SOURCE REWORK / OWNER AND RUNTIME GATES CLOSED.

## Независимое решение

Connector проверил main `cb8fbacd4cf036a4f7ec43fcb734f7dd751fd7ed`, tree `bc4484630fb85be798253f24c02a6ce6bacebd2b`.
Цепочка после f824a22: 7d9fe13 → ba15df3 → 8713159 → cb8fbac, 4 ahead / 0 behind.
Source `871315928f07dd209fc1377451e02931582b8ffc` подтверждён: последний commit добавляет только четыре evidence-файла. Неожиданных изменений вне Portal/new evidence в этом delta нет.

Пакет опубликован, но **полное R2-01…08 CLOSED и source-package PASS не приняты: REWORK_REQUIRED**.
WORKFLOW_TEMPLATE_APPROVED_FOR_OWNER=NO; OWNER_HELPERS_APPROVED_FOR_REAL_CREDENTIALS=NO; NETPOL_APPROVED_FOR_APPLY=NO.
Готовность предоставить на review не означает успешное прохождение review.
P8C остаётся IN_PROGRESS / NOT_FINAL_ACCEPTED. Это не пересмотр P8A/P8B.

Основание — проверенные остатки ниже, а не отсутствие Owner token. Сохраняются исходный MVP task, D1–D3, RESUME и RESUME-R2. Этот task не заменяет их требования и не расширяет scope. Не просить нового разрешения «продолжать» между перечисленными инженерными действиями.

## A. R2-01 — helper safety: remaining gate

Принято как прогресс: atomic create-only, корректное различение probe errors/absence, auth-only dockerconfig. Локально повторён `python3 portal/tools/test_helpers.py`: 7/7 PASS. Но это 3 format + 4 flow tests только UI helper; registry helper не тестируется.

Оба helper проверяют stdin.isatty(), но не запрещают GetPassWarning/fallback и не обрабатывают все input errors. Воспроизведение реального stdlib fallback_getpass на synthetic TTY (subprocess mocked): у каждого 2 предупреждения, затем get/create, exit0. Настоящих credentials/запросов не было. Наличие TTY само по себе не доказывает отключение echo.

Исправить оба helper: fail-closed при невозможности no-echo до чтения fallback input, безопасные bounded сообщения для EOF/encoding/OS/input ошибок, отсутствие credential-bearing traceback. Отдельно различать timeout до create и timeout после отправки create: последний означает UNKNOWN_OUTCOME, нельзя печатать «no write attempted». Только metadata recheck, без overwrite/implicit rotation.

Тестировать оба helper через mocked subprocess, включая body/argv/output assertions: success, exists, Forbidden/network probe, AlreadyExists race, create denied, timeout на каждой фазе, missing kubectl, non-TTY, реальный fallback warning, EOF. Никаких реальных secrets в tests. Зафиксировать no annotations/no credentials in output/no overwrite.

## B. R2-02 — transport: allowlist вместо denylist

Исправление authority https://host:port принято как прогресс. Но `forbiddenPath` — blacklist нескольких сегментов, не exact resource/path allowlist. Например configmaps/неизвестный API GVR проходят guard. req.Host override/userinfo не проверяются; при пустом parsed host проверка host отключается. API request timeout5s не задан в newClients; есть только общий cycle20s.

Сделать fail-closed canonical HTTPS base URL validation, fixed authority (включая Host override), exact approved collection/named GET paths/namespaces/GVR, отсутствие неизвестных subresources; сохранить запрет redirects. RBAC остаётся основной границей. Положительные fixtures для каждого реально используемого approved path + отрицательные configmaps/unknown GVR/encoded path/host override/invalid URL/method/redirect. Отдельный per-request deadline5s и общий cycle20s. Не добавлять platform mutations.

## C. R2-03/04 — coherent API, freshness и UI

В `handlers.go`:
- encodeCursor содержит только snapshotID:namespace:offset; endpoint не кодируется. parseListQuery не читает endpoint. Events не сверяет даже namespace cursor, а since/severity не связаны с ним.
- snapshot читается отдельно при query parsing, данных, выдаче cursor; межшаговая смена snapshot возможна.
- SQL LIMIT/OFFSET читается из изменяемого live набора без стабильной границы; upsert меняет ingested_at. Cursor collector snapshot не фиксирует DB view.
- nil snapshot оставляет sources/warnings=null; non-null исправлен только внутри snap!=nil.
- source ageSeconds заморожен при collection; health/subsystem health не деградируют по возрасту. application-db в summary всегда unknown; nodes subsystem игнорирует node.Health/pressure.
- handleHealth не применяет requireNoQuery.

В collectors: listWithContinue применён лишь к Pods и вызван с (listPage,listPage)=(200,200), поэтому после первой полной страницы останавливается. Остальные List одностраничные; backup Limit500. Сам helper может вернуть600 при page200/cap500 (append до проверки, без усечения), вопреки своему комментарию. В tree нет continuation test, несмотря на evidence claim.

Исправить coherent snapshot на весь HTTP response; cursor binding endpoint+все применимые filters+snapshot, стабильный DB event pagination boundary/ordering (или другой явно обоснованный bounded snapshot), корректное истечение при смене memory/DB источника. Не позволять huge offset вызвать overflow/panic. Все K8s list categories: page<=200, full continuation до согласованного cap500, корректная partial/error coverage, сортировка и caps. Честные dynamic age/freshness/status, non-null schema arrays на startup/errors, DB connected state и node pressure.

Frontend уже читает data.items, но:
- nextCursor нигде не обрабатывается;
- failed list requests превращаются в «Нет данных»;
- stale/unavailable summary с прежним healthy остаётся зелёным и пишет «нет предупреждений»;
- Storage overview health фиксирован unknown, вместо фактического scoped health;
- Barman/WAL details из API не отрисованы; replicas/recovery и warnings должны быть достоверны;
- backup Health cell выводит phase вместо health.

Проверить реальные renderers: startup/null, source error, stale/unavailable, pressure, partial, pagination, пустой достоверный результат отдельно от unavailable. Не ослаблять утверждённый OpenAPI. Browser/DOM fixture test должен существовать, выполняться и иметь output; упоминание jsdom в отчёте не является test. Fixtures/screenshot помечать как test data, не runtime Portal.

## D. R2-05 — persistence и DB

В `cmd/portal/main.go` всё ещё:
- каждый persistOnce генерирует random UUID и пишет тот же snapshot повторно;
- overall_health всегда 'unknown';
- Prune error игнорируется;
- LagSeconds.Add(1) считает ошибки, не секунды от последней успешной persistence;
- status event только о write failure отправляется в ту же неисправную DB, ошибка игнорируется; это не история platform status transitions и не durable/bounded fallback.
В store ListEvents nullable object_kind/object_namespace/object_name сканируются в string; UpsertEvent пишет NULL для пустых значений. Это ломает чтение соответствующих rows.
Readiness один раз проверяет ledger и не имеет bounded initial retry/structure validation; TLS minimum/ambient pgx overrides не закреплены явно.

Закрыть ранее заданные требования: stable snapshot batch identity/idempotency, calculated health, source count-aware event dedup с корректным refresh source metadata, bounded time/batch/backpressure, ошибки всех write/cleanup путей в status, lag по elapsed time, nullable readback, bounded memory queue с transitions/recovery и честным dataLoss. Диагностическая UI сохраняется после успешной initial validation при временном DB outage. Exact ledger + expected table structure, bounded initial retry, TLS verify-full/min1.2/servername, запрет ambient PG overrides/fallback. Не менять infrastructure tables; ещё не применённые migration files проверять по evidence, после применения только forward migration.

Integration tests существуют, но не выполнены и сейчас содержат собственные дефекты:
1. Все используют одну portal schema без изоляции/cleanup, повторно CREATE TABLE без IF NOT EXISTS и ledger version1.
2. Первый event test создаёт NULL object fields и читает их в string.
3. TTL test старит observed_at, а Prune использует recorded_at (остаётся now); ожидаемое удаление не произойдёт.
4. Test с именем TTLAndCap не проверяет over-cap.
5. Test DDL дублирует migration вместо использования actual embedded migration.

Исправить изоляцию тестов на отдельном disposable PostgreSQL17 и actual migration. Проверить insert/readback/NULL, unchanged+increased source count, recreated UID, repeated batch, TTL и cap независимо, failures/fallback/recovery, ledger/schema drift. Принудительно FAIL CI job если TEST_DATABASE_URL отсутствует вместо silent SKIP. Никаких failure tests на production DB.

## E. R2-06 — workflow template не executable

В `portal/tools/p8c-portal-release.yml.template` проверено:
- `sudo buildkitd &` — rootful, не заявленный rootless; BUILDKITD_FLAGS не переданы daemon command.
- buildctl использует default Dockerfile, но в repo только Containerfile; нет filename option.
- push=true и private-image SBOM/scan стоят ДО login-action.
- digest извлекается вторым build/grep stdout; это не проверенный digest первого push. Нужны metadata JSON одного build, строгая validation и registry verification этого же artifact.
- GO_SHA256 не используется; action SHAs помечены «verify before run», proof отсутствует.
- cosign installer input `v${COSIGN_VERSION}` — literal строка, shell env substitution в with не выполняется. Требуется точная версия через поддерживаемую expression/установку и verification.
- sign+verify не сверяет source annotation; отсутствуют полноценная provenance attestation, SBOM attestation/subject verification.
- SBOM создаётся в repo root, upload ищет portal/sbom.spdx.json; signature/verification/scan/provenance artifacts не сохраняются.
- нет DB service/job, integration command, race, helper tests, JS/browser tests. Они не будут выполнены «в CI» данным template.
- не доказана private package visibility; deployment и migration Job не ссылаются на portal-registry-pull (возможная привязка через SA должна быть явной и проверенной).

Подготовить рабочий template и вспомогательные scripts по D2/R3: actual rootless pinned builder + prerequisites/health wait; verify tools/action refs; explicit Containerfile; authenticated private push, один build и immutable digest из metadata; scan final binary/OCI, SBOM/provenance/signature, exact identity/issuer/source/subject verification; private visibility proof; retained artifacts с корректными путями и fail on missing. Test jobs до release, без PAK access, без новых расходов. SOURCE_SHA фактического dispatch, не исторический source8713159. Build/test/push/sign различать по фактическому исполнению.

До review разрешены доработка, static workflow/schema/action validation, tests и build/scan на уже разрешённой локальной isolated среде. Template не публиковать и не dispatch. Если отдельный внешний шаг действительно недоступен — предоставить точный blocker и закончить всё независимое; не объявлять отсутствующие test jobs выполненными.

## F. R2-07 — NetworkPolicy небезопасен и блокирует собственные flows

`PLAN.md` не изменён: по-прежнему8008 и нет полной flow matrix. Новый JSON сообщает8000, но не содержит raw safe runtime output/command/time, подтверждающих port/labels/destinations.

В новом YAML:
- CNPG ingress не разрешает Portal9187, migrator5432 и CNPG operator8000; egress разрешение клиента само по себе не разрешает ingress назначения.
- actual migration Job pod template не имеет labels; p8c-migrator-flows его вообще не выбирает. Default-deny блокирует DB egress Job.
- Portal ingress namespaceSelector:{} + podSelector:{} разрешает8080 из всех namespaces/Pods. Комментарий «refined in dataplane policy» это не исправляет: policies additive.
- p8c-portal-dataplane-flows отсутствует.
- API egress /24 и Barman namespaceSelector:{} шире exact inventory; actual service/DNAT path не доказан.

Нельзя применять первый CNPG policy в этой версии. Исправить selectors/manifests вместе с полным D1 inventory: actual namespace/labels/source → destination/port/protocol/purpose → safe raw evidence refs; operator/monitoring/replication/DNS/API/S3/Portal/migrator, новый Gateway-owned dataplane/listener/xDS. Свести PLAN/YAML/evidence без противоречий. Объяснить service/DNAT/CNI path, без guesswork или blanket allow. Добавить offline selector/flow assertions для positive и negative cases, проверяя ОБЕ стороны union policies, плюс safe rollout/postcheck/точный rollback только своих объектов. Live apply по-прежнему отложен до закрытия последующих gates.

## G. R2-08 — фактическое evidence

`01-build-test.txt` снова только пять summary PASS lines. Это не raw command output/source/tool/time/exit evidence. `go vet -tags integration` не выполняет PostgreSQL tests; `go test ./...` исключает tagged integration tests.
Новые 11-handler tests полезны, но проверяют envelope presence/несколько shapes. Не загружают OpenAPI и не проверяют additionalProperties/enums/types/required/nullable на всех11 endpoints, startup/error/stale/partial cases.
Наличие test source не равно выполнению и не доказывает closure.

Один законченный пакет: failing-before/passing-after regression cases для A–F, schema validation actual11 handlers, tests/race с meaningful paths, обе helper suites, actual isolatedDB + browser/DOM fixture run, workflow validation, secret scan. Сохранять source SHA/clean status/tool versions/UTC command transcripts/exit/package output и test-case→requirement mapping. Секреты/DSN/auth headers не сохранять. Old evidence не переписывать.

## Порядок и STOP

1. Recovery текущего main через разрешённый доступ; новый Architect docs/evidence commit ожидаем.
2. Автономно закончить A–G без Owner secrets; не выдавать очередной partial как CLOSED.
3. Выполнить доступные source validation; если остаётся настоящий external blocker, явно назвать NOT_EXECUTED проверки и не ставить PASS.
4. Один reviewable пакет, FF/no force, новое evidence, exact SOURCE_SHA. Проверить финальный remote main и отсутствие непредвиденного delta.
5. STOP для независимого Architect review. До положительного решения не запускать real Owner helpers, workflow dispatch, live policies, production migrations/deploy.
6. Только после принятия подготовить Owner instructions с exact reviewed helper/template hashes, protected local provisioning и metadata-only proof. Наличие /etc/hermes/gh_token.txt не снимает Gate; не читать/выводить/переносить токен ради этой source работы.

P8D–P8G/P9 NOT_AUTHORIZED. Backup/latest restore/PITR/P8A failover/P7/P7C failure tests не повторять. Никаких новых adapter/SSO/framework/scope expansion. Не менять историю и не присваивать FINAL ACCEPTED/CONNECTOR VERIFIED самостоятельно.

Evidence этого review: `evidence/P8/20261020-p8c-cb8fbac-architect-review/`.
Источники: immutable reviewed repository; Python getpass documentation (fallback warning); Kubernetes NetworkPolicy documentation (additive, both ingress/egress); BuildKit rootless documentation. Architect не запускал Go/PostgreSQL/browser/live cluster/CI; локально выполнены helper unittest и offline reproducer (actual Python helpers/JS renderers, mocked IO + static YAML checks).
