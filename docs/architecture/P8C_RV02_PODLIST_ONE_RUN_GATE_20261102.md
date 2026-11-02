# TASK: P8C-RV02-PODLIST-ONE-RUN-20261102

Дата: 2026-11-02 (Europe/Moscow).
Исполнитель: **основной Hermes**. Hermes2 не участвует.
Репозиторий: dedvmedved-dot/otus-diplom. Единственный Source of Truth — GitHub main.

## Architect decision

```text
GATE_ID=P8C-RV02-PODLIST-ONE-RUN-20261102
RECOVERY_BASELINE_SHA=b32fa58d4d8615465e525bb3575ba5a69c469196
ACCEPTED_SOURCE_SHA=eed114e2201f75c3235b33779780038f1e8822df
PHASE2_NEW_RUN_APPROVED=YES / ONE_PINNED_RUN_ONLY
OWNER_PHASE2_HANDOFF_ALLOWED=YES / PRIMARY_HERMES_ONLY
NEW_GATE_RUN_BUDGET=1
PREVIOUS_GATE_RUN_BUDGET=CONSUMED / NOT_REOPENED
SSH_TARGET=root@192.168.194.38
EXPECTED_HOSTNAME=node-01
CONTEXT=kubernetes-admin@pak-portal
NETPOL_APPROVED_FOR_APPLY=NO
CI_RELEASE / WORKFLOW_PUBLICATION_DISPATCH / OWNER_HELPERS / PRODUCTION_MIGRATION_DEPLOYMENT=NOT_AUTHORIZED
P8C=NOT_FINAL_ACCEPTED
P8D–P8G/P9=NOT_AUTHORIZED
```

Этот опубликованный gate открывает НОВЫЙ одноразовый допуск для двух файлов ниже.
Он заменяет NO из документа приёмки только для ограниченного preflight, передачи файлов,
одного запуска, возврата результата и документальной reconciliation.
Gates fbaa9a4 и e9553b8 израсходованы и не возобновляются. Дополнительное «продолжай» внутри этого
задания не требуется. Architect публикует задание, но не запускает collector.

Основание: docs/architecture/P8C_RV02_ACCEPTANCE_eed114e_20261102.md
в b32fa58d4d8615465e525bb3575ba5a69c469196. LR-01/02, LC-01/02/03 и MI-01/MI-02/MI-02A закрыты.
Новых исправлений кода и повторных принятых тестов в этом задании нет.

## G0 — recovery и учёт допуска

1. Через Connector проверь фактический HEAD main, последние изменения, этот gate и приёмку.
   Установи полный GATE_SHA — commit, впервые добавивший данный файл.
2. Локальный checkout синхронизируй fast-forward. При конфликтующих изменениях/решениях STOP;
   не reset, не force-push, не переписывать историю.
3. Зафиксируй фактический RECOVERY_MAIN_SHA отдельно от ACCEPTED_SOURCE_SHA и GATE_SHA.
4. Убедись по журналу исполнителя/новым evidence, что этот GATE_ID ещё не исполнен и другой
   оператор не запускает его параллельно. Один исполнитель, один процесс collector.
5. До удалённого запуска запиши локальный run-intent с GATE_ID/GATE_SHA/source/target.
   С момента отправки команды запуска не считать отсутствие ответа разрешением повторить её.

Источник должен совпадать по git blob И SHA256:

| Файл в portal/networkpolicy/ | Git blob | SHA256 |
|---|---|---|
| followup.py | 4917bc9db76748202dfa3e799651474808aaf567 | 8e01355087db65d3c124f0a21ac5a4dd89acf0caaabc092836d469169fe57a7b |
| supplemental.py | 1b613fbd1e35a109072d2843d6e5f3a3fd47b3d6 | ddd9a4dc17bca97d6b36ae6b4d501e1722c5d38d6e5ac8c7b051698fa0b15491 |

Только эти два файла нужны runtime. Тесты, fixtures, typed-contract.json и PyYAML на узел
не передавать. Не менять файлы для обхода gate или parser.

