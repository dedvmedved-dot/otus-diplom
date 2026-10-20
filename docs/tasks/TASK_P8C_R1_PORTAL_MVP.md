# TASK: P8C-R1 PORTAL MVP

TASK_STATUS: PREPARED / NOT DISPATCHED  
TASK_AUTHOR: Chief Architect / ChatGPT  
DATE: 2026-10-20  
REPOSITORY: dedvmedved-dot/otus-diplom  
SOURCE_OF_TRUTH: GitHub main  
AUDITED_BASE: 6e19db29d9da0f9f67c87fd3e1bb3a3320a49702  
SCOPE: P8C only — implementation, safe deployment, functional evidence  
NEXT_STAGES: P8D/P8E/P8F/P8G/P9 NOT AUTHORIZED

## 0. Как использовать это задание

Это законченное техническое задание для Hermes. В текущем Work выполнены только Connector Recovery и архитектурная подготовка. Передача задания на исполнение — отдельное действие Owner; публикация файла не запускает Hermes и не означает, что Портал уже работает.

После явной передачи Owner Hermes выполняет G0–G8 по порядку в пределах P8C. Это внутренние контрольные точки одной задачи; успешное прохождение не разрешает следующую стадию P8D. При любом STOP условии остановить соответствующую операцию, сохранить факты и сообщить BLOCKED. Не продолжать на основании предположений.

Цель: работающая операторская консоль с цепочкой User → Envoy Gateway → Portal UI/API → PostgreSQL + read-only Kubernetes APIs. Финальные четыре показателя:

- PORTAL_UI = RUNNING
- PORTAL_API = RUNNING
- PORTAL_DB = CONNECTED
- PLATFORM_STATUS = VISIBLE

Все четыре подтверждаются свежим runtime evidence. Итог Hermes: READY_FOR_ARCHITECT_CONNECTOR_VERIFICATION. FINAL ACCEPTED присваивает только Architect.

## 1. Неизменяемые границы

1. P0–P7 и P8A/P8B приняты. Не повторять PostgreSQL backup, latest restore, PITR, P8A failover, P7/P7C failure tests.
2. Не выполнять destructive/failure scenarios; не удалять/перезапускать платформенные Pods, не переключать primary, не останавливать узлы, не запускать resync/restore/backup вручную. Естественный ScheduledBackup не отключать.
3. Порталу запрещены cluster-admin, BMC, root/SSH, shell, kubectl, generic Kubernetes proxy и mutation/scenario API.
4. P8C platform API — только read-only. SQL INSERT/UPDATE/DELETE допустимы только в новых прикладных таблицах Portal и не являются разрешением изменять платформу.
5. Не менять существующие инфраструктурные версии/образы/CNPG spec, S3, backup policies, DRBD, LINSTOR, Calico, маршруты, taints или bootstrap.
6. Не запрашивать и не восстанавливать ротированный privileged S3 password. SSH/root к узлам и S3 VM этой задаче не нужны. Недостающий разрешённый доступ — BLOCKED, а не новый парольный файл.
7. Не создавать отдельные LLM/субагенты и не менять модель Hermes. Соблюдать project-governance.
8. В этой задаче не устанавливать Prometheus/Grafana/новый LINSTOR adapter; не реализовывать HA Portal или demo scenario runner.

## 2. G0 — Source-of-Truth и безопасный runtime precheck

### Git

Выполнить в существующем checkout без вывода credential-bearing URLs:

```bash
git status --short
git branch --show-current
git fetch origin main
git rev-parse HEAD
git rev-parse origin/main
git log -6 --oneline origin/main
```

Проверить remote identity безопасным способом, не печатать embedded credentials. Не выполнять reset/clean/rebase/stash чужих изменений. Рабочая ветка для публикации — main; только fast-forward. Если локально другая ветка/dirty tree — сначала объяснить происхождение; не уничтожать работу.

AUDITED_BASE — историческая исходная точка. Ожидаемые новые commits после неё — только публикация данного Architect пакета. Проверить diff и ancestry, записать действительный AUTHORITATIVE_REMOTE_MAIN_SHA_START. Любые иные изменения, новый stage status или неожиданное P8C runtime состояние — STOP AND REPORT.

Прочитать README, project-governance, P8_STAGE_SPLIT, P8_PORTAL_IMPLEMENTATION_ROADMAP, P8B_FINAL_TO_P8C_NEXT_WORK_HANDOFF_20261020, P8_PORTAL_DB_CONTRACT, P8_PORTAL_PLATFORM_API_CONTRACT_R0, P8B_POSTGRES_BACKUP_CONTRACT, P8_BACKUP_POLICY_GAPS, P8C_ARCHITECTURE_PREFLIGHT_20261020, versions.lock, images.lock и P8B-R2 result/evidence. Старые evidence не редактировать.

### Runtime, исключительно чтение

Зафиксировать время UTC, command, exit code и минимальные безопасные JSON projections:

- Kubernetes server 1.36.2; три известных node Ready, отсутствие pressure/quorum/degradation признаков. Не выполнять fault tests.
- CNPG portal/portal-db: 3 expected/3 Ready, currentPrimary присутствует в статусе, streaming replicas по доступным status fields; PG 17.10; PVC Bound. Не искать Pod для SQL подключения.
- ScheduledBackup portal-db-daily с schedule `0 0 2 * * *`, prefer-standby, plugin; ObjectStore portal-db-backup; существующие Backup CR и WAL conditions. Не создавать backup.
- Velero BSL Available и namespace фактического Velero (ожидается velero).
- Metrics API доступен; API discovery подтверждает используемые ниже GVR и status fields. Сохранить served API versions/schema excerpts, без Secret contents.
- Envoy Gateway 1.9.1, GatewayClass eg Accepted, exact control/data-plane image pins из images.lock и сохранённых P6 manifests; MetalLB pool .110–.119 и фактические allocations. Не закреплять историческую .110 без проверки.
- Существующие Gateway/HTTPRoute/EnvoyProxy, policies, listeners, TLS certificate references; неожиданный пользовательский ingress не менять.
- CPU/memory allocatable и requests: хватит Portal (200m/256Mi request), миграции (100m/128Mi), Envoy dataplane по принятому baseline. Нет вытеснения DB/system workloads.
- Существующие NetworkPolicies portal и envoy namespace; namespaces/selectors и endpoint IP/ports API, DNS, DB. Сохранить topology без токенов.

