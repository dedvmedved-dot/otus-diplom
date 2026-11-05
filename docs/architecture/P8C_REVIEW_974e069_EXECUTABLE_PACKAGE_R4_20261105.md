# P8C R4 review 974e069 — scheduler not connected; source package REWORK_REQUIRED

Дата: 2026-11-05, Europe/Moscow. Адресат: ОСНОВНОЙ HERMES; Hermes2 не участвует.
SOURCE_WORK=IN_PROGRESS/PARTIAL. Это продолжение текущего задания, не новый scope и не execution gate.

## 1. Проверенная база и независимые результаты

Connector main: 974e069f6bb7c418c7d9683d75cfd80bfa3fba87.
Source/parent: 317ebc7ab1839f7dac5a22690b24aabafcc98283.
От checkpoint 9a05014 изменены только wrapper.py, wal.py и четыре новых evidence-файла.
Тесты readiness, release/seed templates и runbook в этом R4 не изменены.
25 локальных файлов сверены по точным Git blob bytes с деревом reviewed head.

Независимо воспроизведены readiness 23 + qualification 3 + release 4 + negative 7 +
previous regression 28 + residual 25 = **90 methods PASS**; qualification CLI qualified:true.
Этот результат подтверждает исправление ранее воспроизведённых случаев, но не полный
source-контракт. Прежние suites не проверяли новый scheduler end-to-end.

Новая адресная suite scheduler_regression_test.py: **14 методов, 13 failures, 0 errors**.
Положительный контроль с заранее поданным baseline проходит; остальные проверки
воспроизводят незавершённые production routes. Main, predicates и wal_sample реальные;
подменены только kubectl/HTTP transports и часы, ответы SYNTHETIC. Ни одного live-запроса.
Это адресная suite, а не замена обязательному полному S0→S4 E2E от Hermes.

Evidence: evidence/P8/20261105-974e069-architect-review/:
- scheduler_regression_test.py, scheduler-execution.json;
- reexecution.json (90 методов + qualification CLI);
- source-audit.json, review-scan.json.

Public pin downloads/registry/CI/SSH/cluster/app/PG17/107 policy tests/inventory9/9/
backup/restore/PITR/failover не повторялись. 10/10 public pins остаётся авторским ранее
предъявленным результатом; нового независимого upstream download в этом review нет.

## 2. R4-01 — исполняемый scheduler и baseline, не отдельный класс

`wal.Scheduler` добавлен, но нигде в wrapper.main не создаётся и не вызывается.
main по-прежнему один раз обходит readset и один раз вызывает run_wal_sample.
Нет ожидания слотов 0/300/600, шести bounded окон, перехода между slots/windows,
HC W/I/N/freshness или совместного GET для HC-DB/HC-ARCH-STATE.
В самом Scheduler `windows` не меняется; advance_slot на последнем слоте возвращает
False, но can_sample остаётся True. Наличие констант и методов не является исполнением.

Первый корректный sample возвращает INCONCLUSIVE с metrics и detail «baseline sample
recorded». main сохраняет metrics только при PASS. Поэтому S0 не получает собственного
baseline; повтор снова начинает без baseline. С заранее поданным gate.wal_baseline
контроль проходит, но это не доказывает самостоятельный positive route S0.

Требуется в рамках прежнего дизайна:
- один разрешённый запуск окна управляет своими slots; S0 first valid sample сохраняет
  baseline/identity/sample-end без ложного progress PASS; следующий slot сравнивает с ним;
- stages S0/S1/S2a/S2b/S3/S4, operation boundary и baseline передаются через связанные
  observation/action receipts; caller-счётчик или произвольные metrics не заменяют provenance;
- реальные W/I/N и freshness для HC, без неучтённого финального sweep; health degradation
  не перезаписывает baseline так, чтобы скрыть failure growth;
- inject virtual monotonic clock/wait в тот же executor, который вызывает main.

Acceptance: успешный offline S0→S4 без заранее готового WAL baseline, slots с реальным
виртуальным временем, baseline/receipts и точным transport journal; idle/reset/role-change/
failure/expiry — отдельные отрицательные маршруты. Live E2E сейчас НЕ требуется.
Адресные тесты: test_s0_collects_own_baseline_then_progress_in_one_window,
test_first_valid_baseline_is_preserved_without_claiming_progress.

## 3. R4-02 — request/byte/time accounting и единая crash-safe authority

Наблюдение на реальном main с fake transports: S0 выполняет **19 запросов**, но
journal.budget.requests=**7**, bytes=**0**. PR-6 (9 GET) и WAL (5 запросов) считаются как
один logical check каждый. run_read отбрасывает bytes/status; failed requests не имеют
полного duration/charge. budget_exceeded не вызывается. Даже при уже исчерпанных
233 req / 179 MiB / 5265s main выполняет следующие 19 запросов.

