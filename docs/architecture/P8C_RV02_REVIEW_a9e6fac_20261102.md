# P8C RV-02 — review a9e6fac и задание OD-01…05
Дата: 2026-11-02 (Europe/Moscow).
Исполнитель исправлений: основной Hermes. Hermes2 не участвует.

## Решение Architect
REVIEW_HEAD=a9e6facda8988a694722b436526ed2ed844ce41b
PARENT=3ee0ca08b43fd1d1cbf8ca1311e7095ad15a588d
OFFLINE_ROLLOUT_DECISION=PARTIAL / REWORK_REQUIRED
AUTHORIZED_READ_SET_COMPLETE=YES (принятые 9/9, c872eed)
COLLECTOR_SOURCE_REWORK_REQUIRED=NO
COLLECTOR_RERUN_REQUIRED=NO
PHASE2_NEW_RUN_APPROVED=NO
NETPOL_APPROVED_FOR_APPLY=NO
CI_RELEASE / WORKFLOW / OWNER_HELPERS / PRODUCTION=NOT_AUTHORIZED
P8C=NOT_FINAL_ACCEPTED; P8D–P8G/P9=NOT_AUTHORIZED

Connector подтвердил ровно один fast-forward commit, два документальных изменения.
Сбор 9/9, immutable identity, MI/LC и весь принятый source остаются закрыты.
Приняты: разделение EXISTING/PLANNED, охват 14 FLOW-ID, запрет apply и сохранение
исторических evidence, требование UID-ограниченного rollback и актуализации stale-фактов.
План пока не достаточен для допуска. Ни PR-1, ни PR-2 этим review не разрешаются.

## Проверенные источники
Все repository paths ниже прочитаны в REVIEW_HEAD, а не взяты из памяти:
- План: docs/architecture/P8C_RV02_OFFLINE_ROLLOUT_DECISION_20261102.md,
  blob 97caa5ed2a4f7e82821dd10825f9e1e543583a41.
- ansible/playbooks/files/calico-v3.32.0.yaml,
  blob 21ea9b4b163305ea479bc7708965104465ffc716.
- portal/manifests/networkpolicy.yaml, blob fccb8432135a18f8b7099e131471a48808df1ed7.
- portal/manifests/gateway.yaml, blob 1e1f48a3c6d03c4558f4b4c3cca24bc12c22b763.
- portal/manifests/deployment.yaml, blob 2cb27165330fe4b6772af3a06a1940d661efc72f.
- manifests/envoy-gateway/p6c-envoy-gateway-values.yaml,
  blob 6b1ea60d8e4120016f5675771c46f92f96dadc0e: версия Envoy Gateway 1.9.1.
- portal/networkpolicy/supplemental-design.md,
  blob a4de674f9b98f7ecc2dc063db15ccfca7195484b: закреплённые Barman-роли,
  Felix precedence, пределы DNAT и surveyed monitoring.
- P7 evidence:
  evidence/P7/20261019T030033Z-task-p7c-b2-r1-dns1-coredns-resume/15-dns-after-demo-pak.txt,
  blob 89cd2fe653f09924ede7adcd4a90bbaf515211cc;
  в том же каталоге 16-bind-authority-check.txt,
  blob 680e504cf1027789d124e8c8bf7b29121e24a23e.
  evidence/P7/20261019T113205Z-task-p7c-b2-r2-canonical-reproducibility-closure/09-live-dns-s3-contract.txt,
  blob 078398f07263bae41e1f824b609edc7bd03ec24b.
- Kubernetes 1.36, Network Policies:
  https://v1-36.docs.kubernetes.io/docs/concepts/services-networking/network-policies/
  sections Two sorts of pod isolation, ipBlock, Behavior of to and from selectors.
  Isolation follows policy selection and policyTypes; address rewrite order is
  implementation-dependent. Не закреплять правило порядка NAT по одному названию backend.

Независимое локальное извлечение YAML-схем/объектов: exit=0,
evidence/P8/20261102-p8c-rv02-a9e6fac-review/source-facts.json.
Это статическая проверка фактов, не runtime/network test. SSH/cluster не использовались.

## OD-01 — B1/PR-1 не получает требуемого факта
В закреплённой CRD CalicoNodeStatus status имеет agent, bgp, lastUpdated, routes;
agent содержит birdV4/birdV6. Полей активного iptables/nftables/eBPF/DSR backend
и точки NetworkPolicy/DNAT в этой схеме нет. PR-1 не может закрыть заявленную цель.
Кроме того, list без лимитов/пагинации и разрешение произвольного status не являются
готовым ограниченным контрактом чтения.

