# TASK: P8C-R1-EXECUTABLE-PACKAGE-COMPLETION

Дата: 2026-11-04 (Europe/Moscow).
Исполнитель: ОСНОВНОЙ HERMES. Hermes2 не участвует.
Repository: dedvmedved-dot/otus-diplom. Source of Truth: GitHub main.
Проверенный checkpoint: fb1935883d723c6f85a45d0b0856c9d7f36ee2c5.
Это завершение текущего P8C-R1-EXECUTABLE-RELEASE-AND-READINESS-R1, не новый этап проекта.

## 1. Результат, который требуется сейчас

Завершить ОДИН исполнимый SOURCE-пакет release + private seed + readiness/WAL.
В нём должны работать все обязательные ветви исходного задания и ER-01…08,
проверенные через реальные entry points/helpers на подставных transport/tool responses.

Промежуточные commits и короткие progress reports допустимы. Они не означают STOP,
не требуют Architect review и нового «продолжай». Не завершать работу после очередного
добавленного модуля, нескольких тестов или заполнения части документа.
Довести текущую работу до конечных критериев §5; затем один итоговый STOP для независимой проверки.

Не вводить новые возможности, дополнительные уровни orchestration или новые виды проверок
платформы. Действующие требования и принятые бюджеты не увеличивать.

## 2. Authority / recovery / границы

Прочитать целиком:
1. docs/architecture/P8C_EXECUTABLE_RELEASE_AND_READINESS_R1_TASK_20261104.md
   (опубликовано 5d71dfc345cfacfe98bff42381b7aa36984a7bed).
2. docs/architecture/P8C_REVIEW_713a745_EXECUTABLE_RELEASE_READINESS_20261104.md
   (опубликовано 6249b979ed6486704a1fcdbe234bbe153df27c68).
3. Три согласованных gate-draft и текущий
   docs/architecture/P8C_EXECUTABLE_RELEASE_READINESS_RUNBOOK_20261104.md.

Этот документ уточняет порядок завершения; не заменяет полный технический контракт
двух документов выше и не отменяет подпункты, отсутствующие в коротком отчёте.

Fetch main, проверить HEAD/diff/clean tree. Учесть публикацию данного задания после checkpoint.
Не сбрасывать локальную работу. Неожиданные противоречащие scope изменения — STOP с конкретным diff.

Подтверждено Connector при выдаче:
- main = fb1935883d723c6f85a45d0b0856c9d7f36ee2c5;
- исходный task blob 626a88d3f68de139d55b829407ff3a0cd239e0d7;
- review ER-01…08 blob fa16582d1281548f32d357fd9455fd0d2cd2ff7f;
- seed template blob 5a63cee349133ff392caa7c2cb9e810970757712;
- wal.py blob 9ab5ffe7459e3263a3bc9f3ec550bf67d10e184c.
Это recovery/source binding, не приёмка checkpoint и не утверждение, что все функции проверены.

Допуск сохраняется: source implementation, локальные offline tests и public pin verification
в ранее определённом узком scope; публикация source/evidence в main fast-forward.

Запрещены: SSH/live cluster/readiness, private registry probes, реальная OCI build/push/sign/attest,
CI dispatch/workflow publication (никаких .github/workflows/), Owner helpers, policies apply,
production migrations/deployment. Не использовать workflow token/раскрытые пароли.
Допускаются только templates и fake command runners для проверки будущего release/seed.

Сохранить без изменений application/web/migrations/RBAC/production manifests, candidate policies/
frozen contract, inventory/collector/S1 и принятый design. Не повторять 9/9 inventory, policy107,
native PG17, backup/restore/PITR/failover. Исторические evidence не редактировать.

## 3. Закончить остаток по всему контракту

| Блок | Что должно быть закончено | Что недостаточно |
|---|---|---|
| ER-01 | Все PR/HC predicates, shared DB response, stage applicability, W/I/N/freshness; PR6 baseline comparison | наличие функций без сквозного исполнения |
| ER-02 | Typed source/hash-bound gate, UTC expiry, atomic run/stage state, receipts, no replay/skip, meaningful exits | только формат SHA, переданный флаг consumed или новый output path |
| ER-03 | Exact read allowlist, typed bounded projections, hard deadlines/cleanup, safe journal с реальными exits/counts | regex пути, cap после полного чтения, отсутствие canary только в happy path |
| ER-04 | WAL client/parser/bracket, scheduler, baseline/receipt/state, clock evidence validator, суммарные budgets | добавленный wal_sample без полного безопасного маршрута |
| ER-05 | Release gates/runner contract/immutable sources/verified tools/required artifacts/qualifier negative cases | qualified:true от проверки наличия строк |
| ER-06 | Полный seed decision tree и исполнимый recipe/lifecycle/evidence | комментарии NOOP/Owner approval без управления последующими steps |
| ER-07 | Проверенные bytes с честным provenance, безопасные URL/errors, aggregate nonzero, source binding | ALL_VERIFIED без границ доказательства и с placeholders |
| ER-08 | Полная matrix, runtime manifests, literal runbook, фактические tests/transcripts/scans | таблица имён файлов и общий счётчик PASS |

