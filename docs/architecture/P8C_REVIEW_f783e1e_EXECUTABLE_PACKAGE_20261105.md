# P8C review f783e1e — executable package NOT ACCEPTED

Дата: 2026-11-05 (Europe/Moscow).
Исполнитель: Architect. Адресат исправлений: ОСНОВНОЙ HERMES; Hermes2 не участвует.
Verdict: REWORK_REQUIRED / SOURCE_WORK=IN_PROGRESS/PARTIAL.
Это проверка полноты действующего задания, не новый scope и не execution gate.

## 1. Source of Truth / метод / пределы

Connector подтвердил main=f783e1ed6d34de9188b71ad1f6bedf9ccdf1ec51.
Цепочка: e0c2d3bb2364e6ac063d49e86b900c687de75615 ->
8ffd45792123e8e2ae1ccdd330ee5e1d013523f9 (только seed template + test_release_negative.py) ->
e5a6f83cc553e9a57832a2082c363b7f31f9ed4c (3 evidence-файла) ->
f783e1ed6d34de9188b71ad1f6bedf9ccdf1ec51 (result.md).
Разделение source/evidence теперь соблюдено. 20 полученных файлов сверены по Git blob
по точным байтам; source-audit.json содержит полные hashes.

Authority остаётся:
- docs/architecture/P8C_EXECUTABLE_RELEASE_AND_READINESS_R1_TASK_20261104.md;
- docs/architecture/P8C_REVIEW_713a745_EXECUTABLE_RELEASE_READINESS_20261104.md (ER-01…08);
- docs/architecture/P8C_EXECUTABLE_PACKAGE_COMPLETION_TASK_20261104.md, commit
  940c4e73940c26a01c5af19d6c75b82356eb7701, особенно §§3–5.

Независимо повторены 23 readiness + 3 qualification + 4 release + 7 negative methods:
все exit=0; static qualification выдаёт qualified:true.
Это подтверждает отчёт о выполнении именно этих тестов, но не полноту контракта.
Независимый desired-contract regression: 28 methods, 36 failed assertions/subtests,
exit=1, без errors; один positive payload-binding control проходит.
36 — не число самостоятельных дефектов: ниже они объединены в 8 блоков ER.

Evidence: evidence/P8/20261105-f783e1e-architect-review/
- regression_test.py — воспроизводимые проверки существующих требований;
- execution.json — реальные argv/cwd/UTC/Python/exit/stdout/stderr;
- source-audit.json — source bytes;
- review-scan.json — frozen inputs и ограниченный heuristic scan.

Все transport/tool responses подставные; seed start-step выполнен с fake
unshare/rootlesskit/buildctl. Нет SSH/kubectl/live/registry/OCI build/push/sign/attest.
Публичные binary assets и уже принятые Portal/PG17/policy/inventory тесты не повторялись.
Payload fixtures синтетические: успешный контроль НЕ является Cosign crypto verification.

## 2. Что сохраняется и не переоткрывается

Checkout до seed precheck добавлен; downstream CREATE_ALLOWED conditions присутствуют.
Hash mismatch, ряд gate/predicate checks, missing artifact/digest/source/attestation bindings,
bounded body cap, error nonzero и часть WAL checks существуют и полезны.
Сохранять их; не откатывать к старой реализации.

Candidate policies/frozen contract107, application/DB/collector/S1/inventory9/9,
принятые design/budgets остаются вне доработки. Live clock и CI runtime действительно
не исполнены. Однако перечисленные ниже исходниковые дефекты устраняются offline.

## 3. Обязательный остаток — один пакет, ER-01…08

### C-01 / ER-06: seed lifecycle и decision tree

Подтверждено source и выполнением literal start-step с fake tools:
- EXIT trap в отдельном шаге Start rootless BuildKit убивает BK_PID при успешном
  завершении ЭТОГО шага, до Build + push в следующем shell. Fake daemon готов,
  readiness проходит, затем trap завершает daemon. Это не CI availability blocker.
- Build step работает из корня checkout, --local dockerfile=. и filename=Seed.Containerfile;
  реальный файл находится portal/tools/Seed.Containerfile. Рабочая директория не задана.
- Private-check errors схлопнуты: произвольная env-строка
  SEED_FIRST_CREATION_GATE=approved-by-separate-owner-gate превращает любой nonzero
  (включая public/wrong association/403/ошибку helper) в CREATE_ALLOWED.
  Typed отдельный gate отсутствует. STOP выходит 0, следующая ветвь лишь пишет evidence.
