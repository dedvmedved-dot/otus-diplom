# P8C — независимый review 52e2e38: тест authority исправлен, A/B остаются PARTIAL

Дата: 2026-11-06. Основной Hermes; Hermes2 не участвует.
Вердикт: **SOURCE_PACKAGE=REWORK_REQUIRED**. Продолжение задания
P8C-SOURCE-CLOSURE-SINGLE-PASS-20261106, commit
4786107c41c8e1ed9e69a17190a4bdf490f430b1, и review
87841166145e18254860c1c5e7ca200d24f10e34. Нового объёма работ или execution-допуска нет.

## 1. Независимая проверка и исправление reviewer-теста

Connector подтвердил цепочку:
87841166145e18254860c1c5e7ca200d24f10e34 →
a443b5caa56d7de18dd78a2ea407b5e76763f36d →
52e2e38673671eb7a19dfbf0eeafd4209c4d72cb.
Source commit 08:56:03Z, авторский transcript 08:57:08Z–08:57:54Z,
evidence commit 08:59:03Z. Source перед прогоном, evidence после — подтверждено.
Авторский launcher честно закончил `SUITE RESULT: FAIL`; автор сообщил 152/153, не общий PASS.

Все 153 test methods повторены независимо на точных Connector-blob bytes:
**152 PASS / 1 FAIL**, qualification CLI `qualified:true`.

**Замечание Hermes о единственном старом тесте подтверждено.**
`test_budget_cannot_reset_with_new_state_directory_and_same_receipt` после S0 пишет
233 requests в старый `state/budget.json`, затем использует другой state-dir.
Текущий source правильно хранит authority в `budget_path(gate)`.
Запись в неиспользуемый старый state-dir не доказывает сброс реального расхода.
Это устаревшая fixture reviewer-теста, а не самостоятельный дефект production.

Reviewer подготовил рабочую копию: изменена только запись exhausted budget на
`w.write_budget(gate, ...)` при той же private authority; assertions non-replay/zero I/O
сохранены. **34/34 PASS**, следовательно прежняя обязательная suite с этой поправкой —
**153/153 PASS**. Отдельный контроль настоящего exhausted authority + новый state-dir
также PASS. Исторический `completion_contract_test.py` не изменён.
Встроить эту fixture-поправку в активную suite можно в рамках текущего source-задания.
Не ослаблять production и не устранять эту ошибку теста изменением authority-семантики.

Но это не приёмка всего A/B. Дополнительные проверки **уже изложенных §§2–5 review
8784116**: **20 методов, 2 PASS / 18 failed assertions / 0 errors**. Это воспроизведения
оставшегося контракта, не 18 новых заданий. Есть два положительных контроля:
реальный authority exhaustion и корректный image@digest scan.

Evidence: `evidence/P8/20261106-52e2e38-architect-review/`:
- reexecution.json + reexecution-raw.txt — прежние 153 метода;
- completion_authority_working_test.py + completion-authority-fixture.diff +
  completion-authority-working.txt — единственная fixture-поправка, 34/34;
- residual_contract_test.py + residual-contract.txt + additional-execution.json —
  20 controls через настоящий main/CLI/template shell steps;
- source-audit.json, source-manifest.json, review-scan.json, syntax-execution.json.

Python reviewer 3.12.14; автор 3.11.15. Ответы API/HTTP и часы synthetic;
подпроцессы — локальные fake tools. SSH, кластер, CI, registry, build/push/sign не выполнялись.
Полный shell launcher повторно не запускался: verify-pins.py по-прежнему делает сетевые
запросы. Все его 153 test methods и qualification CLI выполнены отдельно с private TMPDIR.
Public pins не скачивались заново; авторский 10/10 не выдаётся за новый независимый прогон.

## 2. Что принято и сохраняется

Приняты исправления: budget path в authority, finite/nonnegative rejection, request charge
до I/O и его запись; exhausted requests и новый state-dir не обходят guard; failed/completed/
inflight replay guards; receipt сверяет issued_at; ожидания WAL входят в wal_seconds.
Приняты точечные fixes: incomplete metrics не стирают valid baseline; postgres restart
по имени; первичная проверка instanceRole; HC-DB kind, PR-6 kind-set, HC-OP cap;
кубectl timeout без прежних +5s; value-free Ready status.

