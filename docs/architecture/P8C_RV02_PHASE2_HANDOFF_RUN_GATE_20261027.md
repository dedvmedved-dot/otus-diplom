# P8C-R1 RV-02 — Architect Gate: Phase-2 handoff / one read-only run

Дата: 2026-10-27, Europe/Moscow.
Репозиторий: dedvmedved-dot/otus-diplom; main — единственный Source of Truth.
Основание: docs/architecture/P8C_RV02_ACCEPTANCE_7970620_20261027.md.
Recovery HEAD, независимо проверенный Connector: d5801bf2c6914c641b92d7ab36818b74cc500ca4.

## Решение Architect

OWNER_PHASE2_HANDOFF_ALLOWED=YES — только закреплённые байты и инструкция этого Gate.
PHASE2_LIVE_READS_APPROVED=YES — ОДИН запуск supplemental.py при выполнении G0/G1 ниже.
Это отдельный допуск, предусмотренный приёмкой d5801bf. В указанной узкой области он
заменяет прежние NO в acceptance/design/header скрипта. Сам скрипт менять не нужно.

NETPOL_APPROVED_FOR_APPLY=NO.
CI/workflow publication/dispatch/token, реальные provisioning helpers,
production migration/deployment и новые интеграции НЕ разрешены.
P8C=NOT_FINAL_ACCEPTED; P8D–P8G/P9=NOT_AUTHORIZED.
Этот документ НЕ означает, что запуск уже выполнен.

## Исполнители — редакция без Hermes2

По уточнению владельца 2026-10-27 Hermes2 исключён из этого задания.
**Основной Hermes** выполняет весь цикл: recovery → извлечение и проверка
закреплённых байтов → защищённая доставка на node-01 → один разрешённый read-only
запуск → получение результатов → проверка/санитизация → evidence/reconciliation в Git.
Отдельная передача задания Hermes2 и ожидание его действий больше не нужны.

Основной Hermes выступает оператором только при наличии уже разрешённого действующего
доступа к node-01 и контексту из G1. Наличие такого доступа этим Gate не утверждается.
Если доступ есть, дополнительное «продолжай» не требуется. Если доступа нет —
BLOCKED_EXTERNAL: указать недостающий разрешённый путь, не подбирать credentials,
не использовать ранее раскрытый пароль, не копировать kubeconfig и не менять доступ.
Владелец может выполнить тот же блок в своей разрешённой сессии без участия Hermes2;
одновременно с Hermes запускать нельзя.

**Architect** независимо проверяет результат и принимает решение по UNKNOWN.
EXIT=0 не открывает NetworkPolicy/CI/production.

Эта редакция меняет только исполнителя. Лимит ОДНОГО запуска общий для исходного Gate
7d140e256d0ac73aabf586112312e5e861188e00 и этой редакции, а не по одному на каждого
оператора. Если предыдущий запуск уже начат, выполнен или имеет неопределённый исход,
не выполнять второй; сначала получить и разобрать существующий результат.
Перед запуском зафиксировать, что исполнителем назначен основной Hermes, Hermes2
не запускает. В run-manifest GATE_SHA указывать полный SHA опубликованной редакции
этого файла без Hermes2; оригинальный Gate сохраняется в истории Git.

## G0 — pinned source и recovery

Читать текущий main через Connector / git fetch; проверить отсутствие неожиданного
изменения допусков или закреплённого файла. При конфликте STOP AND REPORT.
Сохранить локальные незакоммиченные изменения, не выполнять reset/force.
Зафиксировать полный commit SHA именно этого опубликованного Gate как GATE_SHA;
это не SHA d5801bf и не SHA скрипта. При передаче основной Hermes заполняет его из Git.

Единственный разрешённый collector:
- Path: portal/networkpolicy/supplemental.py
- Executable source: b623afb2fa9fd624e3e1ff418adeb9c71b1074df
- Available unchanged at acceptance: d5801bf2c6914c641b92d7ab36818b74cc500ca4
- Git blob: ad2edaa92de59f657599190842fa7fe68373b582
- SHA-256: 69dac4747856e5f88ac4666e884fe1263777ca5cb64b197741a4b370c093aa4c

