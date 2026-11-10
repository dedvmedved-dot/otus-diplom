# P8C — review a5e58bd: завершить общий механизм исполнения R1–R4

Дата: 2026-11-10. Исполнитель — основной Hermes. Hermes2 не участвует.
Продолжение существующего задания `e196f0d57b228217f0c3a68d284dc99d4e004d26`;
нового execution gate нет.

**SOURCE_ACCEPTANCE=REWORK_REQUIRED; SOURCE_WORK=IN_PROGRESS/PARTIAL.**
Предыдущие семь воспроизведений закрыты. Полный R1–R4 контракт пока не выполнен.
Причина повторного возврата — исправлены показанные случаи, но не все пути одного
исполнителя; в R3 обязательное требование сознательно заменено совместимостью с fixture.
Ниже один консолидированный остаток, без новых функций или изменения scope.

## Проверка и принятая часть

Connector подтвердил два коммита после Architect review e196f0d:
- source `225004d12abe5ed2796c4bcd5e57c7ba945ded52`, UTC 2026-11-10T04:08:18Z;
- evidence/main `a5e58bd2567694e3c644c6a0dafead44ff9bb9f2`, UTC 04:10:42Z.
Авторский transcript начинается04:08:29Z: source→tests→evidence соблюдён.

Независимо выполнены все **214/214 активных test methods PASS**, qualification CLI exit0,
Python syntax и bash -n. В том числе все7 controls из прошлого review проходят.
Дополнительно: **12 методов, 2 PASS, 10 failed assertions, 0 errors**, exit1.
Два положительных контроля — healthy S0 и полностью bound seed attempt1 — проходят.

Окружение reviewer: Python3.12.14; автор:3.11.15. Source/dependency files сверены по
Git blob с деревом a5e58bd; manifest приложен. Каждый suite в отдельном процессе с частным
TMPDIR/authority; сетевой guard запрещает DNS/connect. Все transport/API/clock/tool outputs
synthetic. Весь shell launcher не повторялся: его214 методов и qualification CLI выполнены
отдельно; бинарного cache автора здесь нет, upstream pin downloads не выполнялись.
Авторские offline pin10/10 не выдаются за новый независимый upstream-прогон.

**Сохранить принятые fixes:**
- on-disk exhaustion теперь останавливает повторное I/O в прежнем воспроизведении;
- `run_read` ограничивает timeout локально известным остатком overall;
- partial HTTP до обычной read error теперь учитывается в overall;
- предыдущий late-final-sweep DNS case больше не даёт PASS;
- actual seed attempt2 отвергается, когда binding передан;
- protected build failure теперь доходит до always cleanup;
- положительные seed/release маршруты с настоящим `verified`, E pin binding, additive
  concurrency, exact GVR/identity/receipt, C isolation остаются принятыми в своём объёме.

Evidence: `evidence/P8/20261110-a5e58bd-architect-review/`.
Основные файлы: `reexecution.json`, `reexecution-raw.txt`, `remaining_execution_test.py`,
`additional-execution.json`, `additional-raw.txt`, `source-manifest.json`,
`syntax-execution.json`, `review-scan.json`, `network-summary.json`.
Команда дополнительных controls из корня repo:
`P8C_REVIEW_ROOT=$PWD python3 evidence/P8/20261110-a5e58bd-architect-review/remaining_execution_test.py -v`.

## R1 — timeout/partial должны охватывать все пути и все применимые бюджеты

| Проверка существующего контракта | Фактический результат на225004d | Требуемый результат |
|---|---|---|
| `run_wal_sample`: overall осталось1s | metadata transport получает5s | timeout≤1s |
| `run_wal_sample`: WAL осталось1s | metadata transport получает5s | timeout≤1s |
| current authority уже списал время, base процесса старее, осталось1s | `run_read` получает15s | остаток из актуального authority |
| HTTP read вернул64bytes после deadline | overall.bytes=0 | фактические64bytes учтены даже при отказе |
| WAL HTTP64bytes, затем read error | overall288, wal_bytes224 | WAL subset тоже288 (224metadata+64HTTP) |

Все пять строк воспроизводятся `Budgets.*` через настоящие wrapper/helpers с synthetic
transport. Последняя строка не требует успешных WAL-метрик: отказ тоже расходует бюджет.