Полный TR v4.0 отсутствует в Git tree исходного SHA. Не заявлять полную сверку с отсутствующим документом. Если доступное Hermes требование TR противоречит этому заданию — ADR-PROPOSAL/STOP, не менять решение самостоятельно.

G0 PASS: согласованное Git состояние; baseline здоров; входные объекты и разрешённый deployment доступ определены. При drift — STOP, не устранять его внутри P8C.

## 3. G1 — зафиксировать реализацию и интерфейсы

### Backend и frontend

Точный стек:

| Компонент | Версия / решение |
|---|---|
| Go | 1.27.3, linux/amd64 |
| HTTP backend | standard net/http ServeMux, html/template, embed из Go 1.27.3 |
| Kubernetes client | k8s.io/client-go, k8s.io/api, k8s.io/apimachinery v0.36.2 |
| PostgreSQL driver | github.com/jackc/pgx/v5 v5.11.0; pgxpool |
| Frontend | native browser ES modules + CSS; без внешнего JS framework/CDN |
| UI build | локальные HTML/CSS/JS встроены go:embed; хешированные asset URLs |
| Runtime image | собственный OCI image FROM scratch, statically linked Go binary |
| OCI builder | BuildKit 0.34.0, отдельный build host |
| SBOM/scanner/signing | Syft 1.55.0 / Trivy 0.76.0 / Cosign 3.1.3 |

Реализация — модульный монолит: cmd/portal; internal/httpapi; internal/collectors; internal/store; internal/health; internal/auth; web; migrations. UI/API обслуживает один процесс. Отдельные React/Node/Nginx контейнеры, ORM и миграционный framework для этого MVP не нужны. Это решение не запрещает полноценный дизайн, поиск, фильтры, сортировку и доступность интерфейса.

В Git создать `portal/` с go.mod/go.sum, исходниками, tests, Containerfile, Makefile, scripts, migrations и frontend assets. Приложение не запускает subprocesses. Запретить os/exec в runtime package (проверяется статически).

### Сбор данных

- InClusterConfig, короткоживущий projected ServiceAccount token, CA Kubernetes; никакого admin kubeconfig в образе.
- Typed clients для core/v1, apps/v1, batch/v1. Dynamic client с фиксированными GVR для CNPG/Barman/Velero/snapshots/Gateway/Metrics; не подключать весь operator SDK. Версии: postgresql.cnpg.io/v1, barmancloud.cnpg.io/v1, velero.io/v1, snapshot.storage.k8s.io/v1, gateway.networking.k8s.io/v1, metrics.k8s.io/v1beta1. Если G0 не подтверждает served version, STOP для обязательных источников; не выбирать иной API молча.
- Только Get/List. Poll каждые 30s; browser refresh 15s берёт backend cache. Metrics — 30s. Watch/informer/leader election в MVP не использовать.
- QPS=5, burst=10, максимум 4 concurrent source reads, per-request timeout=5s, collection deadline=20s. Не начинать overlapping collection. Ограничить list page 200; max 500 объектов каждой категории; при превышении `partial=true`, показывать coverage warning.
- Не выдавать браузеру Kubernetes credentials или raw objects. Данные преобразовать по allowlist DTO. Не сериализовать pod spec.env, команды, volumes, annotations, SecretRef values, free-form status messages, TLS keys, Secret/ConfigMap contents.
- Transport guard разрешает только GET к известным Kubernetes API paths; GET list разрешён, произвольный path/query/URL от пользователя запрещён. Redirect запрещён. Отдельный HTTP client для фиксированного Barman metrics Service, no proxy env/no redirects, 5s/1MiB limits.
- Ошибки одного источника не обнуляют остальные. Fresh/stale/error/unsupported/partial различать. Здоровье не выводить из количества успешно полученных объектов.
- Один collector в одном Portal instance; новые batches атомарно публикуются в памяти; background DB persistence не блокирует UI. В API всегда указывать источник и время последней успешной выборки.

### Прикладная БД

Canonical параметры неизменяемы:

```text
host=portal-db-rw.portal.svc
port=5432
dbname=portal
user=portal_app
sslmode=verify-full
schema=portal
```

Использовать pgxpool.ParseConfig с явным sslmode=verify-full и sslrootcert, затем безопасно присвоить Password из secretKeyRef. Запретить fallback к non-TLS, os environment DSN override, PGHOSTADDR/Pod IP, RO service, postgres role. Не логировать DSN/PGPASSWORD/pgx config/errors с credentials. Сверять host/servername; TLS 1.2 minimum.

Password: `valueFrom.secretKeyRef: {name: portal-db-app, key: password}`. Username фиксирован portal_app; DB фиксирован portal. CA: только публичный CA certificate key из действительного CNPG CA Secret, найденного по `.status.certificates.serverCASecret`; mount projection с `items: [{key: ca.crt, path: ca.crt}]`. Не монтировать ca.key/tls.key. Имя CA Secret уточняется чтением Cluster status, не предположением. У ServiceAccount нет read Secret RBAC: projection выполняет kubelet.

Pool maxConns=5, minConns=0, connectTimeout=5s, query timeout=3s, idle=5min. `search_path=portal,pg_catalog`; fully-qualified table names в SQL. Не создавать schema заново, если её нет: это нарушение DB contract, STOP. Не изменять права/схемы public, pg_catalog, CNPG, P8A/P8B probe tables.

Версионируемые forward-only migrations: filename `0001_portal_observations.sql`, SHA256 ledger. Выполнять отдельным Job `portal-migrate-0001`, тем же signed image и portal_app, с ServiceAccount `portal-migrator` без RBAC и без token mount. Не запускать миграции автоматически каждой web replica.

