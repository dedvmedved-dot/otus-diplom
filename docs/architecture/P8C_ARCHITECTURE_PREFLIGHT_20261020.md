# P8C Architecture Preflight — 20 октября 2026

STATUS: DESIGN PREPARED / HERMES TASK NOT DISPATCHED

Автор: Chief Architect. Эта редакция готовит P8C-R1; runtime в этом Work не запускался.

## 1. Независимое восстановление Source of Truth

Через GitHub Connector проверены branch `main`, последние шесть commits, полное Git tree (truncated=false), перечисленные ниже документы и исходные P8B-R2 evidence. На начало проверки HEAD точно равен `6e19db29d9da0f9f67c87fd3e1bb3a3320a49702`, tree `ad210e322bb829bbc91b4b90814b981dfbadbc3d`. Неожиданных commits после handoff нет. GitHub Actions вернул пустой список runs; успешный CI не заявляется.

| Порядок | Commit | Смысл |
|---|---|---|
| 1 | `6e19db29d9da0f9f67c87fd3e1bb3a3320a49702` | Architect принял P8B и разрешил P8C |
| 2 | `3c4dde36d8d03dd208d400381ab7b5869dd509d8` | P8B-R2: schedule, metrics, credential hygiene |
| 3 | `7a286689fffbfd9f9f2820d6329a7f1d4995042e` | P8B: backup / restore / PITR |
| 4 | `68e377918ec33d3d62ecbddbc5bd8534a45b9f7e` | Ранний P8B с историческим credential blocker |
| 5 | `cec598508138b71068f3131740eb41de88d908ea` | Контракт native backup |
| 6 | `ef24d486ecec3c3d5b0c2b4e63d9f005bac60c74` | P8A runtime / evidence |

Проверены README, P8_STAGE_SPLIT, P8_PORTAL_IMPLEMENTATION_ROADMAP, P8B_FINAL_TO_P8C_NEXT_WORK_HANDOFF_20261020, P8_PORTAL_DB_CONTRACT, P8_PORTAL_PLATFORM_API_CONTRACT_R0, P8B_POSTGRES_BACKUP_CONTRACT, P8_BACKUP_POLICY_GAPS, versions.lock, project-governance, P4B-NETWORKPOLICY-BASELINE и canonical CNPG/ScheduledBackup/GatewayClass manifests.

| Этап | Подтверждённый документальный статус |
|---|---|
| P0–P7 | FINAL ACCEPTED |
| P8 | IN PROGRESS |
| P8A | FINAL ACCEPTED / CONNECTOR VERIFIED |
| P8B | FINAL ACCEPTED / CONNECTOR VERIFIED |
| P8C | AUTHORIZED / NOT STARTED — runtime |
| P8D–P8G | NOT AUTHORIZED |
| P9 | NOT AUTHORIZED |

Recovery result: **PASS — состояние GitHub позволяет подготовку P8C**. Это проверка сохранённых доказательств, а не новое измерение работающего кластера. Свежий runtime precheck выполняет Hermes перед изменениями.

В result.md P8B-R2 записано `P8C: NOT_AUTHORIZED`: файл относится к 05:23 UTC, до Architect commit 06:27 UTC. Это не текущий статус. Аналогично исторические checkpoints roadmap не переопределяют его итоговый раздел 12. Заголовок versions.lock `verification_status: NOT_VERIFIED` является общим старым метаданным, не доказательством регрессии принятых стадий; его автоматически не исправлять. Комментарий GatewayClass «1.8.3» устарел: принятое исполнение 1.9.1 подтверждено README/lock/P6 evidence; spec GatewayClass не содержит версии.

Полный текст TR v4.0 и AGENTS.md в полном дереве этого SHA не обнаружены. Совместимость с полным отсутствующим TR не заявляется. Решение ниже конкретизирует доступные утверждённые контракты P8 и текущую директиву Owner; оно не разрешает отклонения от известных требований. Если Hermes располагает требованием TR, противоречащим этому заданию, STOP/ADR, без самостоятельной замены стека.

## 2. Проверка P8B-R2