Точки, которые необходимо исправить/проверить по текущему checkpoint:

### Seed

В текущем template exit 0 в precondition завершает только этот step. Условие следующих
steps !startsWith(github.event.repository.full_name, 'noop') не связано с результатом
private-check и для нашего repository истинно.

Сделать явный typed result precheck (REUSE / CREATE_ALLOWED / STOP), job/step outputs и
условия downstream steps. REUSE обязан давать НОЛЬ build/push вызовов; STOP — также ноль.
Не использовать имя repository или текст echo как переключатель.

Завершить exact recipe location/content, verified BuildKit setup/start/readiness/cleanup,
source-bound unique tag, минимальные job permissions, timeout/gate/run budget,
registry-byte/digest/private/association proof и seed≠application artifact.
Первичное создание требует предусмотренного будущего Owner основания; произвольного env
SEED_FIRST_CREATION_APPROVED=true недостаточно. Наличие package и доступ к нему сейчас не проверять.

### WAL / clock

validate_clock в текущем wal.py принимает число. Это не контракт evidence.
Нужны типы/finite nonnegative numeric bound<=5, источник/provenance, node/backend identity,
observed time/validity и hash-binding с gate. NaN/Inf/negative/bool/missing/wrong-node/expired
не должны разрешать PASS. Условный "trusted=true" без происхождения не является доказательством.

Реальный clock source может оставаться UNRESOLVED с ОДНИМ точным future read proposal,
но его формат/валидация и synthetic positive/negative tests должны быть реализованы.
Для source-квалификации реальные clock data не нужны; для будущего live PASS — обязательны.

Проверить весь original WAL contract: обязательные identity/owner/IP/role/restart markers до/после,
нельзя принимать отсутствующий UID через None==None; duplicate/nonfinite/malformed metrics;
failure/reset precedence; operation boundary + верхняя граница sample_end+5s;
первый S0 sample — baseline, сам по себе не доказательство нового WAL-прогресса.
Baseline и operation receipt брать из проверенного state/binding, не доверять произвольным
входным числам. Не расширять принятый read-set ради этой проверки.

Бюджеты прежние: WAL 5 requests/sample, <=3 slots/window, 6 windows, 90req/36MiB/3960s;
общие ceilings 233GET/179MiB/5265s observation. Limits задаются исполнимым кодом,
а не только константами. Transport failures/restarts не обнуляют расход/разрешение.
Слоты и deadlines проверять виртуальными часами без реального ожидания 300/600 секунд.

### Release / qualification

Проверить все R-01…08, а не только последние изменения release-check.py.
Сохранить и завершить source/workflow revision binding, gate before protected operations,
rerun/expiry, permissions, tool/path verification, rootless cleanup, scan/sign/attestation outcomes.
Qualifier обязан отвергать нарушенные parsed templates/helpers и неверные artifacts.
Отдельные shallow checks не объявлять полной квалификацией.

## 4. Одна сквозная offline acceptance suite

Сделать один документированный запуск suite для всего нового executable package.
Разрешено запускать несколько команд внутри runner. Не создавать новую универсальную платформу тестирования.

Suite использует production entry points/helpers/step logic, подменяя только внешний транспорт,
tool executables и clock/state fixtures. Она не должна тестировать другую, упрощённую реализацию.
Test-only hooks не становятся обходом проверок в production CLI.

Обязательные группы:

A. Readiness:
- валидный S0 -> разрешённая последовательность S1/S2a/S2b/S3/S4 с synthetic action receipts;
- проверенные baselines и clock evidence; все обязательные health/WAL predicates;
- точные requests/stage applicability, counters/bytes/time/state/journal и exit codes;
- negative matrix G5: unhealthy/stale/partial/malformed/oversize/slow-body/timeout/identity drift/
  reset/failure/idle/clock invalid/gate mismatch/replay/crash.
Не заменять exact verdict утверждением PASS OR INCONCLUSIVE.

B. Release:
- synthetic successful chain: gate -> verified tools/test outcomes -> single build digest ->
  private/registry -> scans/signature/two attestations -> complete artifact validation;