- Tag bootstrap-seed общий, не source-bound unique. Post-step только private-check;
  registry byte/digest proof для seed не вызывается. seed_not_application_digest —
  JSON boolean от сравнения с возможно пустым APP_IMAGE_DIGEST, не enforced assertion.
- REUSE/STOP zero-build conditions появились; полного исполнимого теста всех трёх
  ветвей и setup/push/postverify failure paths нет.

Исправить по ER-06: согласованный lifecycle start→readiness→build→verify→cleanup,
одна ответственность за cleanup на success/failure; recipe/source path; typed gate
до protected operations; корректная различимость private/access/first-creation;
STOP non-PASS; binding/tag/registry/association/seed≠app. Проверить literal step logic
fake executables, counts=0 в REUSE/STOP, полный successful CREATE_ALLOWED и его ошибки.
Не выполнять настоящие setup/download/build/push из тестов.

Tests: Seed.test_daemon_survives_until_build_step,
test_recipe_resolves_at_actual_working_directory,
test_failed_precheck_cannot_create_from_magic_env, test_stop_is_non_success.

### C-02 / ER-05: release validation и qualification всё ещё shallow

Независимый валидный synthetic artifact set проходит реальный release-check.py verified.
Замена ОДНОГО файла на public metadata / wrong repository / wrong registry digest /
manifestVerified=false / CRITICAL scan / scan=[] всё ещё даёт exit=0,
payloadBinding=PASS. JSON parse не проверяет семантику этих артефактов.

Новая negative suite начинает с {} во всех файлах. Scan/provenance/SBOM negatives
останавливаются раньше — на build-metadata digest; целевая проверка не достигается.
Седьмой test_digest_mode_accepts_valid передаёт неправильный stdin вместо filename
и допускает любой exit из (0,1,2). Успешного verified E2E он не проверяет.

Qualifier по-прежнему:
- часть условий читает из исходного текста на диске вместо переданного parsed object;
- допускает дополнительный push trigger, лишнее actions:write;
- не отвергает mutable checkout ref/action;
- допускает seed без build route при сохранении слова private.
Все четыре mutations воспроизведены.

Release template не содержит исполнения gate/source package/expiry/run-attempt
проверок перед protected operations. github.sha checkout — полезный immutable checkout,
но не замена binding согласованного application/workflow package и one-run gate.
Rootless release step не имеет cleanup trap. Runner dependency contract не завершён.

Исправить весь R-01…08 по исходному заданию, не только final JSON helper:
точные parsed templates, future gate binding/expiry/rerun, permissions всех jobs,
verified tool path, lifecycle, требуемые semantic artifacts и связь с успешными
scan/sign/verify steps. Реальный crypto остаётся CI_ONLY; fake failures должны
доказывать отсутствие accepted release. Negative cases строить от independently
successful fixture, менять одно условие, проверять достижение нужной ветви.
REUSE/seed artifact не принимается как application release.

Tests: Qualification.test_invalid_templates_rejected (4),
Release.test_positive_payload_binding_control,
test_invalid_semantics_rejected_from_valid_baseline (5),
test_author_negative_fixtures_reach_named_check (3).

### C-03 / ER-01: readiness predicates и scheduler

Воспроизведены ложные PASS:
- PR-3 проверяет ep.ports, но EndpointSlice ports находятся на уровне item. Unready
  addresses с UDP9999 и дополнительным IP проходят; используется subset вместо exact tuples.
- PR-6 проверяет только первые пять empty lists. Tier/Felix/namespace/Pod baseline
  не сравниваются; новые Tier/Felix допускаются.
- HC-OP принимает phase=Running без Ready=True и без запрета terminating Pod.
- HC-DNS принимает ready=true без адреса и TCP/UDP53.
Дополнительно source: PR-5 не связывает UID/selector/ownership, HC-PORTAL не проверяет
spec.replicas и допускает None==None generation; HC-GW также допускает отсутствие generation
при отсутствующем observedGeneration. Типизированные identity/required fields не обеспечены.

main выполняет один проход всех checks, а не нормативные W/I/N/freshness windows.
HC-DB и HC-ARCH-STATE читают Cluster отдельно. Нет shared response и полного scheduler.

Довести predicates и исполнение без изменения принятых budgets/readset.
Tests: Predicates.*. Требуются и полноценные positive controls, весь stage success path,
точные per-check outcomes/requests/counts; не только общий INCONCLUSIVE на пустом mock.

