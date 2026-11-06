# P8C — review e60d1db: прежние 177 тестов PASS, полный source-контракт не закрыт

Дата: 2026-11-06. Исполнитель продолжения — **основной Hermes**, без Hermes2.
Это продолжение P8C-SOURCE-CLOSURE-SINGLE-PASS и review
f9755275004977eb54f49e44ae0d215670c32151; новый execution gate не выдаётся.

**Вердикт: SOURCE_PACKAGE=REWORK_REQUIRED, SOURCE_WORK=IN_PROGRESS/PARTIAL.**
Причины ниже воспроизводятся offline. Их нельзя отнести к CI-only/live prerequisites.

## Проверенный пакет и границы проверки

- Source: `9a4ed77d3131d0b2078b6917e1a7d4419ec02b65`.
- Evidence/head: `e60d1db38fdb19997acc4bbc3177f65e49cb8514`.
- Connector подтвердил последовательность f975527 → 266ea97 → cae118d → 94877dc →
  6a0ad93 → 9a4ed77 → e60d1db. Последние source/evidence commits: 22:18:54Z / 22:20:39Z.
- Exact Connector blobs извлечены и проверены по Git blob SHA; source-manifest приложен.
- Все **177 активных test methods повторены: 177 PASS**, qualification CLI exit0.
  Python reviewer 3.12.14; авторский toolchain 3.11.15.
- Дополнительные проверки **существующего** контракта: **17 методов / 3 PASS /
  14 failed assertions / 0 errors**, exit1. Это воспроизведения остатка A/B, не 14 новых задач.
- Результаты API/metrics, часы, release gates и инструменты в воспроизведениях synthetic.
  Локальные subprocess проверяют настоящий transport/CLI. Production-код не менялся.

Evidence: `evidence/P8/20261106-e60d1db-architect-review/`:
`reexecution.json`, `reexecution-raw.txt`, `remaining_contract_test.py`,
`remaining-contract.txt`, `additional-execution.json`, `route-audit.json`,
`source-manifest.json`, `review-scan.json`, runner scripts и network guard.

Полный shell launcher не запускался повторно: его cached binary artifacts отсутствуют у
reviewer. Public pin 10/10 — авторский результат, не новый независимый прогон загрузок.
Все 177 методов и qualification CLI запущены отдельно с private TMPDIR/authority.
Python network guard блокировал DNS/connect во всём тестовом дереве. Он зафиксировал
одну попытку DNS из seed STOP-теста, который вызывает настоящий `private` с fake token:
вне guard этот тест не является строго offline. Запрос к registry/кластеру не выполнялся.

## Сохранить подтверждённые исправления

Точные kind/apiVersion вместо broad ALLOWED_API в predicates, value-free Felix detail,
sidecar flock + file/dir fsync, уменьшение kubectl read размера до остатка, gate identity
для clock evidence, pod UID в WAL baseline, health failure precedence и stale rejection,
release always-cleanup, seed proof-файлы и работающая тестовая изоляция — реальный прогресс.
Прежние reviewer regression, включая 20 residual-contract методов, теперь проходят.
Историческую budget-fixture ошибку не переоткрывать; C isolation остаётся CLOSED.

Однако flock/MAX не доказывает сложение независимого расхода; наличие gate-файла не
доказывает его валидность; названия steps не доказывают исполнение маршрута.

## A1. Одно исправление accounting/transport по всему маршруту

| Контроль | Наблюдение на 9a4ed77 | Что требуется прежним контрактом |
|---|---|---|
| Два процесса: каждый резервирует один request из общей базы 0 | оба `charged`, authority.requests=1 | независимые charges суммируются; check/reserve/commit сериализованы |
| Общая база 232, два процесса | оба `charged`, authority.requests=233 | из одного оставшегося slot разрешён только один charge |
| `_count_seconds(10)` | runtime seconds=10, authority.seconds=0 | elapsed durable до следующего I/O и после ошибки/crash |
| fake kubectl stdout=`{}UNVALIDATED_SUFFIX`, cap=2, exit0 | возвращает `{}`, exit0, ошибки нет | исчерпание cap без доказанного полного ответа не превращается в успешный усечённый JSON |
| WAL после двух metadata GET: overall body remaining=1 | HTTP получает cap=1048576 | cap HTTP ограничен фактическим минимумом remaining overall/WAL/window/sample/request |

Тесты — `BudgetTransport` и `MainRoutes.test_wal_metrics_cap_uses_remaining_overall_body`.
Конкурентные тесты используют два процесса и barrier, настоящий `_count_request` и один
authority; это проверка примитива accounting, не утверждение о выполненных live запросах.
Положительный контроль полного ответа ровно cap проходит.

