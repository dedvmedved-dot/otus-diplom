# P8C-R1 RV-02 — Architect review bcda2f7; source acceptance and follow-up implementation

Дата: 2026-10-27, Europe/Moscow. Основной Hermes; Hermes2 исключён.

## Решение

REVIEWED_MAIN_SHA=bcda2f78e20a5f83a05f021c5bb4726202f6ca0e
REVIEWED_SOURCE_SHA=3139e08e4243868d5de2aa9f52d054e424e0a653
S1_IDENTITY_EXTENSION=CLOSED / INDEPENDENTLY_VERIFIED
SUPPLEMENTAL_TESTS=36/36 PASS (independent replay)
S2_SUBMITTED_DESIGN=REWORK_REQUIRED (конкретные ошибки ниже)
S2_ARCHITECT_CORRECTED_DESIGN=ACCEPTED_WITH_LIMITS / SOURCE_IMPLEMENTATION_AUTHORIZED
FOLLOWUP_COLLECTOR_IMPLEMENTED=NO (новая работа, не готовый runtime)
IDENTITY_CHAIN=ACCEPTED_PREVIOUSLY_NOT_RERUN
PHASE2_NEW_RUN_APPROVED=NO; OWNER_PHASE2_HANDOFF_ALLOWED=NO
ONE_RUN_BUDGET=CONSUMED; NETPOL_APPROVED_FOR_APPLY=NO
ACCESS_COMPLIANCE=NOT_FULLY_EVIDENCED
FLOW_MATRIX_COMPLETE=NO; P8C=NOT_FINAL_ACCEPTED; P8D–P8G/P9=NOT_AUTHORIZED.

Нет допуска на кластерные/SSH чтения, live collector/handoff, NetPol apply/rollback,
CI release/workflow publication/dispatch/token, реальные provisioning helpers,
production migration/deployment. Принятые PG17/Portal/backup/restore/PITR/failover/P7
тесты не повторять.

## Независимая проверка

Connector: main=bcda2f7; compare 69762bf..bcda2f7 ahead2/behind0, 6 изменённых путей.
Новые evidence + supplemental.py/tests/design; исторические evidence/policies/Portal
runtime не менялись. Published tree=81a4c27b3abcfcdf15e94a592fbd46ca52b7ef2e.

S1 exact source:
- supplemental.py git blob 1b613fbd1e35a109072d2843d6e5f3a3fd47b3d6,
  SHA256 ddd9a4dc17bca97d6b36ae6b4d501e1722c5d38d6e5ac8c7b051698fa0b15491;
- supplemental_test.py git blob fce1e7293346c7825a9a56f93efaa8d169ca3b5d,
  SHA256 12625fa6923d8948eb4e5752b4a7354846870ce207046159b58aceded2cd32e5.

Команды и фактические результаты:
1. python3 review-bcda2f7/supplemental_test.py -v — exit0, 36/36.
2. python3 review-bcda2f7/reproduce.py — exit0:
   сохранённые 3 I1 Pod прошли pure validator; mock main с этими identities разрешил
   C3/C4/C5; смешанный неверный digest блокировал все три. 28 finite cases
   (оба допустимых image refs, точные bare-config/legacy forms и отрицательные случаи).
3. python3 review-bcda2f7/extract_contract.py — exit0: source-schema extraction,
   HostEndpoint scope / ports, Tier defaultAction, CNP ingress/egress peer types проверены.

AST: READ_CONTRACT и все прежние функции/классы, кроме verify_calico_identity,
не изменены; добавлен _image_id_ok. Реальный subprocess в воспроизведении замокан.
Никаких cluster operations. Existing anchored-regex + endswith для legacy forms
в комбинации допускает ровно принятые значения; это не произвольный suffix bypass.
Новый bare-config сравнивается точно. Нет необходимости исправлять работающий код
ради стиля или повторять принятую registry chain.

Evidence: evidence/P8/20261027-p8c-rv02-bcda2f7-review/
tests.txt, observations.json, reproduce.py, extract_contract.py, schema-check.json, replay.md.

## S2 findings — закрыты прямой Architect-коррекцией документа