**Почему это осталось:**
1. Изменён только `run_read`. В `run_wal_sample` metadata timeout всё ещё литерал5,
   HTTP timeout=`wal.REQ_TIMEOUT`; `_remaining_seconds()` туда не подключён. Отчёт и runbook
   утверждают больше, чем сделано. Проверять diff и реальные call arguments, не названия тестов.
2. `_authority_exhausted` читает authority для terminal boolean, но `_remaining_seconds/body`
   используют base+local. Между «ещё не исчерпан» и «сколько осталось» разные источники истины.
3. В `default_http_get` deadline проверяется после `read`, но ДО `total += len(buf)`.
   Уже полученный поздний chunk не попадает в consumption.
4. Error path helper вызывает только `_count_bytes`; `_count_wal_bytes` и sample-body учёт
   находятся после успешного возврата вызывающей функции. Partial/error WAL subset теряется.

Завершить общий permit/consume/terminal путь для metadata+HTTP, success+error+timeout:
- актуальный authority и все применимые sample/window/WAL/overall остатки до I/O/ожидания;
- транспортный deadline = минимум оставшихся временных ограничений; передача общего timeout
  сама по себе не заменяет absolute deadline во время чтения;
- полученный chunk списывается во все применимые счётчики до ветвления по результату;
- при ошибке/deadline/over-cap расход сохраняется ровно один раз, без double charge;
- exhaustion прекращает чтения, concurrency ADD/last-slot protection не откатывается.

Не ограничиваться пятью примерами: в прежнем review явно требовались также hard deadline
внутри blocking HTTP read, ограничения sample/window, terminal stop при любой ошибке.
`default_http_get` пока использует первоначальный socket timeout для последующих read,
а deadline лишь проверяет после возврата; остаток всего контракта нужно проверить целиком.
Не превращать ограничение в фиксацию уже состоявшегося перерасхода.

## R2 — поздний retry также не может закрывать окно

Предыдущий case исправлен только в final sweep при `cur==INCONCLUSIVE`.
Новый вариант того же W30/I5/N6 контракта через реальный main:
- DNS первые observations:300,305,310,315 — INCONCLUSIVE;
- retry начинает GET на320 с timeout15; ответ healthy приходит331;
- первый успешный ответ уже за пределом окна300..330;
- journal принимает PASS; final sweep331 видит `cur==PASS` и обходит expiry guard;
- aggregate=PASS, exit0.

`HealthWindow.test_retry_response_after_dns_deadline_not_pass` воспроизводит нарушение.
`test_positive_s0` остаётся PASS. Это не требование запретить legitimate fresh recheck уже
валидированного check: этот check НИ РАЗУ не проходил внутри разрешённого окна.

У каждого check должен быть один absolute window и valid observation history. Проверять
время ДО sleep, после sleep, перед GET и при завершении GET; передавать остаток окна
транспорту. Retry, initial GET и final sweep не должны иметь разные правила валидности.
Позднее значение не становится «previous PASS», разрешающим обойти окно.
Сохранить N6/N12, интервалы, failure precedence, shared DB/ARCH и freshness30/60.

## R3 — отсутствие binding НЕ является совместимостью

Предыдущее задание требовало буквально: «проверить actual attempt, требуемое поле документа
и их связь; отсутствие binding — отказ». В225004d оба поля проверяются только when-present.

Реальный CLI `first-creation` возвращает exit0/VERIFIED для всех трёх случаев:
- отсутствует `GITHUB_RUN_ATTEMPT`, gate.attempt=1;
- отсутствует gate.attempt, runtime attempt1;
- gate.attempt=null, runtime attempt1.

`SeedBinding.*`: три negative FAIL, bound attempt1 positive PASS.
Отказ actual attempt2 принят, но single-attempt gate целиком не закрыт.

Сделать оба binding обязательными и типизированными: actual runtime attempt1 и целочисленный
(non-bool) gate.attempt1, согласованные с source/repository/workflow. Missing/null/неверный тип/
attempt2 → nonzero до build/push. Не сохранять разрешительный bypass ради старого positive test.

Если исторический positive fixture не содержит поля, он уже не представляет корректный
положительный допуск. Исторический файл сохранить; активную рабочую копию/fixture привести
к полному valid gate+runtime, оставить positive/negative assertions, в launcher и matrix
объяснить замену. Это допустимая синхронизация тестового входа, а не ослабление source-контракта.
Никаких skip/xfail либо подмены validator PASS.