Из существующего проверенного checkout извлечь через
`git show b623afb2fa9fd624e3e1ff418adeb9c71b1074df:portal/networkpolicy/supplemental.py`
в НОВЫЙ приватный каталог передачи. Не брать изменяемую рабочую копию, не
копировать текст скрипта из чата. Проверить git blob и SHA-256 до передачи, затем
SHA-256 на node-01. Несовпадение → STOP, никакого исправления файла на узле.
Приёмка 33/33 сохраняется, тесты повторять не нужно.

Передать только supplemental.py и опубликованный Gate с полным GATE_SHA.
GitHub-доступ с изолированного node-01 не требуется.
Использовать существующий разрешённый канал через операторский хост; SSH host key
проверять. Не использовать ранее раскрытые пароли, password в argv/чате/Git,
StrictHostKeyChecking=no, BMC или обход доступа. При недоступном действующем входе —
BLOCKED_EXTERNAL; не искать иной доступ.

## G1 — конкретная среда, без перенастройки

Исполнение только в уже разрешённой сессии:
- узел node-01, management IP 192.168.194.38 (не SSH alias);
- контекст kubernetes-admin@pak-portal;
- KUBECONFIG=/etc/kubernetes/admin.conf только на этом узле;
- client/server v1.36.2 (как подтверждено базовым inventory);
- доступные python3 и kubectl; ничего не устанавливать.

Не копировать kubeconfig, токены, SSH-ключи или пароли. Не переключать чужую сессию/
кластер. Полномочия используемого admin context НЕ расширяют разрешённый scope.
Локальные проверки hostname, наличия executable/файла и kubectl version разрешены.
Version-запрос и штатный discovery kubectl для фиксированных core-v1 GET не являются
разрешением на дополнительные объектные чтения.
Другой host/context/version или отсутствие безопасной сессии → STOP до collector.
Закреплённый файл должен лежать в новом каталоге владельца с mode0700; файл mode0600.
Никаких untrusted файлов/ссылок в каталоге запуска.

## G2 — десять записей: точный read-only контракт

Каждый вызов имеет wrapper:
`kubectl --context kubernetes-admin@pak-portal --request-timeout=15s`.
Timeout subprocess внутри скрипта 20s. Разрешены только следующие argv tails:

| ID | argv tail | Условие |
|---|---|---|
| D1 | get --raw /apis/crd.projectcalico.org/v1 | discovery |
| D2 | get --raw /apis/policy.networking.k8s.io/v1alpha2 | discovery |
| I1 | get pods -n kube-system -l k8s-app=calico-node -o json | safe identity projection |
| C1 | get --raw /apis/barmancloud.cnpg.io/v1/namespaces/portal/objectstores/portal-db-backup | named ObjectStore |
| C2 | get --raw /apis/postgresql.cnpg.io/v1/namespaces/portal/clusters/portal-db | named Cluster |
| C3 | get --raw /apis/crd.projectcalico.org/v1/networkpolicies | только D1+I1 accepted |
| C4 | get --raw /apis/crd.projectcalico.org/v1/globalnetworkpolicies | только D1+I1 accepted |
| C5 | get --raw /apis/crd.projectcalico.org/v1/felixconfigurations/default | только D1+I1 accepted |
| S1 | get pods -n portal -l cnpg.io/cluster=portal-db -o json | safe sidecar identity |
| S2 | get pods -n cnpg-system -l app=barman-cloud -o json | safe controller identity |

Не запускать эти команды вручную с сохранением raw-ответов: только закреплённый
скрипт проецирует их в безопасный output. Не добавлять HostEndpoint/Tier, ConfigMap,
Secret, env/args, pod exec/log/proxy, SSH-команды диагностики сети или packet tests.
Не ослаблять identity gate при platform-child/другом digest.

Скрипт сам блокирует зависимые C3/C4/C5, но завершает остальные независимые чтения.
Это разрешено в рамках одного запуска. Unsupported optional API, identity mismatch,
API_NOT_SERVED, FORBIDDEN, TIMEOUT или CONNECTION сохраняются честно. После окончания —
STOP, без автоматического retry, изменения scope/RBAC или установки CRD.

## Команда основного Hermes в операторской сессии (или владельца)