В одной транзакции взять `pg_advisory_xact_lock(804003001)`, проверить version/checksum; `lock_timeout=5s`, `statement_timeout=30s`; применить DDL из `docs/architecture/p8c/0001_portal_observations.sql`, записать version/checksum. Migration runner создаёт schema_migrations только если отсутствует; если уже есть — сверяет exact structure/ownership и checksum. Не скрывать drift через IF NOT EXISTS на остальных таблицах. Повторный запуск с тем же checksum — no-op; mismatch — STOP. На ошибке rollback транзакции, без DROP и без автоматической down migration.

DB purpose:

- schema_migrations — доказуемая версия прикладной схемы;
- observation_batches — нормализованные статусы и counts по одному сбору;
- timeline_events — безопасные события Kubernetes и изменения агрегированных статусов, dedup_key уникален.

Сохранять только DTO, не raw Kubernetes JSON. 7 дней retention; hard caps 20 000 batches и 50 000 events; prune не более 1000 строк на cycle только своих двух таблиц. Хранение ограничено также max 64KiB на batch и max 1024 characters synthesized message. Если DB недоступна, ограниченный memory buffer 1000 events; показывать persistence_lag/data_loss flag при overflow, не выдумывать сохранённую историю. После рестарта история читается из БД; прежние observations всегда stale до нового успешного сбора.

DB test: current_database/current_user/search_path, pg_roles flags для своей роли (superuser=false, createdb=false, createrole=false, replication=false), pg_stat_ssl только `pid=pg_backend_pid()` с ssl/version/cipher, migration checksum, INSERT/read в своих tables. Тест неправильного CA/hostname должен отвергаться клиентом до SQL; не отключать сервер TLS. Дополнительные права pg_monitor/superuser не выдавать.

## 4. MVP API contract

Машиночитаемый baseline: `docs/architecture/p8c/openapi.json` (OpenAPI 3.1.0). Реализация обязана соответствовать ему; no generic passthrough и no write endpoints.

| Метод/путь | Назначение |
|---|---|
| GET /api/v1/health | Process, DB connectivity, schema, collector, build; без credential details |
| GET /api/v1/summary | Overall PAK, subsystem health/coverage, alerts, current counts |
| GET /api/v1/nodes | Имя, Ready/pressure, capacity/allocatable; ожидается 3, но число не подставляется |
| GET /api/v1/workloads | Deployment/StatefulSet/DaemonSet/ReplicaSet/Job/CronJob status |
| GET /api/v1/pods | Фазы, Ready containers, restarts, node; без spec/env/logs |
| GET /api/v1/services | Type, safe port summary, readiness endpoints count; без generic proxy |
| GET /api/v1/storage | PVC/PV/StorageClass/VolumeSnapshot Kubernetes view |
| GET /api/v1/backups | Раздельные Velero BSL/Backup/Restore и CNPG/Barman observations + policy gaps |
| GET /api/v1/database | CNPG desired/Ready/currentPrimary/replica counts, phase/conditions, recovery evidence type |
| GET /api/v1/metrics | Nodes/pods CPU cores, memory bytes, source sample timestamp/window |
| GET /api/v1/events | Ограниченный event/status timeline из БД с fallback marker |

Общие обязательные поля: requestId, generatedAt, observedAt (nullable), freshness, partial, sources[], data, warnings[], nextCursor (nullable). Каждый source: id, state, observedAt, ageSeconds(nullable), errorCode(nullable). UTC RFC3339. Браузер показывает время в Europe/Moscow, tooltip UTC. No-cache для JSON; assets content-hash immutable. API business status возвращается в JSON, не кодируется произвольными HTTP codes.

GET/HEAD разрешены для UI; API контракт GET, HEAD допускается HTTP stack без side effects. Иные методы на существующих API → 405/Allow, до обращения к платформе или DB mutation. Unknown path 404; invalid query/cursor 400; auth 401; rate limit 429; server unable to serve bounded response 503. Partial/stale available data → 200 с честными полями. Источник Forbidden → source error, не HTTP 403 якобы от пользователя. Source outage не является пустым здоровым списком.

List endpoints принимают только namespace (точное имя, если применимо), limit (1..200, default=50), cursor. Cursor — локальная непрозрачная позиция snapshot, не Kubernetes continue token и не SQL. Для событий: дополнительно since RFC3339 и severity normal/warning/critical. Не разрешать произвольные labelSelector/fieldSelector, regex, SQL, API path, URL, команды. Проверять длины и allowed enums. Pagination в snapshot детерминированная; истёкший cursor → 400 CURSOR_EXPIRED с предложением обновить список.

### Правила достоверности