Причина MAX: каждый процесс вычисляет absolute total из своего старого base; lock защищает
только запись MAX(1,1), а не атомарную проверку остатка и добавление двух независимых charges.
Решение должно исключать и потерю расхода, и двойную выдачу последнего slot. Допустима
корректная сериализация исполнителя, если она охватывает весь authority и подтверждена тестом.
Не подменять additive accounting максимальным числом одного процесса.

`_persist_budget_now` вообще не добавляет `_TRANSPORT['seconds']`; main в конце суммирует
duration_ms из итоговых journal-записей, заменённых health sweep-ом. Исправить единый учёт
реального elapsed, включая HTTP/metadata, ожидания и ошибочные/частичные ответы.
Сохранить все принятые sample/window/WAL/HC/PR/overall пределы.

Дополнительный source audit уже изложенного hard-deadline контракта: `run_read` передаёт
15s без remaining overall time; WAL metadata/HTTP передают 5s без remaining sample/window time.
`default_http_get` вычисляет remain, но блокирующий `resp.read` не ограничивает этим остатком;
проверка после возврата лишь отвергает поздний ответ. Kubectl timeout-ветка содержит явный
0.08s grace, wait использует минимум 0.1s. Нужен единый абсолютный deadline внутри transport,
а не только поздний non-PASS. Накопленные bytes должны учитываться и при исключении.

## A2/A3. Полные health windows, корректный scope и привязка операции

1. **PR-6 сейчас отвергает реальный NamespaceList.** `pred_pr6` требует непустой
   `metadata.namespace` у Namespace. Namespace cluster-scoped; требуется name/UID и
   валидный selector context, а не namespace поля у самого Namespace.
   Контроль с корректным непустым NamespaceList даёт FAIL `namespace item identity missing`.
   Прежние позитивные fixtures используют пустой NamespaceList, поэтому дефект скрыт.
   Официальный source Kubernetes v1.36.2 `pkg/registry/core/namespace/strategy.go`, blob
   `9c5a7347ac7037199e05c13e79b0fc4f58673e51`: `NamespaceScoped() bool { return false }`.
   Ссылка: https://github.com/kubernetes/kubernetes/blob/v1.36.2/pkg/registry/core/namespace/strategy.go
2. **Один повтор вместо нормативного W/I/N.** HC-OP transient INCONCLUSIVE на первых двух
   наблюдениях, здоровый на третьем в разрешённом окне: main делает только GET на 300/310s
   и заканчивает INCONCLUSIVE. Реализовать принятые per-check W/I/N (включая DNS interval5,
   Gateway N12), shared DB/ARCH и freshness на итоговом verdict. Нельзя просто увеличить
   константу двух проходов; timestamp должен принадлежать фактическому GET, не cache hit.
3. **Action receipt ещё не подтверждает нужную операцию.** После валидного S0 настоящий main
   выдаёт S1 PASS с receipt `stage=S4`, чужим `gate_sha256`, `outcome=FAIL`, если совпали лишь
   source/package/op_end. Эти три равенства недостаточны. Согласовать и реализовать один
   typed receipt-контракт: конкретный gate/stage/operation/успешный исход и время, затем
   использовать его в production-пути и положительных/отказных fixtures. Не требуется
   выдумывать новый внешний сервис или криптографический протокол.

Тесты — `MainRoutes`; здоровый S0 control проходит. Сохранить failure precedence, точные
GVR, clock binding, primary/owner/IP/restart/baseline identity и остальные принятые guards.

## B. Release/seed gate и сквозной маршрут остаются source-работой

### Проверка допуска

Настоящий `release-check.py release-gate` возвращает exit0 / gate=bound для:
- документа только с `source_sha`;
- `mode=TEST_ONLY`, issued_at 2000 года, expiry_hours24;
- attempt2 при аргументе текущего attempt2.

Repository/package/workflow, mode/issued_at/expiry и single-attempt должны быть обязательными
и связанными с фактическим запуском. Сравнение двух равных `2` не доказывает attempt1.
Seed `first-creation` также принимает отсутствие repository/package/workflow и произвольный
синтаксически корректный workflow_sha. Корректный bound seed control проходит — отрицательные
тесты не ломаются из-за невалидной общей fixture. Тесты — `ReleaseBindings`.

**Release gate delivery отсутствует.** В template `workflow_dispatch: {}`, consumer читает
`$RUNNER_TEMP/release-gate.json`, но предшествующего producer/input нет. Тест пишет файл
сам. Реализовать явный безопасный data→file маршрут в неактивном template и проверить его
в том же fake-tool E2E. Публиковать workflow/запускать CI нельзя.

