# TASK: P8C-R1 RESUME-R3 — RV-02 live inventory closure

Дата: 2026-10-25, Europe/Moscow.
Исполнитель: Hermes. Проверяющий: Architect.
Статус: AUTHORIZED READ-ONLY INVENTORY / SOURCE PREPARATION.
Это продолжение RESUME-R3, не новый этап и не допуск к развёртыванию.

## 1. Цель и принятое состояние

Закрыть оставшийся RV-02: собрать проверяемые факты о существующих сетевых зависимостях, согласовать PLAN/кандидат NetworkPolicy/offline tests и передать один пакет на Architect review.

GitHub main в dedvmedved-dot/otus-diplom — единственный Source of Truth.
Перед публикацией этого задания Connector подтвердил:
- main: a8e32cb63cda50e06cc3133c51f8f3648ce1a888;
- application source: 817f0ecef8da1cd756f4b6ab48d61e023764329a;
- после application source изменялось только новое evidence;
- native PostgreSQL 17 evidence дополнено и замечание к его проверяемости закрыто: 12/12 PASS = 10 DB integration + 2 TLS/config, PostgreSQL 17.11, Go1.27.3, UTC/exit0. Это review опубликованного прогона Hermes, не независимое исполнение на его хосте.

Native PG17, полный build/vet/test/race, UI/OpenAPI и ранее принятый coherent snapshot повторно не открывать. Новые проверки — только по фактически изменённому scope и конкретным рискам.

P8C=IN_PROGRESS/NOT_FINAL_ACCEPTED.
P8D–P8G/P9=NOT_AUTHORIZED.
CI release, Owner helpers, live policies, production migration/deployment НЕ разрешены.

## 2. G0 — recovery и точная исходная ревизия

Самостоятельно проверить remote main, текущий HEAD, последние commits, локальные изменения и delta от a8e32cb. Документ с этим заданием является ожидаемым новым commit; не требовать HEAD=a8e32cb после его публикации.
Не сбрасывать чужие изменения. Неожиданное изменение application source/контрактов или конфликт с заданием → STOP с точным delta.

Прочитать:
- docs/architecture/P8C_R3_REVIEW_618d677_20261021.md целиком;
- docs/tasks/TASK_P8C_R1_RESUME_R3_CLOSURE_EXECUTION.md;
- portal/networkpolicy/PLAN.md;
- portal/networkpolicy/inventory.py;
- portal/networkpolicy/flows_test.go;
- portal/manifests/networkpolicy.yaml;
- фактические Deployment, migration Job, Gateway/HTTPRoute manifests в portal/manifests;
- evidence/P8/20261021-p8c-r3-independent-source/result.md и closure-matrix.md;
- evidence/P8/20261024T112600Z-task-p8c-r1-resume-r3-native-pg17/supplementary-verifiability.txt.

Зафиксировать RECOVERY_MAIN_SHA и SHA каждого исполняемого inventory/helper файла. Исторические evidence не редактировать.

## 3. G1 — разрешённый путь доступа

Использовать только уже разрешённую сессию/идентичность:
A. существующий локальный kube-context Hermes, если он появился;
B. существующую разрешённую рабочую сессию на узле/jump host с kubectl;
C. выполнение подготовленного read-only пакета оператором в его существующей сессии, с возвратом только проверенных несекретных результатов.

Не копировать admin.conf на Hermes-хост как обязательное условие. Контекст/credential остаются на разрешённой стороне. Не просить пароли, private keys, токены или kubeconfig через чат/Git/evidence; workflow token не использовать.

Разрешено проверить наличие клиента и имена существующих контекстов без печати credential content. Не выводить kubectl config view --raw, env, конфиги SSH/VPN целиком или файлы секретов. Если клиент отсутствует, это не повод создавать новые доступы: предпочтителен вариант B/C. Для запуска на уже разрешённом локальном рабочем хосте допустима установка отдельного kubectl binary в рабочую папку после проверки официального источника, версии и checksum; никаких изменений ОС/сервисов/прав доступа.

