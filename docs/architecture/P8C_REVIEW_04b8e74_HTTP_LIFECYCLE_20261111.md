# P8C — review 04b8e74: R4 CLOSED; remaining R1 HTTP lifecycle

Review date: 2026-11-11. Исполнитель продолжения: основной Hermes; Hermes2 не нужен.

## Проверенная база и решение

- REVIEW_HEAD: `04b8e7452857230c2af588fbd70d61871cd24f16`.
- SOURCE_SHA: `7adcb29135c0e3bec7cf16c177e028dd91d1d440`.
- Предыдущий review: `b50f638a785af436ac02c987dddbfce3be44fe63`, `docs/architecture/P8C_REVIEW_73a5c28_EXECUTION_BOUNDARIES_20261111.md`.
- Connector подтвердил два последовательных коммита source → evidence после b50f638. 76 локальных файлов сверены по Git blob с деревом REVIEW_HEAD; несовпадений нет.
- Независимо выполнены все 234 активных тестовых метода: PASS, все команды exit=0; qualification CLI также exit=0. Прежние восемь execution-boundary контролей — 8/8 PASS. Python 3.12.14; авторский прогон использовал Python 3.11.15. Проверки синтаксиса: 34 файла, AST/bash -n PASS.
- R4 CLOSED: исключение executor становится отказом; protected-шаги пропускаются, always-cleanup выполняется. R2/R3 и ранее принятые E/seed/release binding сохраняют приёмку.
- R1 PARTIALLY_CLOSED: предыдущие воспроизведения устранены, но полный существующий контракт whole-operation deadline / consume-all ещё нарушается.

SOURCE_ACCEPTANCE=REWORK_REQUIRED. Отсутствие live/CI evidence не является причиной этого решения: ниже воспроизведены source-дефекты в разрешённой offline-среде.

## Остаток R1 — два аспекта одного исполнителя

### 1. Absolute deadline должен охватывать HTTP-заголовки и chunk framing

В `portal/tools/readiness/wrapper.py::default_http_get` вызов `opener.open()` читает status/headers до входа в цикл тела. Переданный timeout ограничивает бездействие сокета, а не суммарное время этой фазы. Аналогично `HTTPResponse.read1()` для chunked encoding может читать строку размера chunk через внутренний readline; периодические байты продлевают эту операцию сверх абсолютного deadline. Проверка после возврата лишь фиксирует уже случившийся перерасход.

В `http_lifecycle_test.py` реальный `http.client.HTTPResponse` работает поверх анонимного AF_UNIX socketpair. `begin()` вызывается внутри подменённого opener.open, как в HTTP-клиенте. Нет TCP, DNS или подключения к кластеру.

| Контроль | Ожидается | Наблюдение |
|---|---|---|
| `test_total_deadline_includes_response_headers` | deadline 50 ms, с тестовым запасом завершение ≤110 ms | ReadError только через 303 ms |
| `test_total_deadline_includes_chunk_size_line` | тот же предел | ReadError только через 305 ms |
| `test_normal_headers_and_chunked_body_positive` | обычный chunked body принимается | PASS, `b'x'` |

Нужен единый абсолютный предел всей HTTP-операции, включая opening/header/framing/body, с прекращением блокирующего I/O. Дополнительные post-check или только inactivity-timeout этот контракт не закрывают. Лимиты и набор разрешённых чтений не расширять.

### 2. Полученные bytes должны учитываться до decode и до выбрасывания terminal outcome

Сейчас `.decode()` вызывается до `_count_bytes/_count_wal_bytes`. Кроме того, `_io_call` в finally списывает elapsed и может выбросить ReadError вместо возврата уже полученного body; вызывающий код тогда не доходит до byte accounting.

| Контроль | Наблюдение на SOURCE_SHA |
|---|---|
| `test_non_utf8_metrics_has_typed_nonpass` | наружу выходит UnicodeDecodeError вместо типизированного INCONCLUSIVE |
| `test_non_utf8_metrics_all_received_bytes_consumed` | 64 полученных metrics bytes потеряны: overall/WAL = 224/224 вместо 288/288 |
| `test_completed_body_is_consumed_when_time_charge_overruns` | разрешённый metadata I/O вернул 129 bytes; concurrent time charge + финальное списание elapsed дают terminal overrun; bytes остаются 0/0 вместо 129/129 |

