# P8C — source acceptance f657318 / evidence d22aa8f

Дата: 2026-11-18. Architect decision: **SOURCE_ACCEPTANCE=ACCEPTED**.

## Закреплённый пакет

| Поле | Значение |
|---|---|
| Принятый source SHA | `f657318125628c986728c5e1fc0055f424c1d90a` |
| Проверенный evidence/main SHA | `d22aa8f1170deaf09580518916ea02c7c4d8bfba` |
| Закрываемый review | `188714952c415a9b608b0fa58fa1200e39112ce0` |
| Проверенное Git tree | `72fbe02838850c1ed9576ef73c263481fe607322` |
| Independent evidence | `evidence/P8/20261118-d22aa8f-source-acceptance/` |

Connector подтвердил последовательность review → source → evidence без расхождения с main. В source изменены readiness wrapper, подключение трёх контролей в launcher и соответствующий runbook. Приложение Portal, policy YAML, collector и ранее принятые эксплуатационные evidence не изменялись. 88 файлов локального snapshot, присутствующих в проверенном дереве, сверены по Git blob; несовпадений нет. Точный состав и SHA256 — в `source-manifest.json`.

## Решение по R1

**R1.1 CLOSED.** Сокет HTTPResponse регистрируется при makefile до блокирующего чтения headers. При deadline чтение прекращается через shutdown, worker завершает работу до terminal return в предоставленном воспроизведении. `test_headers_io_terminated_before_terminal_return` проходит. Прежние controls медленных headers/chunk framing/body и положительный HTTP-контроль также проходят.

**R1.2 CLOSED.** Успешно возвращённый metadata body списывается через `_charge_partial` в overall и WAL subset. Overrun первого счётчика не пропускает второй. Отказной и положительный metadata controls проходят; прежние non-UTF8/elapsed/partial-body controls сохраняют PASS.

**R2/R3/R4 и остальные ранее принятые source-части сохраняют приёмку.** Новых блокирующих замечаний в проверенном остатке R1 нет. Действующее задание source-доработки завершено; очередное задание на расширение тестов или повторную переработку этого пакета не требуется.

## Независимое подтверждение

- 243/243 активных тестовых метода PASS, все команды exit=0; qualification CLI — `qualified:true`.
- Включены 3/3 terminal-lifecycle controls review 1887149 и 6/6 предыдущих HTTP-lifecycle controls.
- Полный перечень команд, cwd, UTC start/end, exit и число методов: `reexecution.json`; вывод: `reexecution-raw.txt`; воспроизводимый runner: `run_review.py`.
- Python независимой среды 3.12.14; авторский полный launcher — Python 3.11.15. Это две разные среды, не один и тот же прогон.
- 36 syntax checks AST/bash -n PASS (`syntax-execution.json`).
- Python process tree с запретом socket.connect/getaddrinfo; попыток подключения не зафиксировано. HTTP controls используют анонимные AF_UNIX socketpair; release/seed маршруты — fake external tools, без настоящего build/push/sign.
- Авторский cached pin verification 10/10 отражён в его transcript. Независимый прогон этого review не выполнял новую upstream/registry/crypto-проверку и не превращает cached результат в live evidence.
- Принятые Portal/PG17/NetworkPolicy/inventory/backup tests не повторялись.

Приёмка относится к согласованному отдельному readiness CLI и release/seed source-маршрутам с зафиксированными ограничениями. Она не является подтверждением произвольного многопоточного переиспользования wrapper как библиотеки или live работоспособности окружения.

## Следующий этап: исполнение, а не новый цикл source-разработки

Следующее решение — отдельный конкретный release execution gate на принятый пакет:

1. Зафиксировать разрешённые workflow publication/dispatch, фактический workflow SHA, source/package binding, срок и одноразовый бюджет. Использовать актуальные шаблоны и helper bytes принятого source, а не старые manifest/pin-статусы ноябрьских draft.
2. Подтвердить private package/access. Seed запускать только если он нужен и разрешён собственным first-creation gate; REUSE/STOP сохраняют нулевой build/push. Не ослаблять private-before.
3. В разрешённом CI выполнить release и вернуть image digest, source binding, private visibility, scan, SBOM, signature/attestation и проверку артефактов. Неуспех — фактический runtime blocker, без автоматического повторения и без подмены source-дефектом.
4. Остановиться до NetPol/deployment. Для runtime-readiness отдельно нужны реальное bound clock evidence и разрешённые чтения; для apply/migration/deployment — отдельное решение по текущим prerequisites и rollback.

Этот документ фиксирует порядок следующего этапа, **но не выдаёт execution gate**, не публикует workflows и не разрешает Owner-действия. Реальные runner/rootless/registry/crypto/clock и live E2E остаются NOT_EXECUTED. Отсутствие этих будущих доказательств больше не удерживает source-пакет в PARTIAL.

## Итоговые статусы

```text
SOURCE_WORK=COMPLETE
SOURCE_ACCEPTANCE=ACCEPTED
ACCEPTED_SOURCE_SHA=f657318125628c986728c5e1fc0055f424c1d90a
R1/R2/R3/R4=CLOSED
READINESS_WRAPPER_SOURCE_QUALIFIED=YES
RELEASE_TEMPLATE_SOURCE_QUALIFIED=YES
PRIVATE_SEED_TEMPLATE_SOURCE_QUALIFIED=YES
INDEPENDENT_OFFLINE_TESTS=PASS (243/243)
NEXT_STAGE=RELEASE_EXECUTION_GATE
CI_RELEASE=NOT_EXECUTED
WORKFLOW_PUBLICATION_DISPATCH=NOT_AUTHORIZED
BOOTSTRAP_PUSH=NOT_EXECUTED
LIVE_READINESS=NOT_EXECUTED
PHASE2_NEW_RUN_APPROVED=NO
NETPOL_APPROVED_FOR_APPLY=NO
OWNER_HELPERS=NOT_EXECUTED
PRODUCTION_MIGRATION_DEPLOYMENT=NOT_EXECUTED
P8C=NOT_FINAL_ACCEPTED
P8D–P8G/P9=NOT_AUTHORIZED
```

Evidence scan — frozen publication payload, эвристические credential-паттерны без совпадений; scope/hashes/limitations сохранены в `review-scan.json`. Исторические отчёты остаются неизменными; эта приёмка заменяет их открытый source-статус для закреплённого пакета.
