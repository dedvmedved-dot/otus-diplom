# P8C R5 review c8007f5 — 104 regressions PASS, full source contract still PARTIAL

Дата: 2026-11-05, Europe/Moscow. Адресат: ОСНОВНОЙ HERMES. Hermes2 не участвует.
Это продолжение review efc6929 и completion task 940c4e7, без нового scope или live gate.

## 1. Проверенная база и результаты

Connector main: c8007f51614ca31df7d532a191327e4eac2ba737.
Source/parent: 783502a7eff2662d6f7612ccc56c4a9251e16ace.
Source parent: efc69293ed0745777a1cb218599fe7124ced5f9a.
Diff: wrapper.py, wal.py, test_readiness.py и четыре новых evidence-файла.
Release/seed templates, release-check.py, readset, runbook и gate drafts не менялись.
22 локальных файла сверены по точным blob bytes с текущим Git tree через Connector.

Независимо воспроизведены все заявленные **104 methods PASS**:
23 readiness + 3 qualification + 4 release + 7 negative + 28 previous regression +
25 residual + 14 R4 scheduler regression. Qualification CLI: qualified:true.

Новая проверка прежнего полного контракта: **15 methods, 16 failures/subtests, 0 errors**.
Один положительный control проходит шесть стадий S0→S4 через настоящий main, реальные
predicates/WAL и подставные transport/time. Это подтверждает достижимость happy path;
это НЕ приёмка freshness, action receipts, budgets и failure/replay branches.
Три отрицательных first-creation входа — subtests одного метода, поэтому failures больше methods.

Evidence: evidence/P8/20261105-c8007f5-architect-review/:
- contract_test.py, contract-execution.json;
- reexecution.json (104 methods + qualification CLI);
- source-audit.json, review-scan.json.

Только offline. Нет SSH/cluster/CI/private registry/OCI build/push. Public pin downloads
не повторялись; 10/10 остаётся предъявленным ранее авторским результатом. Принятые
application/PG17/107 policy tests/inventory9/9/backup/PITR/failover не перезапускались.

## 2. Что исправлено — сохранить

- run_wal_window действительно подключён к main; первый валидный baseline теперь сохраняется;
- успешные реальные transport-вызовы и bytes учитываются, а не только logical read IDs;
- malformed JSON budget и уже исчерпанный бюджет останавливают запуск на проверенном входе;
- inflight/completed marker блокирует повтор; последний metadata response после 30s не даёт PASS;
- PR-3/DNS same-slice cases, обязательная Gateway generation и bpfEnabled drift исправлены.

Но прошлые 14 controls проверяли конкретные воспроизведения. В частности, их replay
case теперь идёт после успешного S0; он не проверяет исчерпанное неуспешное окно.
Ни 14/14, ни сумма 104 не означают закрытия R4-01…05 целиком. Требование полного
positive/negative execution contract уже содержалось в review efc6929 §§2–7.

## 3. Незакрытые прежние блоки — единое задание на завершение

### R4-01: окно, freshness, baseline/action boundary

1. `sleep(300)` выполняется ПОСЛЕ предыдущего sample. При sample duration=10s начала
   равны 0/310/620, а не нормативным 0/300/600. Планировать по абсолютному window-start
   и оставшемуся времени; enforce 660s/window и sample/request bounds в том же executor.
2. HC по-прежнему читаются один раз перед WAL. В успешном S0 HC-OP имеет возраст **300s**
   при выдаче PASS, а нормативное ограничение 30s. W/I/N не исполняются, DB и ARCH делают
   два одинаковых GET вместо одного общего. Встроить принятые HC окна/freshness в общий
   scheduler и budgets; не добавлять неограниченный final sweep.
3. Новое `grown+fresh → PASS` без op_end применяется на ЛЮБОЙ стадии, не только S0.
   S1 проходит без operation_end_utc/action receipt. Для S0 также не используется
   first-sample-end: счётчик растёт, но оба archive timestamps ДО начала окна → PASS.
   Восстановить нормативные boundaries: S0 first valid sample end; post-op — связанный
   operation receipt, строгий `last_archived_time > boundary+5` и upper skew bound.
4. run_wal_window сохраняет ЛЮБОЙ non-None `m`, включая FAIL/malformed/missing/reset.
   При failed_count growth FAIL sample заменяет валидный baseline. Хранить failure
   evidence отдельно; baseline только из явно валидного наблюдения с identity/time,
   без стирания исходной failure comparison. При reset/role/restart — INCONCLUSIVE по дизайну.