Последний контроль использует production `_charge`, `_io_call`, `run_wal_sample` и virtual clock: запрос получил timeout 1s и занял 0.1s; в это время другое списание уменьшило остаток. Сбой происходит при consume, а не из-за транспортной заглушки, игнорирующей timeout. Overrun времени корректно записан; body accounting потерян.

Нужен порядок permit → bounded I/O → учёт всех фактически полученных raw bytes и elapsed во всех применимых счётчиках → типизированный terminal outcome → decode/validation при допустимом исходе. Ошибка одного счётчика не должна мешать учёту остальных; двойное списание также недопустимо. Обработать это общей семантикой success/partial/timeout/cap/decode/accounting-error для kubectl и HTTP, а не отдельным исключением только для данного fixture.

Дополнительная suite: 6 методов, 1 PASS, 5 assertion failures, 0 errors; два отказа относятся к одному non-UTF8 сценарию. Это не пять новых функциональных требований, а воспроизведения оставшегося R1 из b50f638.

## Единое продолжение задания Hermes

1. Восстановить актуальный main fast-forward; сохранить более новые согласованные изменения. Прочитать этот review, существующий R1 и приложенный `http_lifecycle_test.py`.
2. Закрыть оба аспекта R1 в readiness executor одним проходом. Сверить весь уже согласованный путь permit/operation/consume/terminal, включая отказ в самом accounting. R2/R3/R4, release/seed, принятые budgets/allowlists/дизайны не переоткрывать.
3. Включить контролируемые offline воспроизведения в активную suite с изолированным authority. Сохранить положительный HTTP-контроль и действующие защиты; не ослаблять timeout/assertions, не вводить skip/xfail, не переписывать исторические evidence.
4. Выполнить один итоговый прогон всех активных методов плюс эти шесть контролей на окончательном source SHA. Если реализация транспорта меняется, адаптировать инъекцию тестового транспорта, сохранив проверку реального блокирующего чтения headers/framing и фактическое измерение абсолютного deadline.
5. Обновить только относящиеся к исправлению runbook/matrix/dependency manifest. Опубликовать source, затем отдельное evidence: UTC/команды/exit, SHA/blobs, raw transcript, frozen-input secret scan с ограничениями, краткую матрицу R1→код→контроль. Один итоговый STOP для Architect review.

Для разрешённой source-работы нового подтверждения не требуется. Не устраивать отдельные согласования на каждый подпункт. При обнаружении несовместимого изменения контракта — один конкретный blocker; не заявлять COMPLETE при известном source-дефекте.

## Evidence и границы

Evidence: `evidence/P8/20261111-04b8e74-architect-review/`.

- `reexecution.json`, `reexecution-raw.txt`, `run_review.py`: 234 метода и qualification.
- `http_lifecycle_test.py`, `additional-execution.json`, `additional-raw.txt`: шесть дополнительных контролей.
- `source-manifest.json`: 76 файлов с blob/SHA256 и привязкой к Connector tree.
- `syntax-execution.json`, `network-summary.json`, `network-guard/sitecustomize.py`, `review-scan.json`.

Авторские pin 10/10 не перепроверялись как новые upstream-факты. Принятые Portal/PG17/NetworkPolicy/inventory/backup tests не повторялись. Изолированные local socketpair и fake transports не являются live evidence.

PHASE2_NEW_RUN_APPROVED=NO; NETPOL_APPROVED_FOR_APPLY=NO.
CI_RELEASE / WORKFLOW_PUBLICATION / WORKFLOW_DISPATCH / OWNER_HELPERS / SSH / LIVE_READINESS / PRIVATE_REGISTRY / PRODUCTION=NOT_AUTHORIZED.
Реальные clock evidence, CI runtime/crypto/private GHCR и live E2E остаются будущими execution prerequisites; этот review их не разрешает.
P8C=NOT_FINAL_ACCEPTED; P8D–P8G/P9=NOT_AUTHORIZED.