Проверены result.md и исходные 09-scheduledbackup-canonical-match.md, 11-barman-metrics-endpoint-discovery.md, 12-barman-metrics-raw-sanitized.txt, 20-password-rotation-sanitized.txt, 21-plaintext-password-file-removal.txt, 26-post-r2-platform.txt в `evidence/P8/20261020T052255Z-task-p8b-r2-sot-metrics-credential-closure/`.

- Canonical ScheduledBackup: `portal/portal-db-daily`, cron `0 0 2 * * *`, 02:00 UTC, prefer-standby, plugin method. R2 не создавал дополнительный backup.
- Метрики получены из CNPG instance manager, TCP 9187: last available backup и first recoverability point `1792469710`; last failed backup `0`. Это историческая выборка, не сегодняшнее live значение UI.
- Evidence подтверждает ротацию скомпрометированного privileged password без записи нового значения и отсутствие plaintext automation file. Значения не запрашивались.
- Postcheck: portal-db 3/3, PG 17.10, 1+2, archiving включён, Barman sidecars 3/3, Velero BSL Available. Подробное повторение backup/restore/PITR/failover запрещено.
- Policy gaps остаются видимыми: 14d WAL policy; минимум 8 копий — capability, не доказанный фактический возраст; incremental/differential 14 не реализованы; monthly 12 отложены.

## 3. Gateway baseline

Canonical `manifests/envoy-gateway/p6c-gatewayclass.yaml`: `eg`, controller `gateway.envoyproxy.io/gatewayclass-controller`.

P6D-R2 result (`evidence/P6/20260909T232839Z-task-p6d-r2-final-evidence-contract-closure/result.md`) подтверждает Envoy Gateway 1.9.1, Accepted GatewayClass, MetalLB 3/3, внешние HTTP probes с `atlas-1.brest.local / 172.30.20.51`. Временный Gateway был HTTP:80, LB `172.30.140.110`, pool `.110–.119`. После проверки validation namespace, Gateway, HTTPRoute, LB и dataplane удалены; residue=0.

Следствие: foundation есть, постоянный ingress Портала ещё нужно создать. Нельзя скопировать historical LB IP как гарантированно свободный адрес или использовать имя удалённого Gateway. В P8C проектируется новый namespaced `portal/portal-gateway` (class eg), TLS:443, HTTPRoute `portal/portal`, hostname `portal.demo-pak.test`. IP выделяется существующим MetalLB pool после read-only inventory. Публичный DNS не нужен; проверочный клиент использует internal DNS или локальный resolve с тем же hostname.

## 4. Технологическое решение

| Слой | Выбор | Основание |
|---|---|---|
| Backend | Go 1.27.3; standard `net/http`, `html/template`, `embed` | Один статический бинарник; маршруты и доступ к данным строго ограничены |
| Kubernetes | client-go/api/apimachinery v0.36.2 | Соответствие minor 1.36; typed core/apps/batch, dynamic CRD client |
| DB | pgx/v5 v5.11.0 + pgxpool | Native PostgreSQL, verify-full, управляемый pool |
| Frontend | Native ES modules, HTML5/CSS, Go-rendered shell; без стороннего JS framework | Асинхронные таблицы/карточки/фильтры без Node/NPM runtime и отдельного frontend image |
| Образ | Собственный OCI linux/amd64, scratch, UID/GID 65532 | Внутри нет shell, kubectl, package manager; CA поступают через projections |
| Сборка OCI | BuildKit 0.34.0 на изолированном build host | Не устанавливать build daemon на узлы ПАК |
| SBOM | Syft 1.55.0 | SPDX JSON по готовому образу |
| Scan | Trivy 0.76.0 | Image/dependency/config/secret scans, фиксировать vulnerability DB |
| Подпись | Cosign 3.1.3 | Проверка release bundles и подпись результата доверенной identity |

Source tags проверены Connector: client-go v0.36.2 → commit `877f5359348b5df85619f2aa379abc5bd74bca2d`; pgx v5.11.0 → `5e583fa7aabfa88b796292f849fc9d7d75ac159d`. Их go.mod требуют Go 1.26 и 1.25 соответственно. Выбранная версия Go выше обоих минимумов; фактическую сборку ещё нужно проверить.