Не выдаём исходный submitted plan за принятый без изменений:
- CNP-5 ошибочно требовал namespaced HostEndpoint. Pinned CRD и live D1: Cluster.
- HEP projection терял labels/ports, необходимые для обсуждения applicability/named ports;
  Tier projection терял spec.defaultAction (Pass/Deny, schema default Deny).
- apiVersion/kind/scope недостаточно для проверки совпадения CNP spec schema/channel.
- CNP peer/protocol/selector вложенные поля не определены полностью; CNP-2..6 не
  давали одинаково полного type/error/dependency контракта.
- NetworkSet/GlobalNetworkSet нельзя объявлять нерелевантными всем pod flows без
  анализа selectors. Неполный scope должен сохранять UNKNOWN.
- API endpoints — node addresses; обращение к Service VIP не исключает host policy.
- Pagination note признавал невозможность отличить truncated от complete.
  Для будущего collector это требование исправить, не достаточная реализация.
- supplemental-design.md сохранял stale утверждения "Phase-2 not run" для S1/C1.

Чтобы не запускать ещё один цикл documentary rework, Architect подготовил:
portal/networkpolicy/followup-read-design.md
portal/networkpolicy/followup-typed-contract.json

Первый — полный bounded read/projection/dependency/completeness контракт.
Второй — точное извлечение spec schemas без description, остальные validation keys
сохранены. Источники: pinned network-policy-api CRD blob eca1eca97c14f56836aaf8f2394fa03479e01b5f
и Calico manifest blob 21ea9b4b163305ea479bc7708965104465ffc716.
Это source design, а не доказательство установленных live CRD или работающего enforcement.
Новые текущие документы заменяют неполный исторический план; historical evidence не меняется.

## Следующее задание основному Hermes — реализовать готовый контракт offline

Продолжать без нового «продолжай». Текущий опубликованный review — основание.
Не перепроектировать принятый S1 и не скачивать повторно registry chain.

1. Recovery через Connector/git fetch: проверить main, этот review, полный corrected
   design и typed contract. Сохранить local work; unexpected change → STOP; no force/reset.
2. Создать отдельный followup collector/module по corrected design и тесты.
   Разрешены только исходники, локальные fixtures/mocks и документация.
   Не запускать прежний ten-read main(), не менять base inventory.py/policies/Portal.
   Переиспользовать принятые pure projectors и S1 gate. Допустимы минимальные imports,
   но не поведенческое расширение старого collector вне нового задания.
3. Внутренне обеспечить все зависимости, F-CS schema fingerprint, scoped identity,
   finite typed projections, pagination cap/continue failures, категории и no-overwrite.
   Ни одной новой «универсальной» raw-object выдачи; никакого произвольного kubectl API.
4. Выполнить весь адресный offline test checklist из corrected design одним полным
   пакетом. Проверить разрешённые и запрещённые ветви реального main через mocks,
   literal argv, 201/501/next-page-error, semantic-field preservation, canary suppression.
   Не ограничиваться тестами helper-функций или фразой «будет выполнено в CI».
5. New evidence: source SHA, hashes, версии, команды, timestamps/exit, test transcript,
   requirement→code→test→evidence matrix. Граница source/live явно указана.
   Исправления по новым тестам довести до конца без промежуточного запроса продолжения.
6. Публикация fast-forward, исходники → evidence; не переписывать исторические отчёты.
   Итоговый STOP после полного source package или реального внешнего blocker,
   когда независимая работа закончена. Затем Architect review новых script bytes.

Не выдавать новый скрипт оператору для исполнения и не подключаться к узлам.
Доверенный SSH host-key path и безопасный текущий credential остаются отдельным
условием будущего live Gate; их отсутствие не блокирует offline-разработку.
Даже успешный будущий bounded inventory не означает полного EFFECTIVE_POLICY_UNION
и не открывает применение namespace default-deny автоматически.

Итоговые поля:
S1_IDENTITY_EXTENSION=CLOSED (не переоткрывать);
FOLLOWUP_SOURCE=REVIEW_READY/PARTIAL;
OFFLINE_TESTS=<фактический результат>;
PHASE2_NEW_RUN_APPROVED=NO; NETPOL_APPROVED_FOR_APPLY=NO;
P8C=NOT_FINAL_ACCEPTED; P8D–P8G/P9=NOT_AUTHORIZED.