Локально, из checkout репозитория; при любой ошибке STOP:
```bash
set -euo pipefail
umask 077
P8C_SOURCE_SHA=eed114e2201f75c3235b33779780038f1e8822df
P8C_LOCAL_BUNDLE=$(mktemp -d /tmp/p8c-podlist-20261102-local-XXXXXXXX)
git show "$P8C_SOURCE_SHA:portal/networkpolicy/followup.py" > "$P8C_LOCAL_BUNDLE/followup.py"
git show "$P8C_SOURCE_SHA:portal/networkpolicy/supplemental.py" > "$P8C_LOCAL_BUNDLE/supplemental.py"
(
  cd "$P8C_LOCAL_BUNDLE"
  sha256sum --check <<'SUMS'
8e01355087db65d3c124f0a21ac5a4dd89acf0caaabc092836d469169fe57a7b  followup.py
ddd9a4dc17bca97d6b36ae6b4d501e1722c5d38d6e5ac8c7b051698fa0b15491  supplemental.py
SUMS
  test "$(git hash-object followup.py)" = 4917bc9db76748202dfa3e799651474808aaf567
  test "$(git hash-object supplemental.py)" = 1b613fbd1e35a109072d2843d6e5f3a3fd47b3d6
)
printf 'LOCAL_BUNDLE=%s\n' "$P8C_LOCAL_BUNDLE"
```

## G1 — только закреплённый SSH-хост и существующий ключ

Целевой узел только node-01, IP192.168.194.38, пользовательroot.
Используй существующий разрешённый VPN-маршрут. Не соединяться с node-02/03, не делать
сетевой поиск, не использовать BMC или другой маршрут как обход.

Доверенный ED25519 host fingerprint:
```text
SHA256:4Janc/G5wzV6Yfi8gPTz55u/81atXF1xzjkDIISJjvc
```
Источник доверия — принятая Owner out-of-band attestation из915f2c6.
Метод входа — существующий авторизованный id_ed25519 (hermes@vps1), принятый по Owner-report.
Эти сообщения не заменяют фактическую проверку fingerprint при данном соединении.

Подготовь отдельный known_hosts с ED25519 ключом node-01 из существующей записи и проверь
его SHA256 через ssh-keygen. Если записи нет, допускается один
ssh-keyscan -T5 -t ed25519 192.168.194.38 исключительно для получения публичных байтов:
принимать их ТОЛЬКО после точного сравнения с доверенным fingerprint выше.
Несовпадение/неоднозначность → STOP, без TOFU.

Все SSH/SCP используют один проверенный known_hosts и один существующий авторизованный ключ:
```text
BatchMode=yes
IdentitiesOnly=yes
-i <фактический путь существующего авторизованного ключа>
PreferredAuthentications=publickey
PasswordAuthentication=no
KbdInteractiveAuthentication=no
StrictHostKeyChecking=yes
HostKeyAlgorithms=ssh-ed25519
UserKnownHostsFile=<проверенный отдельный файл>
GlobalKnownHostsFile=/dev/null
UpdateHostKeys=no
ForwardAgent=no
ClearAllForwardings=yes
ControlPath=none
ConnectionAttempts=1
ConnectTimeout=10
```
Пути разреши локально; не печатай содержимое private key, парольных файлов, ключевые фразы.
Не читать и не использовать ранее раскрытый пароль или workflow token; password fallback,
sshpass, новые ключи/изменение authorized_keys/sshd в этом задании запрещены.
Root — привилегия данного ограниченного operator-действия, не право Portal.

## G2 — ограниченный preflight и доставка

Через этот же key-only доступ разрешены:
- hostname -s → node-01; id -un → root;
- date -u +%Y-%m-%dT%H:%M:%SZ;
- python3 --version → установленный Python3.11.x;
- command -v python3, command -v kubectl;
- test -r /etc/kubernetes/admin.conf (не читать/не выводить содержимое);
- ОДИН вызов:
  KUBECONFIG=/etc/kubernetes/admin.conf kubectl --context kubernetes-admin@pak-portal
  --request-timeout=15s version -o json.
  Client/server должны бытьv1.36.2.

