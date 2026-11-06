# P8C — завершение исполнимого source-пакета одним проходом

TASK_ID: P8C-SOURCE-CLOSURE-SINGLE-PASS-20261106
Дата: 2026-11-06, Europe/Moscow.
Исполнитель: ОСНОВНОЙ HERMES. Hermes2 не участвует.

## Цель и исходная точка

Закончить текущий release/seed/readiness пакет и передать ОДИН результат для независимой
source-приёмки. Цель — перейти к подготовленному запуску портала, а не наращивать число
частичных отчётов. Новые функции и новые инфраструктурные механизмы согласования не нужны.

Проверенный через Connector main:
f33c80a8faa628f6c8ef8978c4d38c81a52c331e.
R6 source:
2e4e8cc92f12cd6fcb420bd02d84c9b43ed0d380.

R6 представлен автором; это задание НЕ объявляет его независимо принятым и НЕ повторяет
старые замечания как доказанные дефекты R6. Проверить, что уже исправлено, сохранить эти
исправления, доделать только фактический остаток установленного контракта.

При старте сверить origin/main и чистоту worktree. Новые согласованные коммиты сохранить;
локальные изменения не сбрасывать. Публиковать fast-forward без force.

## Фиксированный объём

Это завершение прежнего задания, а не новый цикл требований:
- docs/architecture/P8C_EXECUTABLE_PACKAGE_COMPLETION_TASK_20261104.md — критерии готовности §5;
- docs/architecture/P8C_REVIEW_c8007f5_EXECUTABLE_PACKAGE_R5_20261105.md
  в commit 4ade3d5d6b238eb610212e81524325688818a896 — остаток R4-01…05;
- исходный принятый release/readiness/deployment дизайн и численные пределы сохраняются.

Сначала сверить все пункты с текущим кодом, а не только переданные regression-тесты.
Использовать одну актуальную requirement→code→test→result таблицу в существующем runbook.
Подтверждённые исправления не переписывать ради оформления. Новые пожелания вне MVP
вынести за пределы этого задания; они не блокируют текущую source-приёмку.

Разрешены необходимые правки release/seed templates и helpers, readiness executor,
их offline-тестов, runtime manifest, runbook/gate drafts и нового evidence.
Принятые приложение, collector/инвентарь 9/9/S1, PG17, candidate NetworkPolicy YAML,
контракт шести политик, 14-flow/offline design не переоткрывать.

## Что должно работать целиком

### A. Readiness: один исполнимый процесс S0→S4

Через реальные entrypoints проверить S0/S1/S2a/S2b/S3/S4: допуск → чтения → baseline →
WAL/health verdict → связанные receipts → следующая стадия.

Обязательны:
- один разрешённый запуск окна; слоты 0/300/600 от начала окна, максимум три samples;
  failed/completed/UNKNOWN_OUTCOME не выдают новый бюджет; конкуренция и смена state-dir
  не обходят authority;
- baseline только из валидного наблюдения; identity/time сохранены; S0 сравнивает со
  временем первого baseline sample, следующие стадии — с подтверждённой границей операции;
  FAIL/reset/неполный sample не стирает доказательство предыдущего состояния;
- health W/I/N, shared DB/ARCH GET, freshness на момент итогового PASS;
- typed per-read envelope/kind/apiVersion/scope/limits и точные predicates PR-3/5/6, HC-*;
- фактические attempts/bytes/elapsed, включая ошибки/частичный ответ, учитываются и
  устойчиво сохраняются; проверки remaining budget идут до следующего I/O;
- отдельные sample/window/WAL/HC/PR/общие пределы: WAL 90 req/36 MiB/3960s,
  общий 233 req/179 MiB/5265s; окно 15 req/6 MiB/660s; sample 5 req/2 MiB/30s;
- реальные hard deadlines и body caps внутри transport, cleanup и отсутствие
  proxy/redirect/fallback; post-return проверки сами по себе недостаточны.

В E2E разрешено подменять часы, ожидание, transport и внешние процессы. Нельзя подменять
проверяемые predicates/state machine/scheduler готовым PASS. Positive route и каждый
блокирующий failure route должны быть достижимы через production code.

### B. Release и seed: исполнимые маршруты, не только YAML qualification

Проверить production steps с fake tools/ответами:
- seed REUSE и STOP выполняют ноль build/push; CREATE_ALLOWED доступен только по
  корректному future gate с фактической source/package/repository/time binding;
- доставка будущего gate в workflow описана и реализована в source; файл не появляется
  «сам собой» в RUNNER_TEMP;
- setup → bounded ready → build → registry/private/association proof → cleanup;
  cleanup также на build/readiness/verification failure и предусмотренной отмене;