- Fresh <=90s от source observation; после 90s stale, old numbers визуально приглушены и подписаны; после 5min source unknown для сводного health. Пустой список и unavailable различаются.
- Overall: critical если свежий critical источник; иначе unknown при недоступном обязательном источнике; иначе warning при degraded/partial/stale/policy gap; иначе healthy. Never green on missing evidence. Обязательные источники: nodes, workloads/pods, storage Kubernetes view, Velero BSL, CNPG Cluster, CNPG Backup/ScheduledBackup/WAL conditions, application DB. Metrics optional, недоступность видна, не ломает остальные панели.
- Nodes: Ready=False/Unknown или pressure → warning/critical по словарю. desired=3 — expectation label; observed count выводится отдельно, mismatch — alert.
- DB: primary — только `.status.currentPrimary`; ready — `.status.readyInstances`; desired — `.spec.instances`. Observed replicas из CNPG reported instance status/Pod role+Ready projections. Если формула ready-1 используется как approximation, поле inferred=true; не называть её доказанной streaming replication. Missing fields → null/unknown.
- Storage: bound/ready snapshot и phase counts. `scope=kubernetes_objects`, `drbdDirectHealth=not_observed`, отдельная подпись «Прямое состояние DRBD/LINSTOR — вне MVP». Нет нового LINSTOR API/SSH.
- Backup: Velero и PostgreSQL два независимых домена. BSL Available не равно успешному последнему backup; Backup Completed не равно свежему restore proof. CNPG CR/conditions — основной источник, Barman metrics — дополнительный. Никаких S3 bucket list, download или credentials.
- PostgreSQL WAL: используемые текущие CNPG ContinuousArchiving/backup conditions с observedGeneration; timestamps из доступных полей/метрик. Не выдавать archive_timeout=300s за измеренный RPO; отсутствие WAL activity при idle не доказывает failure. last_failed_timestamp=0 не самостоятельный health proof. Last full backup >26h → warning; missing timestamp → unknown. Точность границы 26h — выбранная alert policy, не SLA.
- Latest restore/PITR PASS — явно «историческая квалификация P8B, 20.10.2026», а не «restore сейчас». Recovery state — отдельное живое CNPG phase/condition с nullable полями.
- Policy gaps всегда отдельным блоком; 8 копий не подставлять. Показать фактически observed successful backups, scope/limit и возраст; planned retention не равна доказанному числу сохраняемых S3 recovery points.
- Metrics: Kubernetes Quantity parsing, CPU в cores, memory в bytes; CPU% nodes — usage/allocatable*100, denominator подписан. Нет sample — null, не 0. Window/timestamp сохраняются; это Metrics Server samples, не полноценная историческая observability.
- Events: dedup по event UID + resourceVersion, counter сохраняется; source time и ingestion time разделить. При ошибке часов не переставлять историю молча. Kubernetes Event TTL и polling могут потерять события — timeline не полноценный audit trail.

## 5. Read-only RBAC — точная allowlist

Runtime SA: `portal/portal-reader`; automountServiceAccountToken=false и explicit projected volume с expirationSeconds=3600, default API audience, ca.crt и namespace. ClientConfig читает штатные projection paths; нельзя задавать произвольный audience, не принятый API server. Token rotation должна работать без рестарта приложения.

Все явно выдаваемые resource verbs: **get, list**. Watch отсутствует, поскольку выбран polling. Не использовать wildcard, aggregate-to-admin, system:masters, bind, escalate, impersonate или nonResource wildcard.

| Binding scope | API group | Resources | Verbs |
|---|---|---|---|
| ClusterRole portal-platform-reader + ClusterRoleBinding | core "" | nodes, persistentvolumes | get,list |
| тот же | storage.k8s.io | storageclasses | get,list |
| тот же, namespaces всех workloads для общей картины ПАК | core "" | pods, services, persistentvolumeclaims, events | get,list |
| тот же | apps | deployments, statefulsets, daemonsets, replicasets | get,list |
| тот же | batch | jobs, cronjobs | get,list |
| тот же | discovery.k8s.io | endpointslices | get,list |
| тот же | snapshot.storage.k8s.io | volumesnapshots | get,list |
| тот же | metrics.k8s.io | nodes,pods | get,list |
| Role portal-db-reader в portal + RoleBinding | postgresql.cnpg.io | clusters (resourceNames: portal-db), scheduledbackups (resourceNames: portal-db-daily) | get |
| та же Role | postgresql.cnpg.io | backups | get,list |
| та же Role | barmancloud.cnpg.io | objectstores (resourceNames: portal-db-backup) | get |
| Role portal-ingress-reader в portal + RoleBinding | gateway.networking.k8s.io | gateways (portal-gateway), httproutes (portal) | get |
| Role portal-velero-reader в фактическом velero namespace + RoleBinding | velero.io | backupstoragelocations, backups, restores | get,list |

Cross-namespace workload reads обоснованы общей консолью ПАК, а не только собственным namespace Portal. Kubernetes RBAC не умеет скрывать pod spec при get/list: backend DTO filtering защищает UI, но SA технически видит полные разрешённые objects. Это осознанная граница; не писать «SA не видит inline env». Secret API, logs, exec, attach, portforward, proxy и ConfigMap API не разрешены. Новые CRDs, VolumeSnapshotContents, nodes/proxy, pods/log, pods/exec, tokenrequests, rolebindings, certificatesigningrequests в allowlist не входят.

Проект exact YAML: `docs/architecture/p8c/rbac-design.yaml`; namespace velero сверить G0. Итоговый YAML сформировать строго по таблице; для resourceNames-only правил использовать named GET, не LIST с ложной фильтрацией. Ролевые bindings в velero ссылаются на SA namespace portal. Не выдавать namespace-wide edit ради миграции. Admission/system discovery permissions, выдаваемые кластером всем authenticated users, инвентаризировать отдельно; не маскировать их как созданные этим Role.

Read-only runtime API transport — дополнительная защита; реальная граница полномочий — RBAC. Пользовательский ввод не может добавить новый ресурс/verb.

## 6. Deployment, ingress, secrets, network

### Workloads

Namespace `portal` уже содержит БД. Не пересоздавать и не удалять namespace, не изменять его общие security labels так, чтобы задеть CNPG.

Deployment `portal`, replicas=1, labels `app.kubernetes.io/name=pak-portal`; container port8080; requests CPU200m/memory256Mi, limits CPU1/memory512Mi. ReadOnlyRootFilesystem=true, runAsNonRoot=true, runAsUser/Group=65532, allowPrivilegeEscalation=false, capabilities.drop=ALL, seccompProfile RuntimeDefault. No hostNetwork/hostPID/hostIPC/hostPath/privileged. Memory-only /tmp не более16Mi, только при доказанной необходимости. No PVC для самого web process.

Service `portal`: ClusterIP, port80 → named http:8080. Отдельный internal management port8081 не включать в Service: `/livez`, `/readyz`, `/startupz` только для kubelet probes. startup 60s budget, readiness interval10s, liveness interval20s. Liveness проверяет процесс без внешних зависимостей. Readiness: loaded assets, validated config/auth, known migration version и работающий serving loop. После первоначальной DB validation временный DB outage не отключает всю диагностическую UI; health/API явно DB_DISCONNECTED, persistence degraded. Первоначально без успешной DB/schema validation readiness=false. Это не доказательство failover/HA, P8F не выполняется.