Убрать PR-1 как способ закрыть B1. Убрать недоказанное обобщение
«iptables/nftables = ClusterIP pre-DNAT». В самом плане есть противоречие:
B1 зависит от effective mode, а ниже per-node mode объявлен не влияющим на правила.
Разрешить противоречие, не назначая автоматически новые чтения.

Разделить API Service tuple и endpoint tuple, DNS pod/namespace selectors и IP-представление.
API VIP не смешивать с backend endpoints; /24 не принимать по умолчанию вместо точных
адресов. Дать версионное доказательство выбранного представления либо анализ ограниченного
варианта, устойчивого к необходимым представлениям, с точными адресами/портами и объяснением
предела дополнительных разрешений. Это кандидат решения, не разрешение broad allowlist.
Если без свежего факта решение невозможно — указать конкретное существующее поле,
его источник/версию и что оно докажет/не докажет. Не подменять факт конфигурации
доказательством фактической обработки пакета.

Критерий закрытия: аргумент правила проверяем по источнику; PR-1 удалён/отклонён;
нет вымышленных полей, противоречий и необоснованного назначения live-сбора.

## OD-02 — B2/PR-2: повторное открытие известных фактов и неверный способ доказательства
P7 evidence уже фиксирует s3-backup.demo-pak.test → 172.30.143.10 через CoreDNS и BIND,
а также принятый POD_DNS_TO_S3/POD_TO_S3_PATH. Это исторические факты с ограниченным
сроком актуальности, не сегодняшнее доказательство из каждого CNPG Pod.
Использовать их вместо общего «резолюция неизвестна» и ссылки на неназванную BIND-зону.

IPPool содержит конфигурацию CIDR/инкапсуляции/NAT/выбора узлов; в закреплённой CRD нет
status с измерением S3-достижимости или роли инициатора трафика. DNS-запрос с node-01
проверяет только соответствующий resolver/network path, не путь CNPG sidecar.
PR-2 не закрывает весь сформулированный B2.

Разделить: historical resolution; current freshness; role/direction from versioned Barman
design; actual connectivity. Не требовать повторного backup/WAL/restore для этих пунктов.
Разложить control operator→plugin:9090 (cnpg-system) отдельно от CNPG-pod/sidecar→S3;
не добавлять control-9090 в CNPG-pod policy без доказанного инициатора именно в этом Pod.
Не выводить controller→S3/DB из наличия сервиса. Дополнительное чтение IPPool оставить
только если конкретное поле реально меняет кандидат правила; иначе исключить.
Любой необходимый DNS proposal: resolver, qname/type, source, таймаут/число попыток,
allowlisted output, errors, предел вывода. Никакого исполнения.

Критерий закрытия: сохранены ранее принятые P7/P8 факты, freshness отделён от отсутствия
доказательства, каждое предложенное действие отвечает только на достижимый им вопрос.

## OD-03 — B3 оставлен вместо исполнения offline-задачи
Gateway YAML уже задаёт portal.demo-pak.test, HTTPS443, TLS Terminate,
certificateRef portal-ui-tls и HTTPRoute→Service portal:80; Deployment задаёт http8080.
Завершить дизайн на этой основе сейчас, не запрашивать отдельное разрешение на описание.

Нужны точные namespace+label keys/values обоих концов, логический listener и фактический
генерируемый service targetPort/Envoy port по закреплённому Envoy Gateway 1.9.1
(не считать listener443 автоматически container443), exposure/LB/source-address модель,
owning-gateway-name+namespace, xDS/DNS/backend, probes и граница management8081.
Отделить kubelet probes, возможные LB health checks и активный backend health check;
не придумывать активный health-check ресурс, если его нет в принятой конфигурации.
Факты generated-runtime, которых ещё нет, пометить PLANNED с точным будущим precheck.

В текущем candidate p8c-portal-dataplane-flows policyTypes=[Egress]; ingress этим объектом
не ограничен. Явно отразить это в design/delta; не описывать его как готовое ingress-правило.
Указать необходимость будущего решения без изменения YAML в этом задании.
Никакого namespace-wide deny для envoy-gateway-system.

Критерий закрытия: B3 решён документально; остаток — именованные будущие deployment
проверки, а не незавершённый дизайн «listener не смоделирован».