Запрещено самостоятельно выдавать RBAC, создавать ServiceAccount/token/kubeconfig, менять VPN/routes/firewall/SSH/authorized_keys, подбирать учётные данные, сканировать подсети, обращаться к BMC/SOL/IPMI как обходу. Наличие доступного TCP/22 не даёт авторизацию на вход. Timeout означает timeout, не доказанный closed.

Если пути A/B/C сейчас нет:
- не повторять известные сетевые пробы в цикле;
- завершить независимую подготовку безопасного inventory/операторского handoff и offline checks;
- сформировать один конкретный запрос владельцу: выполнить read-only пакет из существующей разрешённой сессии либо предоставить такую сессию обычным защищённым механизмом;
- итог BLOCKED_EXTERNAL с точным отсутствующим условием. Не запрашивать новое «продолжай» для уже разрешённой подготовки.

## 4. G2 — безопасный сбор фактов

Базовая команда из корня проверенного checkout (параметры заменить фактическими локальными значениями):

    python3 portal/networkpolicy/inventory.py --context "<approved-context>" --output "<new-local-inventory-directory>"

Новый output directory не должен существовать заранее; не перезаписывать прежний журнал. Запускать в разрешённой сессии, не внутри Portal и не через production Pod exec.

Скрипт — отправная точка, а не доказательство полноты. До живого запуска проверить вывод:
- сохранять только нужные поля identity/namespace/labels/ports/selectors/endpoints/status;
- исключать Secret data, env/valueFrom, credentials, TLS private keys, полные Pod specs, managedFields и произвольные annotations/last-applied;
- для Gateway/EnvoyProxy/NetworkPolicy вместо небезопасного полного объекта при необходимости сделать allowlist-проекцию нужных полей;
- чувствительные endpoint URL очищать от userinfo/query, сохраняя host/port, нужные для flow;
- ошибки фиксировать безопасными категориями и кодами, без credential-bearing traceback.

Допускаются адресные изменения inventory.py и его offline/mock tests, необходимые для этого задания. Сбор — только GET/LIST/discovery. Никаких exec/proxy/debug/port-forward/POST, временных Pod/Job и mutation даже через server-side dry-run.

Для каждой команды: UTC start/end, точный безопасный argv, exit, projected stdout или безопасная категория ошибки. Различать API_NOT_SERVED, FORBIDDEN, TIMEOUT и EMPTY_SUCCESS: ошибка не доказывает отсутствие ресурса. Не переписывать command/time задним числом.

Обязательные факты:
1. Все namespace labels и workload identities, которые могут затронуть proposed policies; existing NetworkPolicy union и применимые CNI-specific policy objects, если served.
2. CNPG portal-db peers, operator и Barman plugin: namespace, labels, Services/targetPorts/EndpointSlices, ports, ready state.
3. DNS: фактическая цепочка Service → endpoints → pods, TCP/UDP; NodeLocalDNS/hostNetwork учитывать только если обнаружены.
4. Kubernetes API: default/kubernetes Service/EndpointSlices, фактические API destinations, тип/версия CNI, proxy/replacement mode, enforcement point относительно DNAT. Без dump полного CNI конфигурационного файла: только разрешённые несекретные поля.
5. Monitoring: discovery ServiceMonitor/PodMonitor, фактические selectors/namespaces/ports и scrape workload identities. Не ограничиваться CRD: проверить уже настроенные альтернативные scrapers по существующей конфигурации. «Monitoring отсутствует» допустимо только с областью и доказательством проверки.
6. S3/Barman: sanitized ObjectStore endpoint, используемый протокол/порт и доступные разрешённые routing facts. Velero domain учитывать отдельно, не смешивать его credentials/backup path с Barman.
7. Envoy: GatewayClass/controller/EnvoyProxy, фактические dataplane namespace и labels, owning-gateway-name И owning-gateway-namespace, xDS/listener/backend/DNS dependencies.
8. Read-only baseline: nodes Ready, CNPG instances/conditions/archiving, Velero BSL, существующие Gateway conditions. Это статусные GET, не повтор квалификационных backup/failover tests.