## R4 — cleanup исполняется, но его ошибка теряется; полнота negative routes

Закрыт прежний дефект: failed build действительно пропускает protected steps и доходит до
always cleanup. Это сохранить.

Но `_run_job_steps` добавляет nonzero в failures ТОЛЬКО при `not is_always`.
`CleanupOutcome.test_cleanup_nonzero_cannot_report_route_pass`:
- полный release positive route исполняется с прежними fake external tools;
- на границе cleanup-step инжектирован process result exit42;
- trace содержит Cleanup exit42, но failures=[]: caller объявляет маршрут успешным.

Это проверка runner на synthetic process failure, **не заявление**, что production cleanup
сейчас возвращает42 или GitHub Actions проигнорирует always. Условия запуска шага и учёт
его результата — разные вещи. Always определяет исполнение после отказа, а не разрешение
игнорировать его returncode. Учитывать любой обязательный nonzero в итоговом verdict,
продолжая остальные положенные always-шаги; assertions делать после cleanup.

Полнота §6 прошлого review также ещё не предъявлена: в активном route suite осталось5методов,
REUSE/STOP по-прежнему вызывает один precheck и проверяет структуру, а не полный routing;
инъекций readiness/build/proof ошибок для ОБОИХ маршрутов нет. Завершить ту же матрицу
общим runner: positive; REUSE/STOP→0build/push; readiness/build/proof failure→nonzero,
no subsequent protected operations, always cleanup с проверенным outcome. Реальные validators
оставить; внешние бинарники/private/registry boundary допускается подменять.

## Одно задание основному Hermes — завершить остаток прежнего контракта

Продолжать автономно без нового «продолжай». Не дробить исправления на очередные пакеты
«все controls PASS → COMPLETE» до проверки остальных путей того же исполнителя.
Принятые части сохранить. Нового продукта, функций или ограничений здесь нет.

1. Завершить R1 единым механизмом ограничения и списания для всех транспортов/исходов.
2. Завершить R2 единым правилом валидности наблюдения внутри окна на всех путях main.
3. Закрыть R3 строго по обязательному binding, синхронизировав активные positive fixtures.
4. Довести R4 полную negative routing matrix, учитывая outcome cleanup.
5. Обновить runbook/matrix по фактическому коду. Проверить production entrypoints и traces
   по всему R1–R4 контракту, не только12 controls. Непройденное source-требование не относить
   к CI_ONLY/live prerequisites.

Итог: final source commit → единый offline launcher exit0 → отдельный новый evidence commit,
полный dependency manifest (path/blob/SHA256), requirement→code→test→evidence, команды/cwd/UTC/
exit и границы synthetic/real. Fast-forward, без force/rebase/amend. Историческое evidence
не менять. Промежуточные commits PARTIAL допустимы; итоговый STOP — завершённый пакет либо
конкретный непреодолимый внешний blocker после всей независимой работы.

App/PG17/policy107/inventory9/9/S1/14-flow/backups и закрытый E не переоткрывать. Hermes2
не задействовать. Live/SSH/кластер/CI/private registry/реальные build-push-sign/workflow
publication-dispatch-token/Owner helpers/NetworkPolicy apply/production не разрешены.

```text
REVIEWED_SOURCE_SHA=225004d12abe5ed2796c4bcd5e57c7ba945ded52
REVIEWED_EVIDENCE_HEAD=a5e58bd2567694e3c644c6a0dafead44ff9bb9f2
ACTIVE_TEST_METHODS=214/214 PASS
PREVIOUS_7_CONTROLS=7/7 PASS
ADDITIONAL_EXISTING_CONTRACT=12 methods; 2 PASS; 10 failed assertions; 0 errors; exit1
SOURCE_ACCEPTANCE=REWORK_REQUIRED
SOURCE_WORK=IN_PROGRESS/PARTIAL
EXECUTION_GATE_ISSUED=NO
CI_RELEASE / LIVE_READINESS / PRODUCTION=NOT_EXECUTED
NETPOL_APPROVED_FOR_APPLY=NO
P8C=NOT_FINAL_ACCEPTED
P8D–P8G/P9=NOT_AUTHORIZED
```