Seed input передаётся через env, source mismatch отклоняется, generic private error
не даёт CREATE_ALLOWED, tag source-bound, добавлены registry proof и always-cleanup seed.
Qualifier теперь требует precheck. Launcher использует private mktemp authority без
глобального удаления live-state. C isolation и source→tests→evidence закрыты.
Эти исправления, accepted app/PG17/policy/inventory/design не переоткрывать.

## 3. Единый остаток A — исполнение readiness

### A1. Бюджеты/transport: counters ещё не равны hard limits

| Воспроизведение в production route | Результат на a443b5c | Требуемое поведение прежнего контракта |
|---|---|---|
| overall body remaining=1 byte | счётчик 187695449 при cap187695104; первая metadata response целиком прочитана | remaining body передать внутрь чтения; учитывать принятые bytes при любом исходе |
| overall remaining=1 second | S0 PASS, 300s elapsed, budget.seconds=5564 при cap5265 | запретить новое I/O/ожидание сверх remaining time; не проверять только на входе стадии |
| локальный fake kubectl пишет 64 bytes, затем зависает | 13 attempts, bytes=0 после timeout | partial/timeout/over-cap bytes должны сохраняться во время transport |
| HTTP EOF возвращается после deadline | default_http_get принимает позднее завершение | абсолютный deadline должен ограничивать блокирующее чтение и завершение, не только проверяться до read |

Тесты `test_remaining_body_byte_is_enforced_inside_io`,
`test_remaining_elapsed_second_cannot_authorize_300s_window`,
`test_timeout_partial_stdout_is_accounted`, `test_eof_after_deadline_is_not_accepted`.

Код: `_TRANSPORT['seconds']` не увеличивается во время исполнения; `_persist_budget_now`
не сохраняет elapsed overall. `_count_bytes` вызывается после возврата транспорта;
ошибка из select/read выбрасывает накопленные chunks. Per-request cap не уменьшается до
remaining global/WAL/sample/window body. В reverse health sweep duration_ms записан 0,
поэтому суммирование последнего journal дополнительно теряет время health-запросов.
`default_http_get` считает remain, но не использует его для ограничения блокирующего read.

Доделать весь существующий контракт budget: отдельные HC/PR/WAL/global пределы,
remaining requests/body/time внутри I/O и ожиданий, durable расход на всех исходах,
crash/concurrency-safe accounting. `os.replace` файла — атомарная замена, но сам по себе
не сериализует read/modify/write расхода и не доказывает crash durability.
Не заменять запись фактического расхода обрезанием счётчика до cap.

### A2. Health windows/freshness и typed observations

| Воспроизведение | Факт | Остаток |
|---|---|---|
| HC-DB readyInstances=2 в первом health observation, затем 3 | FAIL перезаписан итоговым PASS | сохранять failure precedence/STOP, не стирать отказ sweep-ом |
| Ready отсутствует, затем появляется | два GET в один момент 300.0/300.0, PASS | исполнить согласованные W/I/N, не два немедленных прохода |
| S4, каждый health GET занимает разрешённые 14s | PASS при возрасте HC-PORTAL 42s (>30s) | проверять свежесть КАЖДОГО обязательного observation на итоговом verdict |
| HC-OP item.status — строка | uncaught AttributeError | typed error + journal, без аварийного выхода вместо disposition |
| PR-6 NamespaceList items=[null] | PASS | валидировать typed namespace/pod selector context |
| PR-6 PodList содержит 201 объект | PASS | enforce max_items из readset для каждого списка |
| PR-5 Service namespace='other', labels прежние | PASS | точный namespace/identity и полный tuple-контракт |

Тесты `test_first_health_failure_is_not_erased_by_final_sweep`,
`test_health_retry_obeys_interval`, `test_portal_observation_fresh_at_s4_verdict`,
`test_nested_malformed_health_returns_typed_verdict`, `test_pr6_namespace_items_are_validated`,
`test_pr6_list_cap_enforced`, `test_pr5_rejects_wrong_service_namespace`.

