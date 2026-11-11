# P8C — review 73a5c28: R2/R3 приняты; остаток R1 и exceptional cleanup

Дата: 2026-11-11. Исполнитель — основной Hermes, без Hermes2.
Продолжение существующего source-контракта review
`4cff2e709d50f05bfb182fae3cc950cddd3f818b`; execution gate не открывается.

**SOURCE_ACCEPTANCE=REWORK_REQUIRED; SOURCE_WORK=IN_PROGRESS/PARTIAL.**
Объём остатка сокращён: R2 и R3 закрыты, обычные отказные маршруты R4 подтверждены.
R1 пока не стал единым механизмом исполнения; один exception-path R4 обходит cleanup.

## 1. Проверка и принятые исправления

Connector подтвердил fast-forward:
`4cff2e709d50f05bfb182fae3cc950cddd3f818b` → source
`7235e713ad22ab530bbd67c16c1b33a587506964` → evidence/main
`73a5c28e6a547ccfb181ec6f99a3a64c5381325e`.
Source commit UTC2026-11-10T21:53:12Z; evidence commit21:55:29Z.

Независимо выполнены **226/226 активных методов PASS**, qualification CLI exit0,
Python syntax и bash -n. Все12 controls предыдущего review проходят.
Тесты выполнены отдельными процессами с private authority/TMPDIR и сетевым guard.
Полный shell launcher не повторялся: проверены его226 методов и qualification CLI;
бинарный pin-cache автора отсутствует, upstream/download/CI не выполнялись.
Авторский offline pin10/10 не выдаётся за новый независимый upstream proof.

Reviewer Python3.12.14; source snapshot сверён с70 exact Git blobs, manifest приложен.
Исторические evidence, принятый app/PG17/policy107/inventory9/9/S1/14-flow не менялись.

**Принято и не переоткрывать:**
- R2: retry/final completion после конца разрешённого окна не создаёт первый PASS;
  ранее воспроизводившиеся обходы закрыты, positive S0 сохранён.
- R3: actual runtime attempt1 и integer/non-bool gate.attempt1 обязательны. Рабочая копия
  исторического positive fixture меняет только valid gate/env binding и описание;
  assertions сохранены, исторический файл не изменён.
- R1 адресно: актуальный on-disk remaining, timeout metadata+HTTP перед WAL-вызовом,
  поздний HTTP chunk и обычный partial HTTP error теперь учитываются.
- R4 адресно: любой nonzero, включая cleanup, отражён в failures; protected failure
  пропускает protected steps и выполняет always steps.
- Дополнительная полная nonzero матрица исполнена reviewer: seed/release ×
  readiness/build/proof failure =6сценариев PASS; seed REUSE/STOP =2сценария PASS,
  полный precheck→routing,0build/push. Эту проверенную часть не объявлять снова непроверенной.
- E, positive real-verified routes, additive budget charges, source/gate bindings,
  frozen tests/evidence и C isolation остаются принятыми в зафиксированном объёме.

Дополнительный suite: **8 методов /2 PASS /6 failed assertions /0 errors**, exit1.
Два PASS-метода содержат8 положительных refusal/routing подслучаев выше.
Все новые controls относятся к требованиям уже опубликованных R1/R4, не к новому scope.

Evidence: `evidence/P8/20261111-73a5c28-architect-review/`:
`execution_boundary_test.py`, `additional-raw.txt`, `additional-execution.json`,
`reexecution.json`, `reexecution-raw.txt`, `source-manifest.json`,
`syntax-execution.json`, `network-summary.json`, `review-scan.json`.
Повтор из корня repo:
`P8C_REVIEW_ROOT=$PWD python3 evidence/P8/20261111-73a5c28-architect-review/execution_boundary_test.py -v`.

## 2. R1 — hard deadline и полный расход ещё не едины

