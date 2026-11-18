# P8C — review 6c18d79: R1 actual cancellation and consume-all

2026-11-18. Основной Hermes; Hermes2 не требуется.

REVIEW_HEAD=`6c18d7940477513337d849276fd63d89d74fe202`.
SOURCE_SHA=`7ec15cc7d34bf30645a3af94dfefbd4cf3084848`.
Authority: review `151f800af93b328a24a6bcb03665e728e1f279a5`, `docs/architecture/P8C_REVIEW_04b8e74_HTTP_LIFECYCLE_20261111.md`.

## Решение и подтверждённый прогресс

Connector подтвердил source → evidence и fast-forward от 151f800. Все 82 файла локального snapshot, присутствующие в проверенном дереве, совпали по Git blob.

Независимый прогон: **240/240 методов PASS**, все команды exit=0, qualification CLI `qualified:true`. Включены шесть прежних HTTP-lifecycle контролей: 6/6 PASS. Python 3.12.14 (автор: 3.11.15). Проверки синтаксиса AST/bash -n прошли. Авторские pin 10/10 не перепроверялись как новые upstream-факты.

Принято в R1: raw metrics учитываются до decode; non-UTF8 даёт типизированный non-PASS; elapsed overrun больше не отбрасывает возвращённое тело. R2/R3/R4 и остальные ранее принятые части **не переоткрываются**.

**R1 остаётся REWORK_REQUIRED по двум воспроизводимым нарушениям уже действующего контракта.** Прежний header-тест измерял время возврата функции, а не окончание I/O: его недостаточность — пробел предыдущей Architect-проверки. Прохождение этого теста не доказывает отмену запроса. Ни live prerequisites, ни новые функциональные требования не являются основанием отказа.

## Два точных остатка

### R1.1 — возврат timeout не прекращает чтение headers

В `wrapper.py::default_http_get` `holder['sock']` заполняется только **после** возврата `opener.open()`. Пока `HTTPResponse.begin()` читает медленные headers, socket ещё не передан watchdog. Через deadline основной поток выбрасывает ReadError, но daemon worker продолжает читать. Его завершение и учёт не подтверждены до terminal outcome.

Контроль `test_headers_io_terminated_before_terminal_return` использует реальный HTTPResponse на анонимном AF_UNIX socketpair, с `begin()` внутри opener.open. При timeout 50 ms функция вовремя возвращает ReadError, однако `open_finished_at_return=false`, спустя ещё 60 ms `open_finished=false`, `worker_alive=true`; после возврата сервер отправил ещё пять байтов заголовка. Тест сам останавливает соединение в finally, чтобы не оставлять фонового I/O.

Это нарушение требования 151f800 «единый абсолютный предел всей HTTP-операции … с прекращением блокирующего I/O». Ограничить `join` недостаточно. Нужен доступный механизм отмены **до** блокирующего open/status/headers и подтверждённое окончание worker до возврата. После terminal outcome запрос не продолжает I/O/изменение accounting. Та же гарантия действует для framing/body; существующие положительные и отказные тесты сохранить.

### R1.2 — успешный kubectl body всё ещё теряет WAL-учёт при overrun overall

В `run_wal_sample.raw` остаются последовательные `_count_bytes(len(body))` и `_count_wal_bytes(len(body))`. Если первое durable-списание фиксирует overrun и выбрасывает ReadError, второе не выполняется. Исправление `_charge_partial` применено к metrics, но общая гарантия consume-all не охватывает этот metadata-путь.

Контроль `test_metadata_body_charges_wal_even_when_overall_charge_overruns`: разрешённый metadata I/O возвращает 98 bytes; во время I/O другое завершённое списание уменьшает overall-остаток до одного байта. Записан overall overrun (`187695201`), но `wal_bytes=0` вместо 98. Исход INCONCLUSIVE верный, расход неполный. Transport возвращает меньше выданного ему cap; тест не имитирует нарушение transport-контракта.

Положительный `test_metadata_body_normal_charge_positive` проходит: без конкурентного списания тот же body учитывается в обоих счётчиках.

Нужно провести metadata body через тот же порядок consume-all до terminal outcome, что и metrics, без потери или двойного списания. Отказ одного применимого счётчика не пропускает остальные. Сохранить typed non-PASS и запрет следующего I/O после исчерпания.

Дополнительная suite: **3 метода, 1 PASS, 2 assertion failures, 0 errors**. Это два остатка исходного R1, не новые независимые блоки разработки.

## Продолжение основному Hermes — одним исправлением и одной итоговой проверкой

1. Восстановить актуальный main fast-forward, сохранить более новые согласованные изменения. Прочитать этот review и `terminal_lifecycle_test.py` из evidence ниже.
2. Исправить фактическую отмену HTTP на фазе headers и общий consume-all metadata-путь. Лимиты, readset, семантику gate и принятые release/seed/R2/R3/R4 не менять. Не ограничиваться изменением условий в тестах.
3. Сохранить три воспроизведения в активной suite. При смене транспортной реализации адаптировать только точку инъекции: проверка должна по-прежнему наблюдать реальное блокирующее чтение и отсутствие живой операции после terminal outcome. Без skip/xfail/ослабления проверок. Исторические evidence не редактировать.
4. Один итоговый прогон действующей suite плюс эти три контроля на финальном source SHA; затем отдельный evidence-коммит с UTC/exit, raw transcript, полными hashes/dependencies и краткой матрицей двух исправлений. Runbook исправить только там, где он преждевременно заявлял гарантированное прекращение headers-I/O.
5. STOP для независимой source-приёмки. Для этой source-работы дополнительного подтверждения не требуется. Не создавать новые этапы согласования между подпунктами.

Граница следующей проверки остаётся прежней: закрытие обязательного R1 и регрессия действующей suite. Необязательные улучшения — backlog. Приёмка не блокируется отсутствием исполнения операций, которые сейчас запрещены.

## Evidence и статус

`evidence/P8/20261118-6c18d79-architect-review/`:
- `terminal_lifecycle_test.py`, `additional-execution.json`, `additional-raw.txt` — три точных контроля.
- `run_review.py`, `reexecution.json`, `reexecution-raw.txt` — 240 методов + qualification.
- `source-manifest.json`, `syntax-execution.json`, `network-summary.json`, `network-guard/sitecustomize.py`, `review-scan.json`.

В Python process tree запрещены socket.connect и getaddrinfo; попыток не зафиксировано. Дополнительные проверки: анонимный local AF_UNIX и fake kubectl; это не live evidence. Portal/PG17/NetworkPolicy/inventory/backup tests не повторялись.

SOURCE_ACCEPTANCE=REWORK_REQUIRED; SOURCE_WORK=IN_PROGRESS/PARTIAL (remaining R1 only).
PHASE2_NEW_RUN_APPROVED=NO; NETPOL_APPROVED_FOR_APPLY=NO.
CI_RELEASE / WORKFLOW_PUBLICATION / WORKFLOW_DISPATCH / OWNER_HELPERS / SSH / LIVE_READINESS / PRIVATE_REGISTRY / PRODUCTION=NOT_AUTHORIZED.
P8C=NOT_FINAL_ACCEPTED; P8D–P8G/P9=NOT_AUTHORIZED.