## OD-04 — первая policy уже изолирует CNPG; rollback должен учитывать union
p8c-cnpg-existing-flows выбирает CNPG Pods и содержит policyTypes=[Ingress,Egress].
При применении CNI она уже изолирует их по обоим направлениям. Формулировка
«первым и до любой изоляции» неверна: полный allowlist и preconditions нужны ДО этого шага.
Изоляция не откладывается до baseline-default-deny-all.

Описать состояние и разрешения после каждого шага, включая другие существующие Pod
в namespace portal. Удаление только cnpg allow-policy при оставшемся default-deny
может оставить CNPG без нужных разрешений. Нужна явная безопасная последовательность
rollback для каждого достигнутого шага, а не только общее «удалять новые UID».
Сохранять независимый operator management path; не рассчитывать на сам Portal.

Для каждого нового объекта — отсутствие до rollout, записанный UID после создания,
повторная сверка + UID precondition операции удаления в будущем execute-gate; при
несовпадении STOP, без удаления чужого объекта. Изложить порядок снятия ограничивающих
новых политик и последующего удаления allow-правил, с восстановлением исходного
состояния; существующие политики/нагрузки не затрагивать. Не выдавать удаление сейчас.

Задать наблюдаемые pre/post checks с command/field/time-window/timeout/STOP/rollback.
Ready3/3 и LastBackupSucceeded=True сами по себе не доказывают текущую DNS/API/S3
доступность после изоляции. Учитывать свежесть/reconcile/естественный ход WAL, не запускать
новый backup/restore/PITR/failover или destructive probes. Где проверка требует отдельного
runtime-допуска, включить её в будущий proposal, не исполнять.

Критерий закрытия: безопасное состояние и rollback определены для всех четырёх стадий,
нет ложного «allow-policy не изолирует» и ловушки оставшегося default-deny.

## OD-05 — точная трассируемость, candidate delta и сохранение ограничений
14 строк присутствуют, но сокращения «portal: pak-portal», «external», «controller» —
не точные selectors. PLANNED не означает автоматически non-blocking.
MON-9187 остаётся NOT_FOUND_IN_SURVEYED_SOURCES, не доказанным отсутствием любого scraper.
Строку «memory / repo» заменить конкретным файлом/blob/фактом либо убрать.
F-NP явно назвать Calico NP; K8s NetworkPolicy — другой GVR/другая дата.

Добавить по каждой строке: namespace, selector key/value или обоснованный адрес,
направление и обе стороны policy enforcement, порт до/после Service при необходимости,
источник+commit/blob+record+время, candidate YAML object/rule и необходимый delta.
В candidate YAML всё ещё есть Barman controller→DB5432 и широкое API /24:
не менять YAML, но отметить эти расхождения как NOT_APPROVED и дать проектное решение.
Не заявлять «полное сохранение» со ссылкой на заведомо несогласованный candidate.

Критерий закрытия: 14/14 проверяемы без памяти; все расхождения и границы доказательства
видны в одной таблице; актуальные flow-matrix/PLAN/gaps ссылаются на итоговую редакцию.

## Исполнимое задание основному Hermes
TASK=P8C-RV02-OFFLINE-ROLLOUT-DECISION-R1

1. Recovery main через Connector, прочитать этот review целиком и указанные источники.
2. Закрыть OD-01…05 единым offline-пакетом. Исправлять документы, не collector/S1/app/policy YAML.
   Использовать уже полученные evidence. Допустима проверка официального version-pinned
   исходника для конкретного документального вопроса; без registry/live/SSH.
3. Подготовить окончательную редакцию решения, 14-flow table, candidate delta, state/rollback
   table и минимальный proposal только для оставшихся необходимых свежих фактов.
   Если новое чтение не способно ответить на вопрос, исключить его; не писать новый collector.
4. Проверить все подпункты за один проход. Таблица OD→исправленное место→источник→проверка.
   Для документации достаточно проверяемых извлечений/сопоставлений, без фиктивных unit tests.
5. Новые evidence + текущие docs; fast-forward, без force, historical evidence byte-identical,
   source SHA отдельно от evidence/final SHA; readback. Промежуточные коммиты не требуют
   дополнительного «продолжай». STOP после полного пакета либо конкретного внешнего blocker
   после завершения всей независимой работы.

Запрещено: SSH/cluster/API/DNS-пробы, новые collector bytes, accepted test reruns,
NetworkPolicy apply/rollback, CI/workflow/token, реальные helpers, production migration/deploy,
P8D–P8G/P9. Нового live gate в этом документе нет.