### Что E2E действительно исполняет

`route-audit.json` получен инструментированием вызовов существующего `_run_step` без замены
его реализации. Тесты зелёные, но:

| Заявленный тест | Реально исполненные template steps |
|---|---|
| seed full route | precheck → Start BuildKit → Build; first-creation validator подменён `exit 0` |
| release full route | только Future execution gate; остальные шаги проверяются порядком названий |

Seed cleanup/postproof/collect/upload не исполняются; REUSE отдельным позитивным маршрутом
не проверяется. Release build/scan/sign/attest/proof/cleanup не исполняются. Поэтому 4/4 —
реальный PASS ограниченных тестов, но **не доказательство заявленного полного E2E**.

Завершить прежний контракт B: исполнять реальные template steps и helpers с fake только
внешним I/O/tools, без подмены validators готовым PASS. Проверить REUSE/STOP→0 build/push,
положительный CREATE_ALLOWED, release полный digest-bound маршрут, refusal/cleanup после
ошибок gate/readiness/build/proof. Пути передачи gate и artifact-файлов входят в маршрут.
Readiness loop `30 × (timeout5 + sleep1)` может длиться около180s; сообщение «after30s»
неверно. Выдержать заявленный абсолютный bounded-ready бюджет либо согласованный уже
нормативный предел, не считать timeout каждого подпроцесса общим deadline.

## E. Offline pins и честная полнота evidence

`verify_offline` проверяет binary bytes, но для actions/images копирует cached status по id,
не связывая его с текущим lock SHA/digest. Synthetic cache `checkout.commit_sha=b…`, новый
lock `checkout.sha=a…`, cached status VERIFIED → exit0. Закрыть binding cache→current lock
и integrity/provenance cached evidence без новых download. Отдельно проверить image case.
Это не пересмотр принятых upstream pins, а исправление offline verifier.

Убрать сеть из offline route suite: mock transport для `private` должен различать REUSE,
404-with-approved-gate, error/STOP; production decision logic оставить настоящей. Reviewer
network-attempt log содержит только event/result, не адреса/креды.

## Одно продолжение основному Hermes

Продолжать **то же** source-задание без нового «продолжай». Закрыть A1/A2/A3/B/E как один
исполняемый пакет. Не сводить работу к 17 supplied методам: они воспроизводят наблюдения,
а acceptance — весь уже согласованный контракт f975527/8784116 и single-pass task.
Сначала собрать целые production routes и соответствующие positive/negative controls,
затем один полный launcher на окончательном source SHA. Не выдавать SOURCE_WORK=COMPLETE
по числу PASS при оставшихся source-placeholder/неисполненных маршрутах.

Нужны: точный source SHA → единый offline прогон с exit0 → отдельный evidence commit;
матрица requirement→production code→test→evidence с честной границей mock/CI/live;
полный dependency manifest; новые evidence, неизменённые исторические файлы. Fast-forward,
без force/rebase/amend. Промежуточные commits PARTIAL допустимы, не требуют нового допуска.

Accepted application/PG17/policy6/107 policytests/inventory9/9/S1/14-flow/design и C isolation
не переоткрывать. Hermes2 не нужен. Никаких SSH/cluster/live/Owner helpers, CI/private registry,
workflow publication/dispatch/token, реального build/push/sign, NetPol apply, production,
backup/restore/PITR/failover. Наличие этих запретов не мешает исправить перечисленный source.

```text
REVIEWED_SOURCE_SHA=9a4ed77d3131d0b2078b6917e1a7d4419ec02b65
REVIEWED_EVIDENCE_HEAD=e60d1db38fdb19997acc4bbc3177f65e49cb8514
EXISTING_ACTIVE_TESTS=177/177 PASS (offline network guard)
QUALIFICATION_CLI=exit0 (limited coverage, not full-route acceptance)
ADDITIONAL_EXISTING_CONTRACT=17 methods; 3 PASS; 14 failures; 0 errors; exit1
C_TEST_ISOLATION=CLOSED
SOURCE_PACKAGE=REWORK_REQUIRED
SOURCE_WORK=IN_PROGRESS/PARTIAL
EXECUTION_GATE_ISSUED=NO
CI_RELEASE / LIVE_READINESS / PRODUCTION=NOT_EXECUTED
NETPOL_APPROVED_FOR_APPLY=NO
P8C=NOT_FINAL_ACCEPTED
P8D–P8G/P9=NOT_AUTHORIZED
```
