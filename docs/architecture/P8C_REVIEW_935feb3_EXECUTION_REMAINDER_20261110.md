# P8C — review 935feb3: положительные маршруты приняты, остаток исполнения R1–R4

Дата: 2026-11-10. Исполнитель — основной Hermes, без Hermes2.
Продолжение существующего source-задания и review
`2a38af9f8caa84268a41158efc8459e564b83fad`. Нового execution gate нет.

**SOURCE_PACKAGE=REWORK_REQUIRED; SOURCE_WORK=IN_PROGRESS/PARTIAL.**
Это не переоткрытие всего пакета. Ниже отдельно зафиксированы принятые исправления и
конкретный остаток прежнего контракта, воспроизводимый без live/CI.

## 1. Независимая проверка

Connector подтвердил fast-forward:
`2a38af9f8caa84268a41158efc8459e564b83fad` →
`3422e31e97742dd32ad5044451eb062ee5dacf1d` (source) →
`935feb3de24116d52fd8c4da7ac963242a82fc07` (evidence/main).
Source commit: 2026-11-10T03:27:33Z; авторский transcript начинается03:27:52Z;
evidence commit03:30:10Z. Порядок source→tests→evidence подтверждён.
Название нового evidence-каталога содержит 20261111, но фактические UTC — 10 ноября;
это метка каталога, не основание менять историческое evidence.

Независимый прогон exact Connector blobs:
- **207/207 test methods PASS**, qualification CLI exit0.
- Все прежние 12 controls — PASS. В том числе учёт переданного elapsed, нужные количества
  health-наблюдений, release actual-attempt/workflow/future checks и image cache binding.
- Число206 в отчёте неточно: route E2E теперь5, а не4; и авторский raw-transcript содержит
  `Ran 5 tests`. Это неблокирующая поправка к подсчёту, не дефект source.
- Положительные route traces подтверждены: seed8 shell steps и release15 shell steps,
  все exit0; настоящий `verified` выдал digest-bound PASS. Это **synthetic offline proof**,
  не выполненный build/registry/crypto в CI.
- Дополнительные controls прежнего контракта: **7 методов / 1 PASS / 6 failed assertions /
  0 errors**, exit1. Положительный S0 контроль проходит.

Python reviewer3.12.14; автор3.11.15. Сетевой guard запрещал DNS/connect в тестовых процессах.
Transport/clock/API/registry/tool outputs synthetic. SSH, кластер, CI, private registry,
реальные build/push/sign не выполнялись. Бинарного cached pin набора автора здесь нет:
весь shell launcher повторно не запускался, все его207 методов и qualification CLI выполнены
отдельно; upstream pins не скачивались. Python syntax / bash -n проверены отдельно.

Evidence: `evidence/P8/20261110-935feb3-architect-review/`:
`reexecution.json`, `reexecution-raw.txt`, `final_contract_test.py`, `final-contract.txt`,
`additional-execution.json`, `audit_routes.py`, `route-audit.json`, `source-manifest.json`,
`syntax-execution.json`, `review-scan.json`, `network-summary.json`.
Повтор controls из repo root: `P8C_REVIEW_ROOT=$PWD python3 <evidence-path>/final_contract_test.py -v`.

## 2. Принятые изменения — сохранить

- Atomic request ADD/last-slot protection, durable запись фактически переданного расхода,
  учёт успешного I/O elapsed, min(sample/WAL/overall) body caps — адресные fixes приняты.
- Namespace cluster scope, GVR, value-free diagnostics, action receipt bindings, failure
  precedence, health N6/N12 и per-check freshness — не откатывать.
- **Release validator** теперь правильно отвергает actual attempt2, чужой workflow SHA,
  отсутствие runtime binding и future issued_at. Его прежние три дефекта закрыты.
- **E закрыт:** image observed manifest digest теперь связан с lock; action binding сохранён.
- **R4 positive routes закрыты:** env propagation, returncode assertions, реальные
  gate/digest/predicate/verified, полный положительный seed/release proof проходят.
- C isolation, frozen evidence, app/PG17/6 policies/107 policytests/inventory9/9/S1/
  14-flow/design не переоткрываются.

Остаток не требует новых runtime данных или нового проекта. Нужны завершение stop-семантики
того же executor, окон того же scheduler и negative cases того же route harness.

## 3. R1: расход записан, но запрет следующего I/O ещё не обеспечен