budget.json находится в пользовательском --state-dir, не рядом со стабильной authority.
Новый state-dir обнуляет бюджет; malformed budget JSON также тихо превращается в нули.
Сохранение идёт после всего readset — crash до записи теряет расход.

window-state ограничивает число CLI-вызовов до 3, но не является slot scheduler:
- второй запуск сразу при тех же часах вновь выполняет 19 запросов;
- marker после open_window без завершения (crash/in-flight) разрешает другой процесс;
- retry read-modify-write без блокировки может одновременно допустить два процесса;
- attempts не содержит времени начала/номера нормативного слота/дедлайна/owner-run;
- package identity не заменяет identity конкретного допуска; receipt reader не проверяет
  записанный issued_at, а clock gate_sha256 сравнивается с package hash.

Исправить единым state model, а не ещё одним несвязанным файлом:
- gate/run/source/package/stage-bound authority, блокировка конкуренции и одноразовый
  расход допуска; samples внутри одного окна не равны повторному CLI запуску;
- crash/UNKNOWN_OUTCOME не создаёт право на retry; ослабление one-run не разрешено;
- реальный charge каждого запроса/байта/времени в transport, до следующего запроса;
  все уровни принятых лимитов (sample/window/WAL/HC/PR/global), включая timeout/error;
- устойчивое сохранение расхода, отсутствие reset при смене out/state-dir, corrupt state
  → STOP; reserve перед I/O, не только post-factum суммирование;
- отдельное хранение неуспешного outcome без advancement/подмены completed receipt.

Принятые пределы не расширять: WAL 90 req/36 MiB/3960s; общий контракт 233 req/
179 MiB/5265s; окно 15 req/6 MiB/660s, sample 5 req/2 MiB/30s.
Адресные тесты: budget_counts_requests_and_bytes, exhausted_budget, corrupt_budget,
same_clock_new_invocation, crash_inflight_marker, new_state_directory (полные имена в suite).
Добавить deterministic concurrent/reservation/crash-before-and-after-charge тесты и
проверку израсходованного gate, не удаляя исторические evidence и не расширяя допуск.

## 4. R4-03 — hard deadline во время transport

raw проверяет 30s ДО запроса; HTTP — до/после. После последнего Cluster GET deadline
вообще не проверяется. Reproduction: перед последним GET elapsed=29, после него=31,
run_wal_sample возвращает **PASS**. Значит утверждение «после каждого из 5 запросов»
не соответствует коду. Остаток sample/window/gate deadline не передаётся в transport.

default_http_get использует urllib timeout и read(cap+1); timeout ожидания socket bytes
не является абсолютным сроком чтения медленного тела. Проверка после возврата не
прерывает этот запрос. Сохранить no redirect/proxy, добавить реальный monotonic hard
deadline и bounded read/cleanup, передав min(request, remaining sample/window/gate).
Прерывание и расход времени/байтов должны доходить до общей authority.

Acceptance: final-response-over-deadline, slow body/header, elapsed при parsing,
timeout/partial body и cleanup с fake/local controlled transports, без cluster calls.
Адресный тест: test_last_response_cannot_cross_sample_deadline_and_pass.

## 5. R4-04 — прежний R2-контракт не сужается до checkpoint scheduler

Сохранить исправления, подтверждённые 90 PASS. Но следующие прежние требования не
закрыты, хотя aggregate «R2-01…08 CLOSED» уже заявлялся:

Readiness (R2-02):
- validate_envelope использует общую allowed API таблицу и kind.endswith('List'), а не
  exact per-read GVR/kind/scope/item bound; readset max_items не применён;
- PR-6 сравнивает только nftablesMode/name Felix; bpfEnabled=True остаётся PASS;
  Namespace/Pod части baseline не участвуют в сравнении;
- HC-GW при отсутствующих generation на обеих сторонах даёт PASS;
- PR-3 и HC-DNS собирают ports и endpoints разных EndpointSlice в общий результат:
  порт на пустом slice признаётся портом ready endpoint другого slice;
- PR-5 ещё принимает Service без проверенной ownership/UID/selector identity и с
  произвольным непустым ingress; прежняя exact identity/tuple проверка обязательна.
Четыре первых конкретных ложных PASS закреплены в ExistingReadContract.