Migration Job использует тот же pinned image, args `migrate`, отдельный SA без token. TTL не включать до сохранения logs/status; удалять только собственный completed Job после evidence, если предусмотрено change ledger.

### Barman metrics

Новый Service `portal/portal-db-metrics`, ClusterIP, TCP9187 →9187, selector `cnpg.io/cluster: portal-db` после подтверждения labels G0. EndpointSlice count ожидается3; это не балансировщик SQL. Collector обращается только к `http://portal-db-metrics.portal.svc:9187/metrics`, no redirects. Разрешены ровно три metric names из P8B-R2: first_recoverability_point, last_available_backup_timestamp, last_failed_backup_timestamp с полным prefix `barman_cloud_cloudnative_pg_io_`.

Запрос попадает на один instance; результат — sample одного exporter, не quorum consensus. При отсутствии source instance label отметить instance unknown, не искать primary и не обращаться к Pod IP. Endpoint для SQL по-прежнему только portal-db-rw с TLS. Raw metrics целиком в UI/DB не сохранять. Отсутствие метрик — unknown supporting evidence, не автоматический отказ всей системы.

### Gateway и HTTPS

Новый Gateway `portal/portal-gateway`, gatewayClassName=eg, listener https:443, hostname `portal.demo-pak.test`, TLS Terminate, certificateRefs на отдельный `portal/portal-ui-tls`; allowedRoutes.namespaces.from=Same. HTTPRoute `portal/portal`, parentRef portal-gateway/sectionName=https, hostname тот же, PathPrefix `/`, backendRef Service portal:80. Same namespace: ReferenceGrant не нужен. Port80 listener не открывать; TLS verify никогда не отключать.

Gateway dataplane должен наследовать approved Envoy digest из images.lock; inspect rendered/runtime imageIDs. Если controller создаёт dataplane по mutable tag, сначала определить supported EnvoyProxy config и разрешённый pinned образ; без закрепления — STOP. Не обновлять общий controller/CRDs. GatewayClass/MetalLB не пересоздавать. Dynamic allocated address из существующего pool, без расширения pool или правки сети.

TLS model для этого изолированного demo MVP: собственная namespaced цепочка cert-manager 1.21.0, исключительно для Portal UI. Проектные объекты заданы в `docs/architecture/p8c/tls-design.yaml`: Issuer portal-ui-bootstrap (SelfSigned) → Certificate portal-ui-root (CA, ECDSA256,365d) → Issuer portal-ui-ca → Certificate portal-ui-server (SAN portal.demo-pak.test, ECDSA256,30d,renewBefore7d) → Secret portal-ui-tls. Это конкретное P8C architectural proposal; после явной передачи данного задания Owner эти named objects входят в deployment allowlist. Не создавать ClusterIssuer и не менять shared trust/CA, CNPG или S3 certificates.

Root private key создаётся cert-manager в отдельном Secret portal-ui-ca и не экспортируется; runtime Portal не получает его. Экспортировать только публичный root certificate и SHA256 fingerprint для точечного доверия разрешённого тестового браузера/client profile. Не устанавливать новый trust root глобально на узлах/корпоративных клиентах. Browser proof обязателен с валидной цепочкой, без certificate-warning bypass. Cert-manager не обеспечивает автоматически распространение доверия при rotation CA: root rotation и восстановление UI CA — явно зафиксированное эксплуатационное ограничение demo PKI, без утверждения о production PKI/HA. Leaf renew проверяется конфигурационно, не искусственным временем/failure.

Если issuer/Certificate CRD отсутствует, cert-manager нездоров, выбранные имена заняты, согласованный клиент не может безопасно доверять публичному сертификату или policy запрещает dedicated demo CA — BLOCKED_TLS_ISSUANCE. Не включать HTTP fallback. При уже существующем разрешённом корпоративном issuer не переключаться молча: представить exact alternate issuerRef Architect.

В leaf secret ключи хранятся только Kubernetes, в Git — refs/certificate request parameters. Публичный CA допускается как trust material; private key и Basic Auth verifier не попадают в evidence. Client certificate SAN/chain/expiry проверить без вывода private material. Для демонстрации DNS на уже разрешённом клиенте или curl --resolve с выданным LB IP; `--cacert`, без `-k`. Не менять CoreDNS или корпоративный DNS внутри этой задачи.

### Доступ оператора

Один demo operator, read-only, без user management/SSO в MVP. Backend Basic Auth на UI/assets/API, только через HTTPS Gateway. Краткоживущие preflight probe paths на8081 наружу не экспонировать.

Сгенерировать 32 random bytes для operator password только через разрешённый secret store/secure delivery workflow. Username `portal-operator`. Хранить SHA256 этого высокоэнтропийного случайного значения в Secret `portal-ui-auth`, key `password-sha256`; приложение получает verifier через secretKeyRef и сравнивает constant-time. Не применять эту схему к выбранному человеком слабому паролю. Raw password не хранить в файлах/ConfigMap/Git/logs/скриншотах; защищённая передача Owner обязательна. Если нет такого механизма, BLOCKED_AUTH_HANDOFF. Не печатать credentials в итоговом ответе или URL.

Заголовок Authorization никогда не логировать; не доверять forwarded identity headers. Rate limit до auth: bounded global50requests/s и20concurrent, auth failure backoff; no unbounded per-IP map. Referrer-Policy no-referrer, X-Content-Type-Options nosniff, CSP default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'. Без inline JS/eval/innerHTML с platform text. No CORS wildcard. Cookies/JWT не вводить. Неверный Host отклонять; доверять TLS proxy headers только от разрешённого gateway path.

### NetworkPolicy

Перед новыми Pods проверить существующий default-deny. Не применять новый namespace-wide deny так, чтобы неожиданно заблокировать CNPG. Если baseline отсутствует в portal, STOP для отдельного согласования его безопасного введения с полным existing-flow inventory. При наличии baseline добавить политики только с selectors Portal/migrator/нового dataplane.