Тесты: slot_offsets_include_elapsed_sample_time; shared_db_arch_metadata;
success_receipt_requires_fresh_operator_observation; s0_progress_must_be_after_first_sample_end;
post_operation_stage_requires_its_action_boundary; first_slot_failure_metrics_do_not_replace_valid_baseline.
Полные имена находятся в contract_test.py.

### R4-02: одноразовость допуска и расход всех ресурсов

1. После idle-окна из 3 samples main пишет clean_failed. Следующий CLI invocation
   принимает его и выполняет НОВЫЕ 3 samples (ещё 29 запросов). Attempts считает
   CLI invocations, а run_wal_window каждый раз начинает range(3) с нуля. Получается
   до 9 samples по одному stage, а не максимум 3. Тот же обход работает с новым state-dir.
   Чистый non-PASS не выдаёт новый допуск. Slots принадлежат одному разрешённому
   окну; exhausted/completed/UNKNOWN_OUTCOME терминальны согласно предыдущему review.
2. budget_path(gate) объявлен, но main его НЕ использует: по-прежнему читает/пишет
   --state-dir/budget.json. Смена state-dir теряет расход; запись после всего readset
   теряет его при crash. Atomic charge/reservation должен жить в единой gate/run/package
   authority, под блокировкой; повтор/конкуренция/corrupt state не обнуляют счётчики.
3. _count_transport вызывается лишь ПОСЛЕ успешного возврата. В reproduction 9 попыток
   с transport failure дают requests=0. Учитывать попытку перед I/O, реальные bytes
   по мере чтения и elapsed на всех исходах; reserve/check remaining до следующего запроса.
4. Проверка budget_exhausted только перед readset: нет enforcement в ходе window,
   нет отдельных WAL/HC/PR/global counters. Один общий счётчик сравнивается с WAL cap
   90/36MiB/3960s, хотя общий принятый cap — 233/179MiB/5265s. Разделить по принятому
   контракту, не менять численные пределы. Не просто заменить 90 на 233.
5. Числовые значения budget не валидируются: отрицательные requests/bytes/seconds
   принимаются; после S0 остаются отрицательными и aggregate=PASS. Проверять полную
   типизированную схему, finite/nonnegative bounds и provenance; invalid → STOP до I/O.
6. Сохраняются прежние требования: atomic concurrency; gate identity отличается от
   package identity; baseline/receipt/action state связан с конкретным допуском и стадией,
   а не только с формально похожим JSON в пользовательском каталоге.

Тесты: clean_failed_window_cannot_restart_three_more_samples;
new_state_directory_after_nonpass_cannot_start_fresh_window;
failed_request_attempts_are_charged; negative_budget_not_accepted.
Добавить в полную suite crash/parallel/per-request cap crossings, включая неуспешные ответы.

### R4-03: hard deadline пока не завершён

Post-return проверка теперь отвергает последний response за 30s — это принято.
Но она не прерывает зависший/медленный HTTP body: default_http_get всё ещё urllib
socket timeout + read(cap+1), без absolute monotonic transport deadline. В raw остаётся
hard_deadline=now+timeout+5; WAL metadata timeout=5 получает ещё 5 секунд. Оставшийся
sample/window budget не передаётся в transport. Полный R4-03 по-прежнему source-work.

Исполнить прежний контракт deadline/cap во время чтения и cleanup, с transport-level
accounting на error. Проверить controlled fake/local slow-body/EOF/timeout, без cluster.
Не переоткрывать уже принятые no-proxy/no-redirect и исправленный final-response case.

### R4-04: весь исходный остаток, включая release/seed

Readiness requirements не сводятся к четырём исправленным predicate cases:
- exact per-read kind/apiVersion/scope/max_items не подключены. Реальный PR-3 route
  принимает PodList/v1 с EndpointSlice-подобными полями и выдаёт PASS;
- PR-5 принимает отсутствие metadata/UID/ownership и loadBalancer.ingress=[{}] как PASS;
- новый Felix loop допускает отсутствие nftablesMode (spec={}) как PASS;
- typed Namespace/Pod selector context и полный принятый PR-6 projection не заменяются
  общим API allowlist или пропуском частей baseline. Не выводить effective union из отсутствующих данных.

Seed/release files не изменены с предыдущего review, поэтому эти пункты НЕ CLOSED:
- first-creation проверяет regex SHA/date и expiry_hours range, но не время, режим и
  реальную binding. CLI принимает **2000-01-01**, **2099-01-01** и **TEST_ONLY** → VERIFIED;
- template ждёт RUNNER_TEMP/first-creation-gate.json, но исполнимой source-bound доставки
  будущего gate в job нет; private failure distinctions и fake-tool CREATE_ALLOWED E2E не готовы;