### C-04 / ER-02: gate/state не обеспечивает последовательность и привязку

Воспроизведено:
- S4 разрешается первым, без S0 и action receipts.
- Тот же gate с новым --state-dir исполняется снова; с прежним каталогом run.reserved
  блокирует вообще любой следующий stage. Это не модель S0→S1→S2a→S2b→S3→S4.
- --now остаётся production CLI и позволяет использовать истёкший gate.
- package_hash() = readset + wrapper, НЕ включает импортируемый wal.py.
- существующий output заменяется os.replace.
Source: source_sha только format-check; stage не связан с разрешённой стадией gate;
baseline/operation_end берутся прямо из gate без verified receipt/state.

Реализовать существующий typed source/runtime-manifest gate, fixed run identity/state,
атомарные stage reservations/receipts, budgets и crash/UNKNOWN_OUTCOME по контракту.
Новый output/state path не выдаёт новое разрешение; последующая разрешённая стадия
не блокируется безусловной общей меткой. Clock injection — test-only, не --now bypass.
Output preexistence проверять до запросов и не перезаписывать evidence.
Tests: GateState.* (5).

### C-05 / ER-03: transport/envelope/journal

validate_envelope принимает wrong API/SecretList/continue:null как обычный List;
required identity/GVR/scope и max_items из readset не enforced. Проверка path — regex +
частичный substring deny, не exact approved read allowlist.

Блокирующий stdout.read может ждать за hard deadline: fake child молчит 6 секунд,
timeout=0 задаёт текущий кодовый deadline +5s; возврат/ошибка случается только после
6s. Это воспроизведение самого отсутствия interrupt, не предложение timeout=0 для live.
Piped stderr до окончания stdout также не дренируется параллельно.
Observed ResourceWarning показывает незакрытые pipes error-path.

Журнал содержит aggregate attempt/duration/detail, но не per-request UTC/path/real exit/
bytes/counts. str(e) и значения conditions не являются конечной value-free диагностикой.
Bounded HTTP не отключает environment proxy: build_opener(NoRedirect) добавляет default
ProxyHandler. Проверено без сетевого вызова.

Нужны реальные hard deadlines при stalled/slow body, bounded stderr, kill/wait/close,
точная схема/projection/allowlist/complete semantics, safe per-request journal.
Tests: Transport.test_blocking_body_obeys_hard_deadline,
Predicates.test_wrong_list_kind_and_explicit_null_continue_rejected,
WALContract.test_default_http_has_no_environment_proxy.
Не возвращать raw objects и credential-bearing stderr.

### C-06 / ER-04: WAL источник исполнен, нормативный протокол — нет

Положительные UID checks сохраняются, но sample пропускает:
- смену currentPrimary в завершающем Cluster;
- смену Pod IP/restart/owner в завершающем Pod;
- duplicate series (last wins) и невозможный future timestamp;
- первый baseline sample даёт PASS вместо отсутствия доказанного WAL progress.

Clock validator проверяет формат/поля, но не expiry/фактическую привязку node/backend
к sample. gate_hash optional и caller его не передаёт; наблюдение 2020 года с другим
node и wrong gate hash принимается. Real clock evidence остаётся будущим prerequisite,
но это не оправдывает отсутствие source validator.

run_wal_sample делает metadata requests с 15s/1MiB вместо 5s/256KiB.
Budget class/fetch_metrics не используются main route. Нет 30s sample deadline,
slots 0/300/600, 660s window, shared persistent stage/global requests/bytes/time counters.
Нет upper timestamp bound sample_end+5s, persisted verified baseline/operation receipt.
Потенциальный URL из podIP создаётся без IP validation/owner binding.

Завершить существующий протокол, убрать/согласовать дублирующие неиспользуемые wal_sample
и parse_archiver_metrics в wrapper. Не увеличивать readset/budgets.
Tests: WALContract.* (8). Проверить positive fresh progress и negative reset/idle/
role/IP/owner/restart/clock/dedup/future/budgets через actual main route с fake transport
и virtual clocks. Никакого реального ожидания 300/600 секунд в suite.

### C-07 / ER-07: pin evidence/error path