| Control | Наблюдение на3422e31 | Прежний обязательный контракт |
|---|---|---|
| Overall remaining1s, первый metadata transport занимает2s | после отказа начинается второй I/O; оба получают timeout15; authority.seconds5268 при cap5265 | после исчерпания — terminal stop, новых I/O нет |
| Remaining1s перед metadata | transport получает timeout15 | timeout ограничен оставшимся enclosing deadline ДО I/O |
| Настоящий HTTP helper получает64 bytes, затем read error | authority.bytes0 | частичный body учитывается при любом исходе |

Тесты — `BudgetTermination.*`. Ответы и время synthetic; вызываются настоящие
`run_read`, `_io_call`, `default_http_get`, `_charge`, authority persistence.

Причина повторного I/O: `_charge` записывает overrun и бросает ReadError; локальное
`_TRANSPORT['seconds']` не увеличивается, так как исключение происходит раньше. Следующий
`_overall_exhausted()` смотрит старые base+local; request charge проверяет только поле
requests и снова разрешает чтение. Файл authority знает об исчерпании, executor его не
использует как terminal authority для следующей операции.

Причина HTTP bytes0: chunks находятся внутри `default_http_get`; на исключении helper
возвращает только ReadError. `_io_call` учитывает время, но полученные bytes теряются до
`_count_bytes` вызывающей функции. Аналогично проверить timeout/over-cap paths и WAL-subset,
чтобы исправление одного транспорта не оставляло другой с прежней семантикой.

Завершить один путь `permit → I/O → durable consumption → terminal outcome`:
- перед каждым I/O/ожиданием проверять актуальный authority по ВСЕМ применимым пределам;
- ограничивать вызов минимальным остатком request/sample/window/WAL/overall time и body;
- фиксировать actual partial consumption при ошибке, не выдавать его повторно после crash;
- после исчерпания возвращать typed disposition/journal без нового I/O;
- сохранить additive concurrency fix и запрет повторного request slot.

Запись факта перерасхода — полезное исправление, но сама по себе не является hard limit.
`_io_call` в finally считает уже прошедшее время; это не отмена блокирующего I/O в deadline.
Не заменять полноценное ограничение очередной проверкой лишь после возврата. Существующий
`default_http_get` по-прежнему делает blocking read без настройки remaining absolute time;
kubectl имеет прежние grace0.08s/minimum wait0.1s. Это ранее изложенный остаток, не новая норма.

## 4. R2: финальное перечитывание не может обойти истёкшее health-окно

Независимый S0 control использует одновременно transient HC-OP и HC-DNS:
- OP observations: 300,310,325,340,340;
- DNS observations: **300,315,330,340**;
- DNS indeterminate во всём своём W30, впервые healthy на340 (>330);
- итог — **HC-DNS PASS и aggregate PASS**.

`HealthWindows.test_late_dns_cannot_turn_expired_window_into_pass` воспроизводит результат
через настоящий main. Единственная positive fixture разница — время появления готовности.

Причина: окно проверяется перед sleep только в retry loop; final freshness sweep выполняется
без проверки окна и может заменить INCONCLUSIVE поздним PASS. Начало общего retry clock
также определяется после initial GET sweep, вместо per-check начала наблюдения.

Завершить принятую W/I/N-семантику: per-check first observation/start, due time, absolute end,
N включая first/final, валидный timestamp фактического GET. Поздний healthy ответ не должен
закрывать check, который ни разу не прошёл в разрешённом окне. Final freshness re-read
остаётся частью разрешённого алгоритма и не создаёт новый допуск/новое окно сам по себе.
Сохранить shared DB/ARCH, failure precedence, freshness30/60 и уже исправленные N6/N12.
Проверить несколько одновременно transient checks — одного happy check недостаточно.

## 5. R3: single-attempt исправлен в release, но отсутствует в first-creation

`SeedGate.test_actual_second_seed_run_rejected` вызывает реальный CLI `first-creation`:
полный bound gate attempt1, `GITHUB_RUN_ATTEMPT=2`, совпадающие source/repository/workflow.
Результат **exit0 / first_creation=VERIFIED**.

В first-creation branch нет проверки actual run attempt. Заявление «тот же actual-attempt
контракт для обоих validators» пока не подтверждается. Довести seed ветку до принятого
single-attempt контракта: проверить actual attempt, требуемое поле документа и их связь;
отсутствие binding — отказ. Release-проверку не переписывать: её предыдущие controls PASS.
Добавить положительный seed attempt1 и отрицательный seed attempt2 через тот же CLI/template.
Никакого CI/push для этого не требуется.