Allowlist flows:

- Portal/migrator → CoreDNS UDP/TCP53 с известными namespace/pod selectors.
- Portal → Kubernetes API Service443 и фактические control-plane endpoints6443: точные подтверждённые /32, учитывая Calico/DNAT. Нет 0.0.0.0/0.
- Portal/migrator → CNPG pods TCP5432; CNPG ingress reciprocal allow только от этих app labels. PostgreSQL verify-full обязателен независимо от NetworkPolicy.
- Portal → CNPG pods TCP9187 только для metrics Service; reciprocal allow.
- Только Portal Gateway dataplane → Portal TCP8080; dataplane egress только нужные backend/DNS/xDS flows по уже принятой Envoy схеме. Не ломать controller xDS ports предположениями.
- Migration SA не имеет Kubernetes API egress; после Job completion нет его постоянных Pods.
- Нет Portal egress к S3, BMC, node SSH, Интернету, arbitrary Pod/service networks. Registry pull выполняет container runtime, не приложение.

Проверить аддитивность существующих policies: новая узкая политика не сужает старый allow-all. Если широкое правило уже позволяет Portal запрещённый egress — STOP/Architect disposition, не заявлять default-deny без доказательства. Проверять на существующей безопасной тестовой точке или static effective-policy analysis; не сканировать BMC/SSH подсети.

## 7. UI — реальная операторская консоль

Русский интерфейс, нейтральная тёмная/светлая профессиональная палитра, ясная типографика, контраст и текстовые статусы вместе с цветом. Никаких invented graphs/sample counters в runtime build.

Первый экран desktop1366×768:

- Header «ПАК Портал», overall status, время последнего обновления и source freshness.
- Шесть компактных карточек: Nodes (observed/expected3), PostgreSQL Ready/desired, workloads/pods, storage Kubernetes view, Velero backup, PostgreSQL backup/WAL.
- Блок текущих предупреждений, включая policy gaps, coverage и stale sources.
- Последние события с source time; видимые links в detail tabs.

Навигация: Обзор / Kubernetes / Хранилище / Резервное копирование / PostgreSQL / Метрики / События. Таблицы имеют фильтр namespace, поиск по уже загруженным именам, сортировку и pagination. Кнопки только безопасные: обновить, фильтр, открыть detail. Нет «Удалить», «Failover», «Запустить backup», shell terminal или disabled муляжей будущих действий.

Состояния UI: loading, empty, partial, stale, unavailable, unauthenticated. Не держать зелёные cached cards при ошибке. Доступная навигация клавиатурой, label для controls, adaptive layout. JS получает данные только от same-origin API; обновление не сбрасывает текущий фильтр/scroll/focus. В интерфейсе нет технических Git/checklist instructions, secrets и внутреннего engineering evidence dump.

## 8. G2 — supply chain, воспроизводимая сборка и security gate

Официальные исходники и опубликованные digests зафиксированы в `evidence/P8/20261020-p8c-architect-preflight/source-verification.json`. Они были проверены как metadata, а не как скачанные байты. Перед использованием:

1. Скачать точные релизы только с официальных URLs, проверить SHA256, recorded tag→commit. В случае несовпадения STOP; latest не применять.
2. Проверить Sigstore/checksum bundles, provenance и issuer/identity по upstream release workflow. Сохранить сертификат identity/issuer/public key fingerprint и результат verification. Нельзя `--insecure-ignore-*`, broad identity regexp или «signature verified» на основании одного SHA256. Go archive: официальный SHA256; не заявлять upstream signature, если её нет.
3. Проверить build host architecture/tool versions и изоляцию. BuildKit rootless на разрешённом build host, no privileged builder на ПАК. Если требуются новые привилегии/daemon/registry — STOP, не устанавливать самостоятельно на cluster node.
4. go.mod pins exact; GOTOOLCHAIN=local; запрет go get -u. Один раз разрешить транзитивный graph, сохранить go.sum, `go list -m -json all`, `go mod verify`. Proxy/sumdb verification не отключать. Ни зависимости, ни code generation не скачиваются в runtime.
5. `go test ./...`, `go vet ./...`, race tests на collector/store concurrency; mocked upstream tests. CGO_ENABLED=0, GOOS=linux, GOARCH=amd64, `-trimpath`; записать Go version и git source revision, reproducible build inputs. Не strip Go module metadata, необходимую scanner.
6. Скомпилировать binary вне контейнера; OCI Containerfile FROM scratch, COPY binary only, USER65532:65532, EXPOSE8080/8081. CA/public trust поступают mount projections; не копировать host /etc/ssl/private или /etc/passwd. FROM scratch не имеет base digest — записать NOT_APPLICABLE_EMPTY_BASE, а не фальшивый digest.
7. Использовать встроенный Dockerfile frontend pinned BuildKit, без `# syntax=...:latest`. Build context allowlist: binary и Containerfile; не весь checkout с локальными secret stores.
8. BuildKit provenance не доказывает автоматически внешний Go compilation: добавить attestation с source tree hash, binary SHA256, Go archive hash, go.sum, build command, builder version. Связать все материалы с итоговым OCI manifest digest.
9. Syft по готовому OCI image → SPDX JSON. Trivy image/source/config/secret scans; сохранить точную версию scanner и vulnerability DB digest/updatedAt. Нельзя сканировать пустой scratch и забыть Go binary/modules. Найденные secrets не публиковать, только redacted path/rule disposition.
10. Gate: 0 unaccepted CRITICAL/HIGH findings в app/deps/toolchain. Low/Medium занести в ledger с анализом. Unfixed HIGH тоже требует Architect risk decision; ignore-unfixed не допуск. Не объявлять «безопасно» по exit0 без отчёта и базы.
11. Итоговый image подписать Cosign через уже разрешённый protected signing key/KMS либо утверждённую keyless identity. Публичную часть/trust policy фиксировать; private key не в Git. Если identity/registry permission отсутствуют — BLOCKED_SUPPLY_CHAIN, не создать самоподписанный доверенный ключ и не публиковать исходники/образ публично без разрешения.
12. Registry destination по умолчанию private `ghcr.io/dedvmedved-dot/otus-diplom-portal`, только если доступ и private visibility подтверждены; иначе согласовать конкретное доступное private destination. Runtime ref строго `...@sha256:<verified-digest>`. Перед deploy проверить pull/verify тем же digest, SBOM subject и provenance source. Kubernetes imagePullSecret только ref, если нужен.