Обязательно сохрани preflight.txt: фактические команды, UTC, санитизированный вывод и
exit КАЖДОЙ проверки (hostname/user/Python/наличие команд/admin.conf-readable/client+server).
Отдельно сохрани локальный hash-check-local.txt: git blob и SHA256 для обоих файлов.
Удалённый hash-check.txt создаётся блоком G3 ниже. Не заменять эти transcripts таблицей
«проверено/OK». Если запись transcript не подготовлена, collector не запускать.
Не включать SSH debug, дамп environment или содержимое kubeconfig/ключа.
Version stdout разрешён как данные версии; нефильтрованные ошибки доступа не публиковать.
Version-вызов дополнительный к максимум19 вызовам collector; это не проверка здоровья всех ресурсов.
При неожиданном host/user/version, отсутствии доступа, таймауте или несовпадении хэшей STOP.
Не устанавливать пакеты, не менять сервисы и не добавлять диагностические Kubernetes-чтения.

Создай новый remote каталог mktemp -d /tmp/p8c-podlist-20261102-XXXXXXXX, umask077/mode700.
Передай SCP ровно followup.py и supplemental.py, mode600. Не клонировать Git на узле.
Разрешены только shell builtins, mktemp/mkdir/chmod в НОВОМ run-каталоге, sha256sum, date,
локальное создание метаданных/контрольных сумм, cat только перечисленных result-файлов и SCP возврат файлов. Системные файлы не менять.
Задай P8C_APPROVED_BUNDLE_DIR полным путём нового каталога; SHA256 на узле проверяет блок G3.
Задай P8C_GATE_SHA фактическим полным commit SHA, впервые добавившим ЭТОТ gate.
До G3 проверь наличие сохранённых preflight.txt и hash-check-local.txt на стороне Hermes.
Kubeconfig остаётся только на node-01.

## G3 — один процесс followup.py

Фиксированные чтения collector (все с context выше, --request-timeout=15s):

| ID | argv tail / literal API path | Зависимости |
|---|---|---|
| F-D1 | get --raw /apis/crd.projectcalico.org/v1 | нет |
| F-I1 | get --raw /api/v1/namespaces/kube-system/pods?labelSelector=k8s-app%3Dcalico-node&limit=200 | нет |
| F-CS | get --raw /apis/apiextensions.k8s.io/v1/customresourcedefinitions/clusternetworkpolicies.policy.networking.k8s.io | нет |
| F-CNP | get --raw /apis/policy.networking.k8s.io/v1alpha2/clusternetworkpolicies | F-CS compatible |
| F-NP | get --raw /apis/crd.projectcalico.org/v1/networkpolicies | D1:networkpolicies + F-I1 |
| F-GNP | get --raw /apis/crd.projectcalico.org/v1/globalnetworkpolicies | D1:globalnetworkpolicies + F-I1 |
| F-FELIX | get --raw /apis/crd.projectcalico.org/v1/felixconfigurations/default | D1:felixconfigurations + F-I1 |
| F-HEP | get --raw /apis/crd.projectcalico.org/v1/hostendpoints | D1:hostendpoints + F-I1 |
| F-TIER | get --raw /apis/crd.projectcalico.org/v1/tiers | D1:tiers + F-I1 |

F-I1 — один запрос, limit200, без перехода по continue. Неполный/overlong/invalid identity
блокирует пять потребителей. Нельзя руками дочитывать или ослаблять image/schema guard.
Пять policy list-чтений: limit200/200/100, максимум3 страницы и500 объектов КАЖДОГО списка.
Всего максимум19 kubectl subprocess-вызовов collector. Это не гарантия точного числа HTTP
обменов клиента. Каждый subprocess имеет timeout20s; API-request timeout15s.
F-CS принимает только нормализованный spec hash
ff433d3463dfa2264a7a3ff6201baabf1ec789e98664aff3401a7ef79ae7ce5e.
F-I1 использует принятый typed-PodList adapter и finite itemDiag; не менять скрипт на узле.
Диагностика указывает класс отказа, а не раскрывает raw values.