- gate/hash/source/revision/expiry/rerun failures до protected operations;
- private metadata/HTTP failures и invalid/missing artifacts/scans/signatures/attestations ->
  FAIL/INCOMPLETE без accepted image.
Fake command success не выдаётся за реальную Cosign-криптографию или успешный CI.

C. Seed:
- existing private associated -> REUSE, build/push count=0;
- public/wrong repo/ambiguous access/missing prerequisite -> STOP, push=0;
- explicit synthetic valid first-creation gate -> bounded setup/build/push/verify sequence;
- setup/readiness/push/registry/private/digest failure -> non-PASS;
- seed artifact не принимается как Portal release.
Никаких фактических registry обращений, downloads/build/sign/push из этих tests.

D. Review regressions:
- включить смысл supplied 22-method regression suite из
  evidence/P8/20261104-713a745-architect-review/regression_test.py;
- при изменении интерфейсов адаптировать вызовы с явной traceability; не ослаблять assertions;
- дополнить positive controls и полными case groups исходного G5.
Не назначается искусственная квота числа тестов: требуется покрытие каждого обязательного исхода.

Pin verification повторно массово не скачивать без причины. Можно переиспользовать verified cached
bytes/immutable evidence с их пределами; недостающие public facts получать в разрешённом scope.
Не терять уже выполненную полезную работу и не менять версии самостоятельно.

## 5. Конечный критерий SOURCE_PACKAGE_REVIEW_READY

Перед итоговым STOP Hermes сам проверяет одновременно:

1. Все обязательные source requirements G1–G6/ER-01…08 имеют code + test + evidence.
   Нет TODO/stub/caller-not-implemented в обязательном маршруте.
2. Полная suite реально выполнена на окончательном source SHA. Все expected valid cases проходят,
   все expected denial/error cases дают точный fail-closed результат и не выполняют запрещённый шаг.
3. Runtime manifest содержит все imports/executed helpers/templates/readsets/fixtures роли,
   full hashes/blob/source SHA; опубликованные entry points запускаются из комплекта без
   неучтённых файлов на машине автора.
4. Runbook соответствует фактическим CLI/paths/schema/exit codes; три drafts синхронизированы
   только в пределах текущей реализации. Не переписывать принятый дизайн.
5. Source commit предшествует прогонам; evidence публикуется отдельным commit.
   Полные команды/cwd/UTC/versions/exits, source и evidence scan с frozen inputs, output вне inputs.
   No-match не выдаётся за абсолютную гарантию; signed CDN query/credentials не сохраняются.
6. Remaining external prerequisites перечислены отдельно с конкретным owner/fact.
   CI runtime, actual private GHCR, real clock evidence и live readiness остаются NOT_EXECUTED.
   Они не маскируют незавершённую независимую разработку.

Один итоговый отчёт: source SHA / evidence SHA / matrix / suite command и результаты /
full package manifest / точный остаток внешних prerequisites / NEXT_GATE_REQUEST.
Статус REVIEW_READY не равен Architect ACCEPTED или runtime PASS.

## 6. Рабочий режим и STOP

Продолжать автономно по всему остатоку. Не спрашивать «продолжать?» после каждого ER.
Не называть очередной частичный проход «итоговым», даже если его локальные тесты зелёные.
До выполнения §5: SOURCE_WORK=IN_PROGRESS/PARTIAL.

Итоговый STOP допускается:
- полный пакет готов по §5;
- либо конкретный непреодолимый внешний blocker, с доказательством и перечнем уже завершённой
  независимой работы. Отсутствующая функция/тест/setup — инженерный остаток, не внешний blocker.
При настоящем противоречии source-of-truth/границам доступа STOP немедленно.

Публикация ff-only, no force, remote HEAD/readback. Concurrent main changes учитывать,
historical evidence не изменять. При source-byte changes повторить релевантные qualification checks.

CI_RELEASE / WORKFLOW_PUBLICATION / WORKFLOW_DISPATCH / SEED_PUSH=NOT_AUTHORIZED
LIVE_READINESS / SSH / PRIVATE_REGISTRY_PROBES=NOT_AUTHORIZED
NETPOL_APPROVED_FOR_APPLY=NO
OWNER_HELPERS / PRODUCTION_MIGRATION_DEPLOYMENT=NOT_EXECUTED
P8C=NOT_FINAL_ACCEPTED
P8D–P8G/P9=NOT_AUTHORIZED

После независимой source-приёмки будет рассматриваться отдельный execution gate.
Настоящее задание не открывает его.