- source-bound unique seed tag, failure/cancellation cleanup, exact registry-byte postproof
  и enforced seed≠app assertion по-прежнему отсутствуют в полном исполнимом маршруте;
- release protected operations не связаны с future gate/source/package/workflow/expiry/
  run-attempt contract. Fake-tool negative/positive paths обязательны до CI-допуска.

Тесты: pr3_wrong_resource_kind_rejected_on_actual_read_path; pr5_requires_service_identity;
pr6_missing_expected_nftables_mode_rejected; first_creation_does_not_accept_expired_future_test_only_gate.
Этот последний тест не выполняет build/push и не требует Owner/private registry.

Исчерпывающая прежняя authority: review efc6929 §5 → review 2ff8b58 §3 и original
completion task 940c4e7 §5. Закрыть их целиком, а не только имена тестов этой suite.
Runtime crypto/private registry/runner facts остаются CI_ONLY; исполнимый source не CI_ONLY.

### R4-05: отчёт, traceability и source-bound evidence

R5 raw-transcript.txt снова начинается SOURCE_SHA=efc69293... — parent Architect review,
а result.md называет 783502a7... и «source SHA-bound». По опубликованным данным suite
завершилась 17:59:17Z, source commit создан 17:59:23Z. Это не требуемый порядок
source commit → tests → отдельный evidence commit. Наш независимый повтор на точных
bytes подтверждает 104 PASS, но не исправляет происхождение авторского transcript.

R4 raw/result contradiction также требует отдельного correction record. Исторические
evidence не переписывать. После окончания source зафиксировать окончательный SHA,
выполнить проверки именно его bytes и сохранить полные argv/cwd/UTC/version/exit/output.

Runbook/drafts/matrix в R5 не изменялись: по-прежнему старые 20 PASS, atomic_reserve,
«non-PASS releases reservation», неполное покрытие R-01…08. Обновить на итоговую реализацию,
полный runtime manifest и все imported helpers. Результат теста не считать выполнением
требования, если тест подменяет проверяемый executor/predicate или не проходит failure route.

## 4. Как завершить текущую работу без нового цикла разрешений

Не выдавать очередной частичный пакет за final STOP. До следующего итогового отчёта:
1. Свести R4-01…05 и прежний release/readiness contract в одну checklist; оставить
   честный PARTIAL по незавершённым строкам. Сохранить подтверждённые исправления.
2. Завершить production routes state/scheduler/transport/predicates/release/seed;
   затем прогнать один полный offline positive+negative E2E на final source.
3. Проверить 6 стадий и failure/replay/clock/budget/freshness/action receipts, seed
   REUSE/STOP/CREATE_ALLOWED/failure cleanup, release gate/artifact bindings.
4. Синхронизировать runbook/drafts/matrix/manifest, source-SHA и raw outputs; отдельный
   новый evidence commit. Исторические материалы остаются byte-identical.

Нового «продолжай» для этой source-работы не требуется. Intermediate commits разрешены;
итоговый STOP — полный §5 либо конкретный внешний blocker после всей независимой работы.
Live clock evidence и фактический CI execution остаются внешними фактами, а не причиной
пропускать указанные offline branches. Новый live E2E сейчас не нужен и НЕ разрешён.

Не менять accepted app/PG17/candidate YAML/6-policy contract/107 tests/collector9/9/S1/
14-flow/offline design. Не выполнять SSH/live reads/registry-private/OCI build/push/CI,
workflow publication/dispatch/token, Owner helpers, NetPol apply, production или
backup/restore/PITR/failover. Hermes2 не участвует. Fast-forward, без force.

```text
REVIEWED_SOURCE_SHA=783502a7eff2662d6f7612ccc56c4a9251e16ace
REVIEWED_EVIDENCE_HEAD=c8007f51614ca31df7d532a191327e4eac2ba737
PREVIOUS_SUITES=PASS (104 methods independently reproduced)
CURRENT_CONTRACT_SUITE=15 methods / 16 failed assertions-subtests / 0 errors
POSITIVE_S0_S4_CONTROL=PASS (mock transport/virtual clock; not full acceptance)
SOURCE_PACKAGE=REWORK_REQUIRED
SOURCE_WORK=IN_PROGRESS/PARTIAL
EXECUTION_GATE_ISSUED=NO
CI_RELEASE / WORKFLOW_PUBLICATION_DISPATCH / LIVE_READINESS=NOT_AUTHORIZED
NETPOL_APPROVED_FOR_APPLY=NO
OWNER_HELPERS / PRODUCTION_MIGRATION_DEPLOYMENT=NOT_EXECUTED
P8C=NOT_FINAL_ACCEPTED
P8D–P8G/P9=NOT_AUTHORIZED
```