Один reverse sweep не реализует принятый health scheduler. Прежний тест проверял возраст
HC-DB, поэтому перестановка DB в конец его исправила, но не весь freshness contract.
Сохранить shared DB/ARCH GET; принимать PASS только при допустимом возрасте всех нужных
наблюдений и расходе в рамках разрешённых окон. Полные typed per-read
kind/apiVersion/scope/identity/limits остаются обязательны: общий ALLOWED_API и endswith(List)
не заменяют GVR-binding, а проверка одного уровня не покрывает malformed nested containers.
Value-free diagnostics — включая неизвестные ключи, не только condition values.

### A3. WAL observation identity и граница операции

- `test_after_sample_role_change_blocks_pass`: after-Pod становится replica, но S0 PASS.
  `instanceRole` проверяется только в before-Pod. Проверить обе стороны bracket.
- `test_baseline_identity_survives_cross_sample_change`: UID стабилен внутри каждого
  sample, но меняется между samples; метрики нового UID сравниваются со старым baseline,
  получается PASS. Baseline-файл хранит metrics, но не observation identity/time.
- `test_current_operation_number_without_action_receipt_is_not_authority`: корректное
  по времени число operation_end_utc без связанного action receipt даёт S1 PASS.
  Проверка >=issued_at закрывает пример epoch=1, но не требование binding операции.

Доделать прежнюю binding: source/package/gate/run/stage/подтверждённая операция;
валидный baseline вместе с identity/time и проверкой при чтении; clock evidence связан
с конкретным gate, а не package hash, названным gate_sha256. Сейчас source_sha проверяется
regex, receipt — несколькими полями, clock — package_sha256. Не выдавать это за полную
trusted manifest/action binding. Не строить новую универсальную систему авторизации:
нужны только конечные поля и состояния уже принятого runbook.
Реальное clock evidence по-прежнему future prerequisite; эти source-правки выполняются offline.

## 4. Единый остаток B — исполнимые seed/release routes

| Проверка настоящего CLI/shell step | Наблюдение | Что завершить |
|---|---|---|
| release Future execution gate, корректный repo/sha/attempt=1, БЕЗ gate document | exit0, печатает GATE | реально доставить/проверить допуск source/workflow/package/expiry/attempt до protected operations |
| first-creation с совпавшим source, но gate.repository/package/workflow чужие | VERIFIED exit0 | сверять поля самого допуска, не только окружение GITHUB_REPOSITORY |
| scan-image имеет правильное имя repository, но digest b… вместо ожидаемого a… | payloadBinding=PASS | точное image@digest binding; substring IMAGE in ref недостаточно; отсутствие binding не PASS |
| seed Record step при обычном bootstrap, APP_IMAGE_DIGEST отсутствует | exit1: APP_IMAGE_DIGEST: unbound variable | закончить положительный CREATE_ALLOWED путь и enforced seed/application distinction без необъявленной зависимости |

Тесты `test_release_gate_cannot_pass_without_gate_document`,
`test_first_creation_wrong_package_rejected`, `test_scan_same_image_wrong_digest_rejected`,
`test_seed_record_positive_bootstrap_without_previous_app`.
Положительный контроль `test_scan_exact_image_digest_positive_control` проходит через
тот же `release-check.py verified` с правильным digest: failure не из-за неполной fixture.

В template APP_IMAGE_DIGEST не объявлен ни input, ни env, ни предшествующим producer.
Record step находится ПОСЛЕ build/push и registry proof. Добавление nonzero при равенстве
добавило отрицательный guard, но сломало нормальный bootstrap без существующего app image.
Нужно определить реальный конечный контракт seed≠app, не подставлять пустую строку и не
требовать существующий application digest для самого первого seed.

Остаток source audit из §4 review 8784116 также сохраняется:
- seed `always()` cleanup добавлен, release cleanup отсутствует;
- readiness loop 30×1s в обоих templates не ограничивает зависший `buildctl debug workers`;
- 404 выделен из generic error, но сам не доказывает отсутствие доступного package;
  CREATE_ALLOWED требует принятого конкретного first-creation основания, а не только exit2;
- seed upload содержит один seed-evidence.json; registry/private/build proof файлы не
  включены в возвращаемый полный seed package;