До G3 никаких production apply. Внести exact app/tool versions и pins в новые portal lock entries, не переписывая старые infrastructure locks. Build outputs/сканы подписать и сохранить в разрешённом artifact registry; в Git JSON evidence, SHA256 и устойчивые refs. Не коммитить большие binaries.

## 9. G3 — pre-deployment gate и разрешённые инженерные изменения

Это allowlist действий инженера после передачи задачи Owner; это НЕ права Portal SA:

- создать исходники/locks/tests/документы;
- создать/обновить только Portal Deployment/Service/ConfigMap(no secrets), ServiceAccounts и точные Roles/Bindings из §5;
- отдельный Migration Job и его новые прикладные tables;
- Service portal-db-metrics;
- новый Gateway/HTTPRoute и, при необходимости, scoped EnvoyProxy config только для pinned dataplane этого Gateway;
- два Issuer и два Certificate из tls-design.yaml только в portal; создаваемые cert-manager CA/leaf Secrets; auth/imagePull Secret через безопасный механизм вне Git;
- additive app-scoped NetworkPolicies и узкие reciprocal CNPG ingress allows;
- DNS hosts/resolve на авторизованном тестовом клиенте, без платформенных DNS/network изменений.

Все target names/UID/ownership и expected diff записать в change-allowlist.json. Если объект с выбранным именем уже принадлежит не P8C — STOP. Не применять рекурсивно весь manifests/. Не использовать kubectl apply --prune.

Выполнить schema/RBAC/static security validation и server-side dry-run exact manifest set; сохранить sanitized diff, existing flow safety review, source/image gates и capacity budget. Проверить, что новый Pod не получает system-critical priority или broad toleration. До реального apply должны быть доступны TLS issuance, secure auth delivery, registry pull и signing trust — это реальные prerequisites, не строки TODO.

Если они отсутствуют, завершить полный source/build/reviewable package и STOP до runtime, с конкретным минимальным Architect decision. Это не разрешение ослабить TLS/auth/RBAC.

## 10. G4–G7 — исполнение и доказательства

### G4 — DB migration

Применить только миграционный Job и необходимый restricted network/secret wiring. Дождаться Completed с timeout120s. Сохранить version/checksum/row-level validation и TLS facts, без пароля. Повторный запуск runner в контролируемом validation режиме должен подтвердить no-op (не создавать второй conflicting Job); checksum drift negative test — только unit/fixture. Если migration fails — STOP; web deployment не открывать.

### G5 — backend/frontend

Применить Portal resources, получить Ready; startup/readiness/liveness evidence. Использовать API изнутри и сверить DTO с независимыми kubectl read-only projections одного временного окна. Не использовать Portal response как единственный oracle.

Доказать DB persistence: записанные collector batches и event/status entries читаются отдельным разрешённым SQL запросом portal_app; checksum/data types корректны. Не перезапускать production Portal только ради проверки persistence/HA — долговечность после restart проверить local test instance/test DB в изолированном build/test окружении, не P8F.

### G6 — ingress/UI

Применить dedicated Gateway/HTTPRoute после TLS/auth readiness. Проверить:

- Gateway Accepted=True, Programmed=True и observedGeneration соответствует metadata.generation;
- listener Ready/ResolvedRefs, HTTPRoute parent Accepted=True/ResolvedRefs=True, exact parent/controller, актуальная generation;
- LB Service assigned approved IP; EndpointSlice → Ready Portal Pod; dataplane digest равен принятому pin;
- внешний разрешённый клиент: TLS chain/SAN/expiry verification; unauthenticated401; authenticated200 HTML + JS/CSS200; все API responses; wrong host/no-route negative path;
- неизвестный API путь404; POST/PATCH/DELETE к Portal API405 без side effects;
- UI browser: screenshot первого экрана и каждого раздела, никаких credentials/Authorization в кадре, console/network errors отсутствуют; counters совпадают с независимым snapshot. curl200 сам по себе не доказывает отрисовку JS.

HTTP probe не передаёт пароль аргументом командной строки, URL или логируемым curl -v. Использовать secret-aware client, защищённый stdin/file descriptor; не сохранять credential file на диск. Скриншоты не содержат password prompt заполненным значением.

### G7 — access/security/postcheck

1. Проверить всю allowlist get/list. Проверить запрет Secret/ConfigMap get/list, pods/log/exec/attach/portforward/proxy, nodes/proxy, create/update/patch/delete/deletecollection на platform resources, create tokens/RBAC escalation/impersonation. `kubectl auth can-i` выполняет инженер через impersonation выбранного SA, с корректными serviceaccount groups; этот auth review не разрешён runtime Portal transport.
2. Реальный denied mutation test: от identity portal-reader отправить ровно один create ConfigMap запрос на уникальное НЕСУЩЕСТВУЮЩЕЕ имя `p8c-rbac-denied-<runid>`, `dryRun=All`. Ожидается Kubernetes HTTP403 Forbidden именно RBAC (не timeout/404/validation error). Даже при ошибочном разрешении dry-run не создаст объект. Любой не-403 результат — FAIL/STOP. Проверить объект отсутствует. Не пытаться удалять/patch существующие ресурсы для негативного теста.
3. Тест Secret access только на гарантированно несуществующем имени/authorization review; не скачивать существующие Secret contents ради доказательства отказа. Если auth review показывает allowed — FAIL прежде запроса.
4. Проверить backend transport guard unit tests: POST/PUT/PATCH/DELETE/custom host/redirect запрещены; API input injection не достигает Kubernetes. Fixtures для missing/stale/403/404/429/timeout/malformed/null fields; no-green-on-error.
5. UI XSS-safe rendering test на synthetic Event reason/name; шаблонизация escape; raw message/env/annotations не попадают в DTO/DB/logs. Credentials scanner по tracked diff/evidence/image context с redaction.
6. NetworkPolicy effective allowlist и отсутствие запрещённого egress; отсутствие Secret RBAC, privilege/host mounts; приложение не содержит shell/kubectl; imageID/SBOM/provenance match.
7. Свежий platform postcheck теми же безопасными командами G0: nodes3/3, CNPG3/3, no degradation, Velero BSL Available, ScheduledBackup/ObjectStore без неожиданного изменения. Природные counters/resourceVersion/time/плановые backups отличать от изменения spec.
8. Сравнить списки Backup/Restore/scenario objects и mutation ledger до/после: P8C не инициировал backup/restore/failure. Не удалять естественные scheduled objects для совпадения baseline.