| Воспроизведение | Наблюдение на7235e71 | Нарушенное прежнее требование |
|---|---|---|
| Настоящий blocking HTTPResponse.read, медленная выдача тела | deadline0,05s, elapsed0,404s (даже с допуском планировщика0,06s — FAIL) | прерывание в absolute deadline, не проверка после завершения |
| WAL осталось1s; первый metadata GET занял0,75s | второй GET всё ещё timeout1s вместо≤0,25s | remaining включает уже прошедшее время текущего sample |
| WAL metadata subprocess вернул64bytes и завис | overall.bytes64, wal_bytes0 | partial расход каждого WAL-транспорта входит в оба бюджета |
| HTTP over-cap: overall осталось1byte, получено2 | overall overrun записан, wal_bytes0 | отказ первого счётчика не отменяет расход остальных |
| WAL осталось1s, первый запрос отказал | sleeps300+300; wal_seconds4559 при cap3960 | wait также ограничен остатком WAL; exhaustion прекращает работу |

### Точные границы независимых проверок

HTTP deadline control использует настоящий `http.client.HTTPResponse` поверх анонимной
локальной AF_UNIX socketpair. Есть реальное блокирующее чтение и постепенная выдача20bytes,
но нет TCP listener/DNS/remote host/кластера. Подменён только opener, возвращающий local response;
validator/helper исполняется реально. Socket inactivity timeout0,05s не срабатывает, потому что
байты приходят каждые0,02s; текущий `resp.read(65536)` ждёт всё тело. Это демонстрирует именно
различие inactivity timeout и общего deadline. Код узнаёт о нарушении спустя0,404s.

Metadata partial test запускает локальный fake-kubectl, который пишет64bytes и ждёт.
`run_wal_sample` и `run_kubectl_raw` настоящие. Ожидания scheduler и WAL in-flight elapsed
используют virtual clock. Over-cap test подменяет только HTTP response. Это source/offline
proof, не новый live-read.

### Причины и требуемое завершение

1. **Deadline после blocking read.** В `default_http_get` остался первоначальный socket
   timeout и blocking `resp.read(...)`; проверка после read фиксирует уже нарушенный deadline.
   Обеспечить ограничение чтения во время исполнения, включая медленный поток, остаток всего
   request и enclosing sample/window/WAL/overall. Не заменять это очередной post-check.
2. **WAL elapsed откладывается до finally sample.** `_remaining_wal_seconds()` читает актуальный
   файл, но файл ещё не содержит времени предыдущего GET этого же sample. Учитывать in-flight
   elapsed до следующего I/O и ожидания; не списывать его дважды при выходе из sample.
3. **Раздельные error paths теряют subset.** `run_kubectl_raw` при timeout вызывает только
   `_count_bytes`; HTTP вызывает `_count_bytes` и затем `_count_wal_bytes`, однако исключение
   первого charge прерывает второй. Весь фактический расход нужно durable-фиксировать во всех
   применимых счётчиках ДО выдачи terminal outcome, сохраняя additive concurrency semantics.
4. **Wait не входит в общий permit.** `run_wal_window` ограничивает sleep только overall
   остатком. После WAL exhaustion выдаёт следующие300s ожидания; `_count_wal_seconds`
   записывает overrun и подавляет ReadError. Проверка/permit должны быть общими для I/O и wait.
   Если лимит исчерпан, следующий slot/wait/read не начинается.

Завершить один механизм `permit → bounded operation → consume-all → terminal outcome`.
Проверить metadata+HTTP, success+nonzero+partial+timeout+cap-error, а также exception во время
списания одного из счётчиков. Sample/window/WAL/overall остаются с уже принятыми пределами.
Нельзя считать R1 закрытым по исправлению только пяти строк таблицы: предыдущий review
уже требовал полного покрытия всех путей и всех применимых бюджетов. Данный suite —
воспроизведения, не замена контракта. Ни новых limits, ни новых live-read здесь нет.

## 3. R4 — nonzero учтён; исключение executor ещё минует cleanup

Обычная nonzero матрица теперь проверена и принята. Остался другой исход реально используемого
`subprocess.run(...timeout=90)` в `_run_step`: он бросает `TimeoutExpired`, а не возвращает
CompletedProcess с returncode.