Release/seed (R2-01/R2-06): templates byte-identical с review 2ff8b58. Добавление mode
first-creation в helper полезно, но не закрывает исполнимую доставку/валидацию future
gate: seed всё ещё ожидает заранее существующий RUNNER_TEMP/first-creation-gate.json.
Нет полного fake-tool CREATE_ALLOWED маршрута и typed failure distinctions.
Seed tag bootstrap-seed не source-bound unique; cleanup после build пропускается при
set -e failure/readiness failure; seed≠app записывается boolean сравнением с потенциально
пустым APP_IMAGE_DIGEST, не enforced assertion; exact registry-byte postproof не включён.
Release template по-прежнему без future gate/package/source/workflow/expiry/run-attempt
validation перед protected operations. Доставка gate сейчас проектируется в исходниках;
реального gate/workflow/Owner-действия для её offline проверки НЕ требуется.

Не переносить эти source-остатки в CI_ONLY. Реальная crypto/runner/private registry
проверка — CI_ONLY, но исполнимые команды, связи и cleanup/failure branches — source.
Полный прежний контракт: docs/architecture/P8C_REVIEW_64e36a6_EXECUTABLE_PACKAGE_R2_20261105.md
§3 и docs/architecture/P8C_EXECUTABLE_PACKAGE_COMPLETION_TASK_20261104.md §5.

## 6. R4-05 — исправить текущий отчёт новым evidence, не историческую запись

Опубликованный raw-transcript.txt R4 начинается SOURCE_SHA=9a050145... (checkpoint,
не final source 317ebc7...) и содержит `FAILED (failures=1)` у residual suite.
result.md одновременно утверждает 90 PASS. Наш независимый изолированный повтор
90 PASS не исправляет происхождение/результат того исторического запуска.
Установить причину расхождения и добавить correction record; не заменять прошлый файл.

Runbook всё ещё говорит «non-PASS releases reservation», ссылается на atomic_reserve и
20 PASS; его matrix состоит из шести укрупнённых строк и не отражает новый window-state
или все R-01…08. Синхронизировать после завершения executor, не объявлять старую матрицу полной.

Финальный пакет должен содержать:
1. полный requirement→production route→positive/negative test→evidence по текущему task;
2. offline readiness S0→S4 через реальные entrypoints, mock transports + virtual clock;
3. release/seed production-step fake-tool routes, включая success/REUSE/STOP/failure cleanup;
4. source commit ПЕРЕД прогонами, полный argv/cwd/UTC/версии/exit/stdout/stderr каждой suite;
5. runtime manifest со всеми зависимостями и full hashes; актуальные runbook/gate drafts;
6. новое evidence отдельно, frozen input scan с output вне входного набора, различать
   scanner ERROR / no-match / match. Исторические evidence остаются byte-identical.

Перед публикацией машинно сверить статусы suite и source SHA в raw output/result/manifest.
Нельзя объявлять PASS по tail вывода или при сохранённом FAILED. 14 новых controls — минимум
воспроизведения, не новая замена полному positive E2E и требованиям предыдущего review.

## 7. Действие Hermes и границы

Продолжить текущее completion task без запроса нового «продолжай». Промежуточные commits
допустимы, статус PARTIAL; не останавливать независимую source-работу ради review каждого
checkpoint. Следующий итоговый STOP — после полного §5 либо конкретного внешнего blocker,
когда вся независимая работа завершена. Реальное clock evidence и CI runtime остаются
неисполненными внешними фактами; они не мешают закончить описанные offline routes.

Не переоткрывать принятые candidate YAML/контракт 6 политик/107 policy tests, app/PG17,
collector/inventory9/9/S1, 14-flow/offline design. Не выполнять новые live reads/SSH,
private registry/build/push/CI, workflow publication/dispatch/token, Owner helpers,
NetworkPolicy apply, production migrations/deployment, backup/restore/PITR/failover.
Hermes2 не нужен. Публикация source/evidence fast-forward, без force, только в разрешённой области.

```text
REVIEWED_SOURCE_SHA=317ebc7ab1839f7dac5a22690b24aabafcc98283
REVIEWED_EVIDENCE_HEAD=974e069f6bb7c418c7d9683d75cfd80bfa3fba87
PREVIOUS_OFFLINE_SUITES=PASS (90 methods, independently reproduced)
R4_CONTRACT_CONTROLS=14 methods / 13 failures / 0 errors
SOURCE_PACKAGE=REWORK_REQUIRED
SOURCE_WORK=IN_PROGRESS/PARTIAL
EXECUTION_GATE_ISSUED=NO
CI_RELEASE / WORKFLOW_PUBLICATION_DISPATCH / LIVE_READINESS=NOT_AUTHORIZED
NETPOL_APPROVED_FOR_APPLY=NO
OWNER_HELPERS / PRODUCTION_MIGRATION_DEPLOYMENT=NOT_EXECUTED
P8C=NOT_FINAL_ACCEPTED
P8D–P8G/P9=NOT_AUTHORIZED
```