Не оспаривается заявленный автором public bytes verification; downloads не повторялись.
Положительный sanitize_url и aggregate nonzero сохранять.
Но error fields всё ещё сохраняют str(e)[:200]: mock exception с URL ?sig=SYNTHETIC_CANARY
попадает в JSON. Исправить конечной диагностикой/безопасной projection, не хранить signed URLs.
Source output всё ещё source_sha=RECORDED_AT_COMMIT; action/image results без per-item UTC,
image mediaType не записан; http_get_follow не ограничивает redirect hosts.
Текущий verify_binary всегда скачивает, не читает cached bytes: слово cached в отчёте
не является отдельной реализованной ветвью. Реальную методику повторного использования
immutable evidence указать явно, массовый download не требуется.
Test: PinDiagnostics.test_exception_diagnostic_cannot_echo_signed_query.

### C-08 / ER-08: доказательства и полнота suite

Новый source-manifest.txt с 15 полными blobs/hashes — полезное улучшение.
Однако runbook остаётся шестью широкими matrix rows с 20 PASS и не представляет
полный requirement→entry point→test-case→evidence contract. В нём hash объявлен
readset+wrapper+wal, код считает только первые два; указано clock_skew_bound,
caller использует clock_evidence. Три gate-draft сохранены в старых bytes, release
draft manifest ссылается на старые template/helper hashes.

raw-transcript.txt содержит итоги и SOURCE_SHA, но не полные argv/cwd/start/end/exit
для каждого прогона. Readiness suite имеет один main negative route; нет полного
successful stage sequence. Release/seed orchestration E2E отсутствует.
Проверка bash -n и qualified:true этого не заменяет.

Сделать один документированный offline runner для групп A/B/C/D §4 completion task.
Полный runtime manifest всех импортов/exec helpers/recipes/readsets с roles/source/blob/hash,
runbook по реальным CLI/state/clock formats, точная matrix каждого requirement.
Sync gate drafts только в рамках accepted design. Source commit → suite → separate evidence.
Исторические evidence не менять.

## 4. Порядок завершения без очередных частичных STOP

Продолжать текущее задание автономно, нового «продолжай» не требуется.
Данный review не сводит scope к последним двум changed files: все ER-01…08 остаются обязательны.

1. Сначала собрать действующие end-to-end success routes readiness stages, release, seed
   на fake transports/tools; закрепить наблюдаемые requests/state/artifact chain.
2. Внести исправления C-01…08 в существующие модули. Не создавать новую платформу и
   не расширять accepted design. Сохранить исправленные позитивные ветви.
3. Negative cases от working positive controls; каждый target mutation должен быть
   действительно достигнут. Supplied regressions — воспроизводимые minimum checks,
   не замена полного оригинального G5. При смене интерфейсов адаптировать harness
   с traceability, не ослаблять assertions.
4. Самопроверка всего §5. Intermediate commits разрешены, status PARTIAL. Один final
   пакет после полной suite. Реальный внешний blocker описать конкретно лишь после
   завершения независимой source-работы.

Для regression из repository root:
P8C_REVIEW_ROOT="$PWD" python3 evidence/P8/20261105-f783e1e-architect-review/regression_test.py
Зависимости: Python3 stdlib + PyYAML; никаких реальных network/tool calls.
Тест lifecycle выполняет только fake executables, response-delay test занимает ~6 секунд.
Suite рассчитана на reviewed source interface; более поздний refactor требует явной адаптации.

## 5. Решение / границы

SOURCE_PACKAGE_ACCEPTED=NO
SOURCE_WORK=IN_PROGRESS/PARTIAL
READINESS_WRAPPER_SOURCE_QUALIFIED=NO
RELEASE_TEMPLATE_SOURCE_QUALIFIED=NO
PRIVATE_SEED_TEMPLATE_SOURCE_QUALIFIED=NO
NEXT_STEP=COMPLETE_EXISTING_SOURCE_TASK
NEXT_EXECUTION_GATE=NOT_ISSUED

CI_RELEASE / WORKFLOW_PUBLICATION / WORKFLOW_DISPATCH / BOOTSTRAP_PUSH=NOT_AUTHORIZED
LIVE_READINESS / SSH / PRIVATE_REGISTRY_PROBES=NOT_AUTHORIZED
NETPOL_APPROVED_FOR_APPLY=NO
OWNER_HELPERS / PRODUCTION_MIGRATION_DEPLOYMENT=NOT_EXECUTED
P8C=NOT_FINAL_ACCEPTED
P8D–P8G/P9=NOT_AUTHORIZED

Полнота source проверяется до допуска; сами CI crypto/runtime/private GHCR и live clock
останутся NOT_EXECUTED до отдельного execution gate. Они не заменяют C-01…08.