`RouteMatrix.test_timeout_exception_still_reaches_cleanup` проходит полный release route
до Build OCI, инжектирует именно этот process exception на границе `_run_step` и наблюдает:
- исключение выходит из `_run_job_steps`;
- дальнейшие protected steps не выполняются;
- **always cleanup не вызван**.

Это дефект offline runner/доказательства отказного маршрута, а не утверждение о поведении
GitHub Actions в реальном CI. Полный позитивный route и восьмёрка nonzero/REUSE/STOP cases
не отменяют обязанность обработать штатный timeout-исход своего executor.

Runner должен нормализовать timeout/spawn/step execution error в failed outcome, сохранить
value-free причину/trace, выполнить оставшиеся always steps и затем вернуть non-PASS.
Если cleanup тоже завершился ошибкой/исключением, итог не может стать PASS. Не подменять
gate/verified validators; внешние бинарники и разрешённые network-boundary фейки сохранить.
Интегрировать опубликованную nonzero матрицу и этот exception control в активную suite,
без изменения исторического evidence. Дополнительный CI-запуск для проверки не нужен.

## 4. Одно продолжение основному Hermes

Продолжать тот же source-task без нового запроса «продолжай». R2/R3/E и принятые positive/
nonzero routes сохранить. Осталось **два блока работы**:

1. R1 — общий deadline/permit/consumption для всех I/O и ожиданий. Не оставлять параллельные
   кусочные правила для HTTP, kubectl, WAL-finally и slot sleep.
2. R4 — обработка исключений собственного route executor с гарантированным always cleanup.

До COMPLETE провести полный self-review путей, составить таблицу operation→applicable limits→
reservation→actual bytes/time→durable update→terminal/cleanup. Это внутренняя проверка того же
контракта, не новый approval-документ. Приложить реальные traces positive и отказных ветвей.

Итоговая последовательность: final source commit → единый offline launcher exit0 → отдельный
новый evidence commit. Полный dependency manifest path/blob/SHA256; requirement→code→test→
evidence; команды/cwd/UTC/exit; отличать fake-tool proof от real CI/live. Обновить runbook
по коду. Fast-forward, без force/rebase/amend. Исторические evidence не переписывать.
Промежуточный PARTIAL commit допустим без нового допуска; итоговый STOP — полный source-пакет
либо конкретный непреодолимый внешний blocker после завершения независимой работы.

Не переоткрывать приложение, PG17, policy107, inventory9/9, S1,14-flow и backup/restore/PITR/
failover. Hermes2 не задействовать. Live/SSH/cluster/CI/private registry/реальные build-push-sign/
workflow publication-dispatch-token/Owner helpers/NetPol apply/production не разрешены.
Реальный clock evidence/CI runtime остаются future execution prerequisites; описанный остаток
R1/R4 — source-работа и не может быть перенесён в CI_ONLY.

```text
REVIEWED_SOURCE_SHA=7235e713ad22ab530bbd67c16c1b33a587506964
REVIEWED_EVIDENCE_HEAD=73a5c28e6a547ccfb181ec6f99a3a64c5381325e
ACTIVE_TEST_METHODS=226/226 PASS
PREVIOUS_12_CONTROLS=12/12 PASS
R2=CLOSED
R3=CLOSED
R4_NONZERO_AND_REUSE_STOP_MATRIX=8/8 scenarios PASS (independent offline)
R1=PARTIAL
R4_EXECUTOR_EXCEPTION_CLEANUP=OPEN
ADDITIONAL_CONTROLS=8 methods; 2 PASS; 6 failures; 0 errors; exit1
SOURCE_ACCEPTANCE=REWORK_REQUIRED
SOURCE_WORK=IN_PROGRESS/PARTIAL
EXECUTION_GATE_ISSUED=NO
CI_RELEASE / LIVE_READINESS / PRODUCTION=NOT_EXECUTED
NETPOL_APPROVED_FOR_APPLY=NO
P8C=NOT_FINAL_ACCEPTED
P8D–P8G/P9=NOT_AUTHORIZED
```