## 11. G8 — evidence и публикация

Папка `evidence/P8/<UTC-runid>-task-p8c-r1-portal-mvp/`. Каждый файл содержит источник, timestamp UTC, команду или script hash, exit code и raw sanitized output. Секретные поля отбрасывать ДО записи; не редактировать старый результат задним числом. Сохранять FAIL и subsequent retry как отдельные записи.

Минимальный реестр:

| Группа | Обязательные файлы / доказательства |
|---|---|
| Recovery | 01-start-state.md, 02-git-ancestry.json, 03-platform-precheck.json, 04-gateway-baseline.json |
| Design | 05-api-discovery.json, 06-design-decisions.md, 07-change-allowlist.json, 08-effective-network-policy.md |
| Supply | 10-source-lock.json, 11-tool-checksums.txt, 12-signature-verification.json, 13-module-graph.json, 14-build-tests.txt, 15-image-digests.json, 16-sbom.spdx.json, 17-scans.json, 18-security-ledger.md, 19-provenance-and-image-signature.json |
| RBAC | 20-rbac.yaml, 21-allowed-read-matrix.json, 22-denied-matrix.json, 23-denied-mutation-403.txt |
| DB | 30-migration-inventory.json, 31-migration-checksum.txt, 32-migration-result.txt, 33-db-tls-sanitized.json, 34-db-persistence-proof.json |
| App | 40-deployment-status.json, 41-health-readiness.json, 42-service-endpoints.json, 43-api-responses/*.json, 44-independent-source-comparison.md |
| Ingress/UI | 50-gateway-route-status.json, 51-tls-chain-proof.txt, 52-external-client-proof.txt, 53-ui-screenshots/, 54-browser-console-and-network.md, 55-auth-negative-tests.txt |
| Closure | 60-secret-scan-redacted.txt, 61-platform-postcheck.json, 62-mutation-ledger.json, 63-policy-gaps.md, 64-git-diff-check.txt, result.md |

`result.md` включает observed Git/source/image digests, все Gates PASS/FAIL/BLOCKED/NOT_EXECUTED, ограничения, URL без credentials, снимок четырёх целевых критериев, свежесть данных, отдельные состояния DB connection и CNPG health, policy gaps и безопасный способ доступа Owner (без секретов).

Git последовательность:

- Commit A: исходники/contracts/migrations/tests/locks и design; содержательное сообщение `P8C-R1: implement read-only Portal MVP and pinned build contract`.
- Commit B: manifests/image pins/supply-chain evidence и deploy preparation; `P8C-R1: pin Portal image and scoped deployment resources`.
- Commit C: фактический runtime/evidence/docs status; `P8C-R1: record Portal MVP runtime evidence for Architect review`.

Разделение допускает отсутствие B/C при blocker, но нельзя писать выполненный runtime до его проверки. Перед каждым push fetch origin/main, проверить ожидаемый parent, git diff --check и redacted secret scan. Никаких force/reset/rebase опубликованного. На гонке remote HEAD STOP с сохранением работы.

README/P8_STAGE_SPLIT обновлять только до P8C IN_PROGRESS или READY_FOR_ARCHITECT_REVIEW по факту; P8A/P8B не понижать, P8D–P8G/P9 не авторизовать. Старые P6 zero-Gateway verifiers отражают historical stage boundary: не подменять их output и не запускать cleanup нового Portal. Создать отдельный P8C read-only verifier, ожидающий ровно разрешённые Portal ingress objects плюс принятый baseline; неожиданные объекты не игнорировать.

## 12. STOP conditions и возврат к безопасному состоянию

Немедленный STOP при Git/status drift, unhealthy baseline, недостатке capacity, отсутствующем migration privilege/DB CA/cert-manager capability/client trust/auth delivery/registry/signing trust, версии вне lock, checksum/signature mismatch, неприемлемом CVE, необходимости cluster-admin для Portal, write RBAC, Secret exposure, default-deny bypass, неподдерживаемом mandatory GVR, невоспроизводимом endpoint или требовании изменить P8A/P8B.

Недоступность optional Metrics/Barman supporting sample после корректного admission → видимый degraded source, не скрытый PASS; minimum mandatory platform data всё равно должны быть доказаны. Ошибка реального обязательного источника блокирует успешную приёмку, даже если HTML загружается.

Rollback не трогает platform/DB data. При ошибке новой app rollout прекратить exposure только своего HTTPRoute/Deployment по зарегистрированным UID; использовать previous approved Portal digest, если он существует. Для первого deploy оставить диагностические artifacts и остановить новые Portal Pods/route через инженерный доступ. Не удалять namespace portal, CNPG, PVC/PV, backup objects, shared CA/Secrets, tables или evidence. Failed SQL transaction откатывается автоматически; успешная migration остаётся для forward repair. При сомнении остановиться до удаления; сообщить точные targets и причину.

После G8: STOP AND REPORT. Не приступать к P8D/P8E/P8F/P8G/P9 и не выдавать себе CONNECTOR VERIFIED.