- source-bound seed tag, минимальный not-deployable seed и enforced seed/application
  distinction; public package/403/timeout не превращаются в разрешение первого создания;
- release gate до protected operations: immutable source/workflow/package, expiry,
  permissions и run-attempt; один build/digest связан с SBOM/scan/signature/attestations;
- неверный или отсутствующий обязательный proof даёт nonzero; успешный synthetic
  baseline действительно проходит весь маршрут.

Отдельно сохранить различие: source проверяет исполнимость и связи; реальные registry
visibility, runner availability и криптографическое выполнение будут проверены в CI
после отдельного допуска. Сейчас не запускать реальные build/push/sign/attest.

### C. Устранить зависимость тестов друг от друга

Проверить объяснение R6 о cross-test artifact. Если причина — общий fixed gate и
RESERVATION_BASE, исправить изоляцию АКТИВНОГО test harness: уникальная временная authority
на тест и явное совместное состояние только внутри сценария replay.

Исторический residual_test.py в evidence не редактировать. При необходимости использовать
его рабочую копию в source test suite с ссылкой на оригинал и точным описанием изменения
fixture/setup/teardown. Assertions replay/failed-блокировки сохранить. Не ослаблять
production-защиту, не исключать тест и не заменять его xfail/skip ради зелёного отчёта.

Проверить одиночный, полный и изменённый порядок затронутых тестов. Исправный тестовый
harness — часть текущей работы, отдельного Owner-допуска не требует.

## Как выполнить без новых мелких остановок

Работать непрерывно до завершения A/B/C и полного прежнего §5. Промежуточные коммиты
разрешены; они не требуют отдельного review или нового «продолжай». Статус промежуточной
работы — SOURCE_WORK=IN_PROGRESS/PARTIAL.

Сначала закончить код и адресные проверки, затем один итоговый прогон полной offline suite
на окончательном source SHA. Повторять полный прогон только после изменений, влияющих
на результат, или для разрешения обнаруженной ошибки.

Ранее принятые application/PG17/inventory/policy/backup/restore/PITR/failover проверки
не повторять. Public pins использовать с уже проверенным cache/evidence; без необходимости
не скачивать upstream заново и не менять версии.

Документальные недочёты исправить в том же пакете. Самостоятельные циклы ради формулировок
не создавать. Однако расходящиеся SHA, ложный PASS или отсутствующее доказательство
обязательной проверки — существенные ошибки, их нельзя считать косметикой.

## Единственный итоговый пакет

1. Source commit ДО финального прогона. Зафиксировать SHA и hashes фактически исполняемых файлов.
2. Один launcher полной offline suite с nonzero при любой обязательной ошибке. Все production
   positive/negative routes и активные regression-тесты проходят вместе; число методов —
   справочная величина, не критерий готовности.
3. Полный вывод каждого прогона: argv, cwd, UTC start/end, версии, exit, stdout/stderr.
   Result/manifest/transcript согласованы машинной сверкой. Не только tail и сводка.
4. Один актуальный runbook + полный runtime manifest + requirement→code→test→evidence matrix.
   Принятые ограничения и команды соответствуют фактическому коду.
5. Новый evidence commit после source/tests. Исправления прошлых отчётов — отдельной
   correction note, без переписывания исторических evidence.
6. Короткий итог: что готово, какие проверки PASS, точные source/evidence SHA,
   какие исключительно внешние факты остаются NOT_EXECUTED.

Итоговые статусы:
SOURCE_PACKAGE_READY_FOR_REVIEW=YES — только если весь source-контракт завершён.
SOURCE_ACCEPTANCE=AWAITING_ARCHITECT.
CI_RELEASE/LIVE_READINESS/PRODUCTION=NOT_EXECUTED.
P8C=NOT_FINAL_ACCEPTED; P8D–P8G/P9=NOT_AUTHORIZED.

Если остаётся source TODO, не писать «осталось только CI/live». Продолжать исправление.
Итоговый STOP допустим после полного пакета либо при конкретном непреодолимом внешнем
blocker, когда вся независимая работа закончена. Для blocker указать точное отсутствующее
условие и одно необходимое действие владельца, без запроса секретов в чат.

## Граница допуска

Это разрешение ЗАВЕРШИТЬ SOURCE, а не выполнять deployment.
Запрещены новые SSH/live-readiness/cluster reads, private-registry операции, реальные
Owner helpers, workflow publication/dispatch/token, CI release/bootstrap push,
NetworkPolicy apply и production migrations/deployment.

После независимой source-приёмки Архитектор подготовит конкретный execution-пакет.
Hermes не открывает его самостоятельно. Реальное clock evidence и будущие CI/runtime
факты остаются внешними prerequisites; offline реализация и её проверка от них не зависят.