Если Portal Gateway/dataplane ещё не созданы, пометить NOT_CREATED_EXPECTED. Не создавать их ради inventory. Будущие зависимости выводить из фактического controller baseline + versioned candidate manifests и помечать PLANNED; фактические labels/endpoints будущих объектов проверяются в отдельном deployment gate.

## 5. G3 — полная матрица потоков

Создать flow-matrix.md/CSV с устойчивым FLOW-ID. Для каждой строки:
source namespace+labels/identity → destination namespace+labels/IP/Service →
protocol/port/service targetPort → direction/purpose →
raw evidence file+record/command/time →
proof type (OBSERVED_CONFIG / OBSERVED_STATUS / VERSIONED_DESIGN / UNKNOWN) →
CNI/DNAT assumption and justification →
matching ingress AND egress policy/правило либо явно доказанная неизолированная сторона.

Обязательные группы: replication, instance-manager, operator, Barman plugin, monitoring, DNS, API, S3, Portal5432/9187, migrator5432, Envoy xDS/backend/listener. Проверять все существующие workloads, которые изолирует namespace-wide baseline, а не только новые Portal pods.

Отдельно закрыть известные неопределённости:
- Barman controller находится в cnpg-system по исходному manifest; declared9090 не доказывает направление или наличие трафика. Проверить фактическую plugin/service configuration. Не оставлять controller→DB5432 только потому, что так написано в старом candidate.
- API /24:6443 не считать согласованным. Определить необходимые destinations по фактической Service/DNAT/CNI модели; не заменять вслепую на /32 и не расширять CIDR.
- проверить DNS/monitoring/operator потоки и обе стороны additive policies;
- Gateway ownership требует name+namespace, не только name.

Первичные документы CNI/CNPG/Envoy применимы только к обнаруженной версии/режиму. Ссылаться на конкретный источник и конфигурационные факты; не объявлять документальную реконструкцию packet capture. Не запускать tcpdump/active traffic/failure tests ради закрытия неизвестности. Если без нового привилегированного действия доказательств недостаточно, оставить конкретный UNKNOWN/BLOCKED и закончить независимые строки.

## 6. G4 — согласованный source candidate и адресные тесты

На основе доказанных фактов обновить:
- portal/networkpolicy/PLAN.md;
- portal/manifests/networkpolicy.yaml;
- portal/networkpolicy/flows_test.go;
- inventory helper/tests при необходимости.

Убрать противоречия PLAN/YAML/matrix, необоснованные лишние разрешения и ложные FULL/VERIFIED claims. Не добавлять blanket allow-all или расширять scope Portal. Статус manifests остаётся NOT_APPROVED_FOR_APPLY до отдельного Architect решения.

Тесты должны использовать фактические sanitized fixture labels/ports и проверять:
- положительные required flows;
- отрицательные wrong namespace/owner/name/port/protocol и unrelated client;
- обе стороны policy union, namespace-wide defaults, existing policies/CNI constraints в пределах моделируемой семантики;
- migrator без API/S3, Portal без BMC/SSH/arbitrary mutation;
- Deployment/Job/Gateway selectors соответствуют versioned manifests;
- helpers fail-closed, safe projection и различение missing API/forbidden/empty.
Неподдерживаемую CNI семантику не объявлять проверенной обычным Kubernetes-policy evaluator.

Минимальный Go прогон из portal:
    GOTOOLCHAIN=local go test -count=1 -v ./networkpolicy