Выполни блок ниже ровно один раз на node-01 (Bash):
```bash
(
set -euo pipefail
umask 077
: "${P8C_APPROVED_BUNDLE_DIR:?Set the fresh remote bundle path}"
: "${P8C_GATE_SHA:?Set the full published gate commit}"
[[ "$P8C_GATE_SHA" =~ ^[0-9a-f]{40}$ ]]
cd "$P8C_APPROVED_BUNDLE_DIR"
test "$(hostname -s)" = node-01
test "$(id -un)" = root
test ! -e followup-output
test ! -e run-meta.txt
test ! -e SHA256SUMS.result
test ! -e RUN_STARTED
test ! -e hash-check.txt
printf 'HASH_CHECK_START_UTC=%s\nCOMMAND=sha256sum --check\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > hash-check.txt
if sha256sum --check >> hash-check.txt 2>&1 <<'SUMS'
8e01355087db65d3c124f0a21ac5a4dd89acf0caaabc092836d469169fe57a7b  followup.py
ddd9a4dc17bca97d6b36ae6b4d501e1722c5d38d6e5ac8c7b051698fa0b15491  supplemental.py
SUMS
then
  P8C_HASH_RC=0
else
  P8C_HASH_RC=$?
fi
printf 'HASH_CHECK_END_UTC=%s\nEXIT_CODE=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$P8C_HASH_RC" >> hash-check.txt
cat hash-check.txt
test "$P8C_HASH_RC" -eq 0
export KUBECONFIG=/etc/kubernetes/admin.conf
set -o noclobber
printf 'GATE_ID=P8C-RV02-PODLIST-ONE-RUN-20261102\nGATE_SHA=%s\nSOURCE_SHA=eed114e2201f75c3235b33779780038f1e8822df\nCONTEXT=kubernetes-admin@pak-portal\nSTART_UTC=%s\n' "$P8C_GATE_SHA" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > run-meta.txt
mkdir RUN_STARTED
set +e
python3 -B followup.py --context kubernetes-admin@pak-portal --output "$P8C_APPROVED_BUNDLE_DIR/followup-output"
P8C_RUN_RC=$?
set -e
printf 'END_UTC=%s\nEXIT_CODE=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$P8C_RUN_RC" >> run-meta.txt
if test -f followup-output/followup.jsonl; then
  sha256sum followup.py supplemental.py followup-output/followup.jsonl run-meta.txt hash-check.txt > SHA256SUMS.result
else
  printf 'OUTPUT_STATUS=ABSENT\n' >> run-meta.txt
  sha256sum followup.py supplemental.py run-meta.txt hash-check.txt > SHA256SUMS.result
fi
exit "$P8C_RUN_RC"
)
```

RUN_STARTED — дополнительная локальная отметка одной попытки; её не удалять и не обходить
новым каталогом ради повторного запуска.
Бюджет расходуется при запуске collector, включая немедленную ошибку.
Если после записи intent/отправки SSH неизвестно, стартовал ли процесс, статус UNKNOWN_OUTCOME:
не повторять. Если известен сбой preflight ДО запуска, NOT_STARTED и STOP.
EXIT1/PARTIAL/UNSUPPORTED/PARSE_ERROR/BLOCKED_NOT_EXECUTED не разрешают повтор.
Разрыв связи не разрешает ни новый запуск, ни ручное выполнение отдельных reads.
Независимые чтения внутри единственного процесса идут по принятому коду.

## G4 — возврат, проверка, reconciliation

Верни только:
1. followup-output/followup.jsonl, если создан;
2. run-meta.txt;
3. SHA256SUMS.result;
4. preflight.txt, hash-check-local.txt, удалённый hash-check.txt с фактическими командами/выводом/UTC/exit;
5. локальный отчёт о GATE_SHA/source/operator/context/фактическом ходе и run-intent.