Основной Hermes указывает перед блоком:
`export P8C_GATE_SHA='<ПОЛНЫЙ_SHA_КОММИТА_ЭТОГО_GATE>'`.
Placeholder не исполнять: подставить проверенный 40-символьный SHA из Git.
Из приватного каталога с проверенным supplemental.py выполнить блок ровно один раз.
Он создаёт только локальные evidence-файлы; Kubernetes mutations отсутствуют.
`bash -n` блока проверен Architect; live-запуск Architect НЕ выполнял.

```bash
(
set -eu
umask 077
: "${P8C_GATE_SHA:?Set the full published Architect Gate commit SHA}"
[[ "$P8C_GATE_SHA" =~ ^[0-9a-f]{40}$ ]] || exit 2
test -f ./supplemental.py
test ! -L ./supplemental.py
printf '%s\n' '69dac4747856e5f88ac4666e884fe1263777ca5cb64b197741a4b370c093aa4c  supplemental.py' | sha256sum --check
test "$(hostname -s)" = node-01
command -v python3 >/dev/null
command -v kubectl >/dev/null
test -r /etc/kubernetes/admin.conf
P8C_CTX='kubernetes-admin@pak-portal'
export KUBECONFIG=/etc/kubernetes/admin.conf
P8C_RUN_DIR="$(mktemp -d /tmp/p8c-rv02-phase2.XXXXXXXX)"
printf '%s\n' "$P8C_RUN_DIR"
printf '%s\n' '69dac4747856e5f88ac4666e884fe1263777ca5cb64b197741a4b370c093aa4c  supplemental.py' | sha256sum --check >"$P8C_RUN_DIR/script-check.txt"
if kubectl --context "$P8C_CTX" --request-timeout=15s version -o json >"$P8C_RUN_DIR/version.json" 2>"$P8C_RUN_DIR/version.stderr.local"; then
  :
else
  printf '%s\n' 'PRECHECK_VERSION_FAILED; collector NOT_EXECUTED'
  exit 2
fi
python3 -I - "$P8C_RUN_DIR/version.json" <<'PY'
import json,sys
with open(sys.argv[1]) as f:
    d=json.load(f)
if any(d.get(k,{}).get("gitVersion")!="v1.36.2" for k in ("clientVersion","serverVersion")):
    raise SystemExit("VERSION_MISMATCH; collector NOT_EXECUTED")
PY
{
  printf 'GATE_SHA=%s\n' "$P8C_GATE_SHA"
  printf '%s\n' 'SCRIPT_SOURCE_SHA=b623afb2fa9fd624e3e1ff418adeb9c71b1074df'
  printf '%s\n' 'SCRIPT_GIT_BLOB=ad2edaa92de59f657599190842fa7fe68373b582'
  printf '%s\n' 'SCRIPT_SHA256=69dac4747856e5f88ac4666e884fe1263777ca5cb64b197741a4b370c093aa4c'
  printf 'CONTEXT=%s\n' "$P8C_CTX"
  printf '%s\n' 'HOST=node-01'
  python3 --version
  printf 'START_UTC=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
} >"$P8C_RUN_DIR/run-manifest.txt"
if python3 -I ./supplemental.py --context "$P8C_CTX" --output "$P8C_RUN_DIR/result" >"$P8C_RUN_DIR/collector.stdout.local" 2>"$P8C_RUN_DIR/collector.stderr.local"; then
  P8C_RC=0
else
  P8C_RC=$?
fi
{
  printf 'END_UTC=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf 'INVENTORY_EXIT_CODE=%s\n' "$P8C_RC"
} >>"$P8C_RUN_DIR/run-manifest.txt"
(
  cd "$P8C_RUN_DIR"
  if test -f result/supplemental.jsonl; then
    sha256sum result/supplemental.jsonl version.json script-check.txt run-manifest.txt >SHA256SUMS
  else
    sha256sum version.json script-check.txt run-manifest.txt >SHA256SUMS
  fi
)
printf 'INVENTORY_EXIT_CODE=%s\nARTIFACT_DIR=%s\n' "$P8C_RC" "$P8C_RUN_DIR"
exit "$P8C_RC"
)

```

Не оборачивать блок в повторяющийся job/цикл или команду, скрывающую exit code.
Если precheck завершился раньше collector, сообщить NOT_EXECUTED и причину.
Если collector прерван/упал или JSONL неполон — сохранить частичный результат;
не повторять запуск без нового адресного решения.
Локальные *.local stdout/stderr не пересылать и не коммитить.