Для изменений Python — адресные mock tests. NativePG/full build/race/UI suites не повторять, если application source не изменён и новой зависимости от него нет. Изменения backend/UI/DB/RBAC не входят в это задание; обнаруженный дефект документировать для review.

PLAN должен описывать будущий D1 rollout/postchecks/rollback: inventory всех затронутых identities; полный allowlist CNPG до namespace baseline; stop при конфликте существующих names; rollback только UID объектов будущего rollout, не существующих policies. Ничего из этого сейчас не выполнять.

## 7. Evidence, статусы и Git

Новая папка evidence/P8/<UTC>-task-p8c-r1-rv02-live-inventory/:
- result.md;
- recovery.txt (source/worktree state, diff scope);
- access-path.md (разрешённая роль/путь без credentials либо конкретный blocker);
- inventory.jsonl + safe supplementary command outputs;
- flow-matrix.md и gaps.md;
- requirement→manifest/rule→test→evidence matrix;
- exact source/script hashes, actual test logs/versions/UTC/exits;
- secret-scan result с областью/методом/ограничениями;
- operator-handoff.md, если сбор переносится в существующую сессию оператора: exact reviewed script SHA, параметры/команда, безопасный способ возврата и список исключаемых данных.

Разрешённый Git scope: portal/networkpolicy/**, portal/manifests/networkpolicy.yaml, только новое evidence. Прочие изменения — STOP для scope review. Исторические evidence immutable. Не сохранять private keys/пароли/токены/kubeconfig/полные конфиги или их зашифрованные копии в Git.

Перед push проверить diff и remote head. Только fast-forward, без force/rebase опубликованной истории. При новом remote commit исследовать delta и сохранить чужую работу. После публикации проверить remote SHA, файл-состав и source/evidence separation. Если исправлялись policies/helper, явно указать новый source SHA; application runtime source 817f0ece сохраняется.

Промежуточные коммиты допустимы и не требуют нового разрешения. SOURCE_WORK=IN_PROGRESS/PARTIAL до готовности пакета. PASS — только выполненным конкретным проверкам.

## 8. Acceptance и STOP

Пакет READY_FOR_ARCHITECT_REVIEW только если:
- есть разрешённый источник inventory и безопасные raw records;
- все необходимые existing-flow строки доказаны, UNKNOWN не скрыты;
- PLAN/manifests/tests согласованы; future Portal объекты честно PLANNED;
- адресные проверки пройдены, нет секретов, Git delta соответствует scope.
Это не FINAL_ACCEPTED и не право apply.

Если доступ или существенный факт получить невозможно в разрешённом scope — закончить независимую подготовку и STOP/BLOCKED_EXTERNAL с точным недостающим действием владельца. Не выдавать повторный отчёт только о том, что kubectl всё ещё отсутствует; предоставить готовый операторский пакет.

Итоговый отчёт:
RECOVERY_MAIN_SHA
FINAL_SOURCE_SHA
FINAL_REMOTE_MAIN_SHA
APPLICATION_RUNTIME_SOURCE_UNCHANGED
NATIVE_PG17_EVIDENCE=ACCEPTED_PREVIOUSLY_NOT_RERUN
ACCESS_PATH / NETPOL_LIVE_INVENTORY
FLOW_MATRIX_COMPLETE (YES/NO + точные gaps)
OFFLINE_FLOW_TESTS
SECRET_SCAN
NETPOL_PACKAGE_REVIEW_READY
NETPOL_APPROVED_FOR_APPLY=NO
CI_RELEASE=NOT_EXECUTED
OWNER_HELPERS=NOT_EXECUTED
PRODUCTION_MIGRATION_DEPLOYMENT=NOT_EXECUTED
P8C=NOT_FINAL_ACCEPTED
P8D–P8G/P9=NOT_AUTHORIZED

Backup/base backup/latest restore/PITR/P8A failover/P7/P7C failure tests не повторять.
После итогового reviewable package или доказанного внешнего blocker — STOP для Architect review.
