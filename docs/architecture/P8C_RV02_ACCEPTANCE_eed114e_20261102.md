# P8C-RV02 — acceptance eed114e / MI-02A closed

Дата: 2026-11-02. Решение Architect после независимой Connector/source/test проверки.

REVIEWED_MAIN_SHA=eed114e2201f75c3235b33779780038f1e8822df
ACCEPTED_SOURCE_SHA=eed114e2201f75c3235b33779780038f1e8822df
ACTUAL_PARENT=648be2ad2702c8525a785345074cfb1da42c409c

## Решение

MI-01=ACCEPTED_NOT_REOPENED.
MI-02 / MI-02A=CLOSED / INDEPENDENTLY VERIFIED.
FOLLOWUP_SOURCE_COMPATIBILITY=ACCEPTED.
SOURCE_REWORK_REQUIRED=NO (по рассмотренным MI/LC замечаниям).
SUPPLEMENTAL_BYTE_IDENTICAL=CONFIRMED.
S1 / IDENTITY_CHAIN / LC-01/02/03 / BOUNDED_PAGINATION=ACCEPTED_NOT_REOPENED.

PHASE2_NEW_RUN_APPROVED=NO.
OWNER_PHASE2_HANDOFF_ALLOWED=NO.
NEW_GATE_RUN_BUDGET=CONSUMED (e9553b8 не переоткрывается).
NETPOL_APPROVED_FOR_APPLY=NO.
CI_RELEASE / WORKFLOW_PUBLICATION_DISPATCH / OWNER_HELPERS /
PRODUCTION_MIGRATION_DEPLOYMENT=NOT_AUTHORIZED.
P8C=NOT_FINAL_ACCEPTED; P8D–P8G/P9=NOT_AUTHORIZED.

Принимаются исходники, не результат будущего live-запуска и не весь Portal MVP.
Дополнительного corrective package по MI-02A не требуется.

## Source of Truth и предел изменения

Connector main=eed114e; compare от 648be2a: ahead=1, behind=0, 9 ожидаемых файлов.
Прямой родитель eed114e — 648be2ad2702c8525a785345074cfb1da42c409c.
Поле ACTUAL_PARENT=239c593 в отчёте Hermes устарело; FINAL_SOURCE_SHA(TBD)
разрешено этим документом в точный eed114e. Это поправка provenance,
не основание переделывать исходники. Исторический result.md не редактировался.

Единственное runtime-изменение относительно 4913f07:
в _i1_item_diag optional status=None нормализуется локально в {};
non-dict non-null по-прежнему возвращает STATUS.
Нет status-or-empty truthiness coercion. Source diff приложен.
TypeMeta-адаптер и S1 не менялись; supplemental.py byte-identical.

## Закреплённый runtime-комплект для подготовки следующего gate

Оба файла извлекать из ACCEPTED_SOURCE_SHA; эти pins сами по себе запуск не разрешают.

| Файл | Git blob | SHA-256 |
|---|---|---|
| portal/networkpolicy/followup.py | 4917bc9db76748202dfa3e799651474808aaf567 | 8e01355087db65d3c124f0a21ac5a4dd89acf0caaabc092836d469169fe57a7b |
| portal/networkpolicy/supplemental.py | 1b613fbd1e35a109072d2843d6e5f3a3fd47b3d6 | ddd9a4dc17bca97d6b36ae6b4d501e1722c5d38d6e5ac8c7b051698fa0b15491 |

followup_test.py: blob fb1b191bc54c8382263cab68efbaebde7173a145;
SHA-256 ed3356d1f9d576aa355ce66360e9a0066419067f4e1929053505bd6d3b4a20b3.
Тесты/fixtures/typed-contract/YAML не являются файлами live-комплекта.

## Независимые проверки

Проверены точные Git blobs и SHA-256 до запуска.
Python 3.12.14, свежий offline запуск 2026-11-02T09:12:01.040172Z–
2026-11-02T09:12:02.763764Z (12:12 МСК).

| Проверка | Результат |
|---|---|
| followup_test.py | 147/147 PASS, exit=0 |
| supplied item_diag_regression_test.py | 4 метода / 14 подслучаев PASS, exit=0 |
| absent/null/{} status × invalid image/ports/restartPolicy | 9/9 PASS |
| false/0/empty-string/list/list-of-object status | 5/5 PASS, STATUS сохранён |
| empty output, complete=false, 0 зависимых вызовов, независимые F-CS/F-CNP, no-canary | PASS в адресных assertions |
| supplemental.py source integrity | byte-identical, hash MATCH |
| supplemental suite | NOT_RERUN: принят ранее, исходники не менялись |

Старые ResourceWarning в тестовом harness не блокируют приёмку и не создают
нового задания на рефакторинг. Принятые platform/PG17/backup/restore/PITR/failover
проверки не повторялись. SSH, kubectl, registry, live-запуск не выполнялись.

## Состояние live и следующий шаг

Последний live-артефакт остаётся 980cee55e32bf87451919d37c898d40ae33d4557:
F-CS compatible=true; F-CNP complete empty на момент сбора; F-I1 ITEM;
пять Calico-чтений заблокированы. LIVE_FAILING_FIELD=UNKNOWN.
Offline исправление не превращает прежний EXIT=1 в PASS и не доказывает
успешность будущего live-чтения. FLOW_MATRIX_COMPLETE=NO.

Следующий шаг — отдельный Architect gate на один read-only запуск
принятого двухфайлового комплекта на node-01 с прежней подтверждённой
проверкой SSH host key и key-only auth. Gate должен закрепить новые hashes,
фиксированные argv/лимиты и обязательный возврат санитизированных preflight,
hash-check, run-meta и JSONL evidence. Старые one-run gates израсходованы.
Без нового gate Hermes и Hermes2 ничего live не запускают.

Evidence: evidence/P8/20261102-p8c-rv02-eed114e-review/.