Go 1.27.3 опубликован как stable; release history сообщает исправление crypto/x509. Toolchain 1.27.2 из SeaweedFS ADR не переносится автоматически на новое приложение; существующий SeaweedFS не меняется. Полные URL и опубликованные SHA256 инструментов сохранены в `evidence/P8/20261020-p8c-architect-preflight/source-verification.json`.

Уровни проверки разделены: existence/version/source metadata = VERIFIED; скачанные байты/signatures/SBOM/image scan/runtime digest = NOT EXECUTED, обязательный G2. Финальный digest нового Portal image нельзя достоверно назвать до сборки. Использование mutable tag или выдуманного digest запрещено.

## 5. Границы архитектуры

- Один Deployment (replicas=1), один процесс и ClusterIP Service: UI и API одного origin; HA Портала остаётся P8F.
- Только GET/list к фиксированным Kubernetes ресурсам. Watch в MVP не нужен; verbs watch и write не выдаются.
- CNPG/Velero/Barman читаются как Kubernetes CRD; S3 credentials не выдаются Порталу. Barman metrics идут через отдельный ClusterIP `portal-db-metrics`:9187, не через Pod-IP discovery.
- PostgreSQL SQL через `portal-db-rw.portal.svc:5432`, DB portal, role portal_app, schema portal, verify-full. Только собственные versioned tables; infra/probe tables не трогать.
- DB хранит observation batches и очищенный event/status timeline; экран не зависит от наличия большой истории. Unknown/stale/partial всегда видимы.
- Storage summary — только Kubernetes storage view. Нельзя приравнивать Bound PVC к UpToDate DRBD или успешный backup CR к доказанной текущей восстанавливаемости.
- TLS на Gateway от проектируемой отдельной namespaced demo UI CA (cert-manager, без переиспользования CNPG/S3 CA); доверие только в тестовом client profile. Ограниченный демонстрационный operator account через Basic Auth только поверх HTTPS; credentials вне Git/evidence. Без защищённого доступа внешний listener не открывать.
- P4B default-deny обязателен; существующие CNPG/Barman/Velero policies не заменять. Для новой backend pod применять отдельные selectors и необходимые allows.

Минимальная схема, API, RBAC, network/deployment, authorization, acceptance и STOP условия полностью определены в `docs/tasks/TASK_P8C_R1_PORTAL_MVP.md`; машиночитаемый контракт — `docs/architecture/p8c/openapi.json`.

## 6. Оставшиеся фактические проверки перед runtime

Это ожидаемые deployment gates, а не заявленные успехи: свежий cluster precheck; CRD served versions и status fields; gateway/image baseline и свободный IP; готовность cert-manager к отдельной namespaced UI CA и доверие тестового клиента; registry push/pull и signing identity; SHA/signature инструментов; полный go.sum/SBOM/CVE report; новые image digests; DB schema inventory и права роли; NetworkPolicy endpoint/DNAT behavior. При отсутствии предпосылки Hermes фиксирует точный blocker, не расширяет scope и не запрашивает скомпрометированный пароль.

## 7. Официальные внешние источники, проверенные при подготовке

- https://go.dev/doc/devel/release — release history Go.
- https://go.dev/dl/?mode=json — SHA256 Go archive.
- https://github.com/kubernetes/client-go/tree/v0.36.2 — source/client compatibility; go.mod проверен Connector.
- https://github.com/jackc/pgx/releases/tag/v5.11.0 — driver release; go.mod проверен Connector.
- https://github.com/moby/buildkit/releases/tag/v0.34.0
- https://github.com/anchore/syft/releases/tag/v1.55.0
- https://github.com/aquasecurity/trivy/releases/tag/v0.76.0
- https://github.com/sigstore/cosign/releases/tag/v3.1.3
- https://kubernetes.io/docs/reference/access-authn-authz/rbac/

GitHub — источник состояния проекта; upstream sources используются только для проверки внешних компонентов. Новые версии инфраструктуры не предлагаются и не устанавливаются.

Дополнительно проверены официальные схемы private PKI и Gateway TLS: https://cert-manager.io/docs/configuration/selfsigned/ ; https://cert-manager.io/docs/configuration/ca/ ; https://gateway.envoyproxy.io/v1.9/tasks/security/secure-gateways/ . Dedicated UI CA — новое P8C design решение, не обнаруженный ранее существующий issuer. Публикация design YAML не означает его применение.