## 6. R4: положительные маршруты работают; отказные маршруты ещё не проверяют cleanup

`NegativeRoute.test_release_build_failure_executes_always_cleanup` подменяет только
внешний buildctl: readiness exit0, build exit42. Production template steps неизменны.
Реальный `_run_release_route` прекращается на `assertEqual(returncode,0)`:
- nonzero build обнаружен — правильно;
- Sign не исполняется — правильно;
- **always cleanup не исполняется в harness** — оставшийся пробел.

Это **не утверждение**, что GitHub Actions проигнорирует `if: always()` в production.
Это воспроизведение неполноты заявленного offline negative E2E. Production always-step уже
существует; тестовый runner должен моделировать его после отказа и доказывать вызов.

Завершить один общий route runner для positive/negative:
- помнить failed outcome, пропускать последующие protected steps, но исполнять always steps;
- собирать trace/returncodes/output files, assertions делать после cleanup;
- inject readiness/build/proof error для seed/release и доказать nonzero + no subsequent
  protected operations + cleanup;
- REUSE/STOP провести через тот же job/step routing с precheck output и подтвердить 0 build/push.
  Сейчас соответствующий тест исполняет precheck и проверяет структуру, но не весь routing.

Настоящий semantic `verified` сохранить. Digest mismatch после положительного маршрута —
полезный unit/control, но он не заменяет proof-error ВО ВРЕМЯ исполнения маршрута с cleanup.
Не увеличивать mock-область до validators и не возвращать готовый PASS.

## 7. Одно продолжение основному Hermes

Продолжить тот же source-task без запроса нового «продолжай». Объём не расширяется:
R1 terminal accounting/deadlines/partial consumption, R2 окно при нескольких checks,
R3 seed attempt binding, R4 negative routing. E и положительные закрытые ветви сохранить.

До отчёта выполнить full-contract самопроверку по production traces, а не только по7 controls.
Контроли показывают остаток; требования уже находятся в прежнем review. Сверить все returncodes,
actual I/O/time/bytes, authoritative counters, stop/cleanup и outputs. Не маркировать COMPLETE,
пока hard-limit означает только запись после превышения или negative runner не доходит до cleanup.

Окончательный source commit → единый offline launcher exit0 → новый evidence commit.
Матрица requirement→code→test→evidence, full dependency manifest, точные команды/cwd/UTC/exit,
честная граница synthetic/CI/live. Исторические evidence не менять. Поправить число тестов в
НОВОМ отчёте; старый transcript и каталог сохранить. Fast-forward, без force/rebase/amend.
Промежуточные commits PARTIAL разрешены без нового допуска; итоговый STOP — полный пакет либо
непреодолимый внешний blocker после завершения независимой source-работы.

Hermes2 не участвует. Не переоткрывать app/PG17/policies/inventory/S1/14-flow/C isolation.
Никаких live/SSH/cluster/Owner helpers, CI/private registry, workflow publication/dispatch/token,
реальных build/push/sign, NetPol apply/production, backup/restore/PITR/failover. Execution gate
не выдан. Перечисленные source-дефекты не являются внешними prerequisites.

```text
REVIEWED_SOURCE_SHA=3422e31e97742dd32ad5044451eb062ee5dacf1d
REVIEWED_EVIDENCE_HEAD=935feb3de24116d52fd8c4da7ac963242a82fc07
EXISTING_ACTIVE_TESTS=207/207 PASS (author reported206; raw transcript actually207)
PREVIOUS_12_CONTROLS=12/12 PASS
POSITIVE_ROUTE_E2E=PASS (seed8 / release15 shell steps; synthetic tools; real verified)
ADDITIONAL_EXISTING_CONTRACT=7 methods; 1 PASS; 6 failures; 0 errors; exit1
E_OFFLINE_PIN_BINDING=CLOSED
SOURCE_PACKAGE=REWORK_REQUIRED
SOURCE_WORK=IN_PROGRESS/PARTIAL
EXECUTION_GATE_ISSUED=NO
CI_RELEASE / LIVE_READINESS / PRODUCTION=NOT_EXECUTED
NETPOL_APPROVED_FOR_APPLY=NO
P8C=NOT_FINAL_ACCEPTED
P8D–P8G/P9=NOT_AUTHORIZED
```