- qualified:true по-прежнему статическая/частичная проверка, не полный маршрут исполнения.

Завершить один fake-tool E2E каждого production route: REUSE/STOP дают 0 build/push;
CREATE_ALLOWED проходит setup→bounded readiness→build→postproof→cleanup;
release gate→single build→private/scan/signature/attestation bindings→artifacts.
На missing/wrong/expired gate и ошибках readiness/build/proof — нужный nonzero, cleanup,
никаких последующих protected операций. Использовать действующие steps/helpers; не делать
параллельную тестовую реализацию, выдающую готовый PASS. Реальные CI/registry/crypto не нужны.

## 5. Итоговая suite и документы — в том же исправлении

1. Принять correction устаревшей budget-fixture в активной рабочей копии, исторический файл
   оставить неизменным. Это не требует нового разрешения и не является source-блокером.
2. Полный launcher не должен снова выполнять upstream download под названием cached/offline.
   verify-pins.py всё ещё всегда вызывает HTTP; использовать проверенные bytes/evidence с
   явной offline проверкой целостности. Новый public verification не нужен для этого rework.
3. Старый `TestDigestPredicate.test_digest_mode_accepts_valid` принимает любой exit 0/1/2
   при отсутствии обязательного argument. Исправить active positive control: actual valid
   file → exact digest/exit0; invalid → nonzero. Это уже было в §5 review 8784116.
4. Runbook не должен утверждать enforced hard limits/freshness/typed complete routes,
   пока они опровергаются выше. Синхронизировать одну requirement→code→test→evidence matrix,
   включая все подпункты, а не только имена 34 tests. Manifest — весь runtime/test dependency
   closure, включая импортируемые historical fixtures и pinned inputs.
5. Source commit → один итоговый полный прогон → новый evidence commit; точные SHA,
   команды/cwd/UTC/exit/full output. Любой mandatory fail — nonzero. Не менять historical evidence.

## 6. Продолжение и конечный критерий

PRIMARY HERMES продолжает **тот же** single-pass task. Дополнительного «продолжай» для
source-работы не требуется. Не дробить A1/A2/A3/B на отдельные финальные STOP и не считать
новую сумму PASS заменой исполнению контракта. Промежуточные commits допустимы как PARTIAL.

Следующий итог — работающие целиком readiness и release/seed routes с позитивными и
отказными проверками одного production-кода, полной matrix и доказательствами, либо
конкретный непреодолимый внешний blocker после завершения независимой source-работы.
Перечисленные ошибки воспроизводятся offline и внешними blockers не являются.

Не переоткрывать C, application, PG17, candidate policies/107 policy tests, inventory9/9,
S1, 14-flow/offline design. Не выполнять SSH/live/cluster/Owner helpers, CI/private registry,
workflow publication/dispatch/token, реальные build/push/sign, NetworkPolicy apply,
production, backup/restore/PITR/failover. Execution gate не выдан.

```text
REVIEWED_SOURCE_SHA=a443b5caa56d7de18dd78a2ea407b5e76763f36d
REVIEWED_EVIDENCE_HEAD=52e2e38673671eb7a19dfbf0eeafd4209c4d72cb
EXISTING_FROZEN_SUITE=152/153 PASS (independently reproduced)
REVIEWER_BUDGET_FIXTURE=STALE; CORRECTION_CONFIRMED
EXISTING_SUITE_WITH_FIXTURE_CORRECTION=153/153 PASS
ADDITIONAL_EXISTING_CONTRACT=20 methods; 2 PASS; 18 failures; 0 errors
C_TEST_ISOLATION=CLOSED
SOURCE_TEST_EVIDENCE_ORDER=CONFIRMED
A_READINESS=PARTIAL
B_RELEASE_SEED=PARTIAL
SOURCE_PACKAGE=REWORK_REQUIRED
SOURCE_WORK=IN_PROGRESS/PARTIAL
EXECUTION_GATE_ISSUED=NO
CI_RELEASE / LIVE_READINESS / PRODUCTION=NOT_EXECUTED
NETPOL_APPROVED_FOR_APPLY=NO
P8C=NOT_FINAL_ACCEPTED
P8D–P8G/P9=NOT_AUTHORIZED
```
