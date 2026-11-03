# P8C R1 candidate and gate designs — acceptance of 4a55a7e

Дата решения: 2026-11-04 (Europe/Moscow).
Reviewed main/source: 4a55a7ec799243e0804b12c939dd2dd29c2366f0.
Parent review: 374e55d45af03a1aeaf343e1046f4a44204c23cc.
Task: P8C-R1-CANDIDATE-AND-GATES-R4-FINALIZATION.
Executor: PRIMARY HERMES; Hermes2 not involved.

## Решение

F1=CLOSED / SOURCE_REVIEWED
F3=CLOSED / DESIGN_REVIEWED
EDITORIAL=CLOSED
R4_SOURCE_PREPARATION=ACCEPTED_WITH_EXECUTION_LIMITS

Согласованный остаток задания закрыт. Новый корректирующий цикл F1/F3 не требуется.
Приняты exact-contract guard и source-only проекты gate. Это НЕ приёмка работающего Portal,
НЕ квалификация неизменённого release template и НЕ разрешение применять политики.

## Независимая проверка и пределы

Connector подтвердил main, parent и diff из 12 файлов: три draft, flows_test.go, regression,
fixture и новое evidence. Candidate YAML/app/collector/RBAC/deployment/Gateway и прежние evidence
не изменены. Проверены Git blob hashes всех 16 прочитанных файлов; 6/6 SHA-256 исходников совпали
с source-manifest.json и scan-input-hashes.txt.

| Требование | Проверенный результат | Основание |
|---|---|---|
| Frozen fixture | byte-identical reviewer fixture; 6 exact identities/specs соответствуют accepted YAML | fixture blob 91a4e571ea36395b3cafd8490f057a28e78cf4d6; YAML blob 15f0b3245586bf5086e5a24ed02b0460121f7712 |
| Exact guard | два typed представления, count/missing/extra identity + reflect.DeepEqual целого объекта; global port sets удалены | flows_test.go blob 1fd09c93f37734bf46e38901c526143f949f0ce6 |
| Reviewer regressions | 10 supplied cases интегрированы побайтно; PASS в авторском transcript | reviewer_exact_rule_regression_test.go blob e40304dc10b1644e992459d21e5707486e897ce0 |
| Behavioral tests | both-sides/stage/DNS tests сохранены | flows_test.go + raw-transcript |
| DNS mutation | по inspected predicate меняются только 5 DNS PodSelector; остальные поля сохраняются | независимая Python-проверка исходных объектов и того же predicate |
| WAL binding/budget | Cluster→Pod→metrics→same Pod→same Cluster; 90 req / 36 MiB / 3960s observation upper bound; freshness/skew/STOP | runtime draft blob d95c2fef5117a839ad9017ffa4a7a6e395b55df1 |
| Editorial | full SAR subject, named-Role scope, literal ledger query; 24h future launch expiry | deployment blob b654565d7e14ead36f7d0c44c9b0cb98b077c42c; release blob 033970548b06c4d28e26d72d021d8895650743ad |
| Evidence scan | повторен тот же heuristic над 6 точными файлами: grep 3.11 exit=1, stdout/stderr пустые | новый audit-result.json с полным argv |

Авторский transcript содержит 4 функции / 107 subtests PASS, включая 10 reviewer cases, exit 0.
Go в среде Architect недоступен: отдельный Go-прогон не заявляется. Независимо исполнен Python
source/artifact audit (Python 3.12.14), exact YAML/JSON comparison и grep.
Python-проверка DNS не выдаётся за добавленную Go assertion или runtime CNI test.

Отчёт автора снова объединяет source/evidence в один commit, а строка scan command использует
сокращённый список. История не переписывается. Для этой приёмки содержательная привязка восстановлена
через полный immutable commit + шесть побайтно проверенных hashes; отдельный reviewer scan сохраняет
полный исполнимый argv. Это ограничение provenance, не основание повторять уже закрытый пакет.
Дальнейшие execute-пакеты должны фиксировать source SHA до выполнения и затем отдельное evidence.

Scan проверяет ровно перечисленные шесть файлов ограниченным regex; не весь репозиторий/evidence и
не все возможные секреты. Наличие no-match не является абсолютным доказательством отсутствия секретов.

Evidence: evidence/P8/20261104-4a55a7e-architect-acceptance/.
audit.py + connector-input.json + audit-result.json дают воспроизводимую проверку прочитанных байтов.
Фактический UTC прогона сохранён в audit-result.json; дата решения указана по Europe/Moscow.

## Замороженные результаты

- Candidate policy semantics NP-01..04 и точный fixture закрыты source-only.
- Inventory 9/9, collector/identity/S1, offline design и application source не переоткрываются.
- Предыдущие native PG17, backup/base/latest restore/PITR/failover evidence не повторяются.
- Design выбора operator primary-bound exporter и private seed gate принят; механизм исполнения
  ещё должен пройти самостоятельную квалификацию.
- Порядок S0–S4/UID rollback и ранее принятый design сохраняют силу. Новая операция не начинается
  до PASS текущих обязательных проверок; INCONCLUSIVE не равен разрешению продолжить.

## Что осталось до работающего MVP

1. Исполнимый release-пакет: source-bound проверка tool/action/image pins; соответствие template
   принятым timeouts/permissions/identity; private-package/bootstrap prerequisite; review.
   Publication/dispatch/seed/push потребуют отдельного точного допуска.
2. Исполнимый read-only readiness wrapper по принятому контракту: typed safe output, finite limits,
   before/after binding, clock-skew evidence method, offline tests; review.
   Живые чтения требуют отдельного bounded gate.
3. Owner auth/pull provisioning, verified signed image digest и свежий platform baseline.
4. Отдельный deployment gate: policies, migration, app, Gateway в принятом порядке;
   фактические TLS/RBAC/API/UI/evidence/platform postcheck.
5. Независимая приёмка P8C после достижения UI/API RUNNING, DB CONNECTED и platform status VISIBLE.

Этот список — следующий маршрут, не исполнительное задание и не новые разрешения.
Текущий R4-FINALIZATION завершён; основной Hermes не должен сам переоткрывать его или запускать runtime.
Следующий этап оформляется отдельным заданием с собственным source/execution scope.

## Статус

R4_SOURCE_PREPARATION=ACCEPTED_WITH_EXECUTION_LIMITS
CANDIDATE_NETWORKPOLICY=ACCEPTED_SOURCE_ONLY
RELEASE_RUNTIME_READINESS_DEPLOYMENT_DRAFTS=ACCEPTED_DESIGN_ONLY
RELEASE_TEMPLATE_EXECUTION_QUALIFICATION=NOT_COMPLETED
PHASE2_NEW_RUN_APPROVED=NO
NETPOL_APPROVED_FOR_APPLY=NO
CI_RELEASE / WORKFLOW_PUBLICATION / WORKFLOW_DISPATCH=NOT_AUTHORIZED
OWNER_HELPERS=NOT_EXECUTED
PRODUCTION_MIGRATION_DEPLOYMENT=NOT_EXECUTED / NOT_AUTHORIZED
P8C=NOT_FINAL_ACCEPTED
P8D–P8G/P9=NOT_AUTHORIZED