Существующие файлы результата разрешено забрать после завершения/разрыва связи без повторения
collector. Если результат не получен, честно зафиксировать отсутствие/UNKNOWN_OUTCOME.
Не выдумывать времена или exit. Проверить контрольные суммы после возврата. На стороне Hermes создать SHA256SUMS.evidence
для всех возвращённых файлов и локальных transcripts; удалённый SHA256SUMS.result не менять.
Если transcript утрачен после запуска, честно NOT_AVAILABLE и STOP после доступной reconciliation;
никакие live-проверки не повторять для заполнения пробела.
Не возвращать raw Kubernetes objects, kubeconfig, private keys, passwords, tokens, env или
нефильтрованный stderr. Имена/ключи secret-ref не являются значениями credentials.
Если обнаружена утечка, оригинал оставить приватным, STOP; опубликованный санитизированный
derivative должен иметь явную привязку/hash, а не молчаливую замену исходных байтов.

Проверить JSONL:9 ожидаемых record ID, реальные argv/exit/category/complete/diag/itemDiag,
журнал страниц и количество выполненных/блокированных запросов. Сохранить настоящий aggregate exit.
Различать пустой список, API_NOT_SERVED, FORBIDDEN, TIMEOUT, CONNECTION, PARSE_ERROR,
UNSUPPORTED, PARTIAL и BLOCKED_NOT_EXECUTED. Не превращать exit1 в PASS всего inventory.

Сопоставить наблюдения с14FLOW-ID и текущими gaps; обновить необходимые текущие
flow-matrix/gaps/design conclusions с точными record/page refs. Можно подготовить offline
кандидат rollout-плана, но не менять/применять policy-манифесты этим заданием.
Не выводить traffic direction из declared ports, effective per-node CNI mode из одного default
Felix, полный effective-policy-union только из прочитанного списка.
Не называть EMPTY/OK для непрочитанного или усечённого источника.
Оставшиеся UNKNOWN сформулировать конкретно; не собирать новые данные самостоятельно.

## G5 — публикация и итоговый STOP

Новые evidence и необходимые текущие reconciliation-документы публикуются в main fast-forward,
без force и изменения исторических evidence. Перед push — повторный fetch; чужие изменения
не затирать. Зафиксировать source SHA отдельно от evidence/final remote SHA; readback проверки.

Итог:
```text
GATE_ID / GATE_SHA
RECOVERY_MAIN_SHA
ACCEPTED_SOURCE_SHA
SCRIPT_BLOBS / SCRIPT_SHA256
ACCESS_PATH / HOST_KEY_FINGERPRINT / KEY_ONLY_AUTH
START_UTC / END_UTC / EXIT_CODE (или UNKNOWN с причиной)
OUTPUT_SHA256
PREFLIGHT_TRANSCRIPT / LOCAL_HASH_TRANSCRIPT / REMOTE_HASH_TRANSCRIPT
RECORDS_TOTAL / DISPOSITIONS / COLLECTOR_INVOCATIONS
NEW_GATE_RUN_BUDGET=CONSUMED | NOT_STARTED | UNKNOWN_OUTCOME
FLOW_MATRIX_COMPLETE=YES|NO (только по фактам)
REMAINING_UNKNOWNS
FINAL_REMOTE_MAIN_SHA
PHASE2_NEW_RUN_APPROVED=NO (после расходования/STOP)
NETPOL_APPROVED_FOR_APPLY=NO
P8C=NOT_FINAL_ACCEPTED
P8D–P8G/P9=NOT_AUTHORIZED
```

STOP для независимого Architect review после полного результата/reconciliation.
Промежуточные коммиты не требуют нового «продолжай». Не останавливаться после одной лишь
доставки файлов, если preflight прошёл и независимая разрешённая работа остаётся.

## Исключения

Не выполнять: source rework; повтор принятых offline/PG17/Portal/backup/restore/PITR/failover/P7
проверок; standalone supplemental.py или base inventory; registry queries; node-02/03;
BMC/сканирование; изменение доступа/паролей; произвольный kubectl, exec/log/proxy;
Secret/ConfigMap dump; NetworkPolicy apply/rollback; CI release/workflow/token;
реальные provisioning helpers; production migration/deployment; P8D–P8G/P9.