## G3 — результат и безопасное получение основным Hermes

Перед передачей проверить содержимое, не только совпадение слов:
JSONL может содержать **имена/ключи ссылок** на Secret и имена CA; это разрешённые
метаданные, не значения секретов. Недопустимы значения паролей/токенов, private keys,
Bearer headers, URL userinfo/query/fragment, env/args/raw Pod specs.
Если обнаружено неожиданное содержимое — STOP передачи/Git, сохранить оригинал
локально с ограниченным доступом; вернуть только категорию проблемы. Не скрывать
редакцию под прежним checksum.

Вернуть по существующему защищённому каналу:
1. result/supplemental.jsonl (если создан; без ручного «исправления» результатов);
2. SHA256SUMS;
3. script-check.txt;
4. run-manifest.txt: Gate/source/blob/SHA256, context, host, Python, UTC start/end, exit;
5. version.json: client/server из того же контекста.
Если результат частичный, вернуть доступные безопасные файлы и точное ограничение.
Не передавать credential-файлы, kubeconfig или *.local.

SHA256SUMS проверяется перед передачей и после получения. После полного цикла скрипта
ожидаются десять записей D1,D2,I1,C1,C2,C3,C4,C5,S1,S2; blocked rows не являются
пустыми успешными списками. EXIT=1 не переименовывать в PASS.
Ни EXIT=0, ни десять строк сами по себе не означают FLOW_MATRIX_COMPLETE.

## G4 — основной Hermes после выполнения/получения, без нового «продолжай»

- Проверить Gate/source/hash, timestamp interval, context/version, SHA256SUMS,
  JSONL shape, десять IDs/argv/dependencies/категории и отсутствие секретных значений.
- Отличать [] от NOT_SERVED/FORBIDDEN/TIMEOUT/UNSUPPORTED/BLOCKED; сохранить исходный
  exit. Неполноту и runtime digest incompatibility описывать точно, не «чинить» gate.
- Сопоставить новые факты с 14 FLOW-ID и текущими gaps; сослаться на конкретные записи.
  Для effective mode, HostEndpoint/Tier, DNAT и фактического трафика оставить UNKNOWN,
  если данный пакет их не доказывает. Не обещать закрытие всех gaps этим запуском.
- Добавить только НОВЫЙ каталог evidence/P8/<UTC>-p8c-rv02-phase2-live/ и адресные
  обновления flow-matrix/gaps/collection-map/PLAN при наличии доказательств.
  Исторические base/evidence, source/tests/policy YAML не менять.
- Publish fast-forward без force, проверить remote HEAD и diff scope.
  STOP с полным SHA, краткой reconciliation и оставшимися UNKNOWN для Architect.

Не повторять base inventory, PG17/Portal/backup/restore/PITR/failover/P7 tests.
Не выполнять NetworkPolicy apply/rollback, CI release/workflow/token, Owner helpers,
production migrations/deployment. Эта задача заканчивается evidence и review.

## Итоговые поля отчёта

GATE_SHA; RECOVERY_MAIN_SHA; SCRIPT_SOURCE_SHA; SCRIPT_GIT_BLOB; SCRIPT_SHA256;
ACCESS_PATH (без credentials); START_UTC; END_UTC; INVENTORY_EXIT_CODE;
RECORDS_TOTAL; OK/UNSUPPORTED/API_NOT_SERVED/FORBIDDEN/TIMEOUT/CONNECTION/
PARSE_ERROR/GET_FAILED/BLOCKED_NOT_EXECUTED counts;
OUTPUT_SHA256; PHASE2_RESULT (EXECUTED/PARTIAL/BLOCKED_EXTERNAL);
FLOW_MATRIX_COMPLETE (только по доказательствам); REMAINING_UNKNOWNS;
FINAL_REMOTE_MAIN_SHA; NETPOL_APPROVED_FOR_APPLY=NO; P8C=NOT_FINAL_ACCEPTED.

Допуск одноразовый. После исполнения/неопределённого исхода он считается использованным;
новые reads, повторный run и дальнейшие gates требуют отдельного решения.
