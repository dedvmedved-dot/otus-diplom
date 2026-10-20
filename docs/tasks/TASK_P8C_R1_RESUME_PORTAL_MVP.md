# TASK: P8C-R1 RESUME — PORTAL MVP

STATUS: PREPARED FOR OWNER DISPATCH. Исполнитель: Hermes. Стадия: только P8C.

## 1. Цель и границы

Доработать опубликованный MVP, закрыть три внешних preconditions фактическими evidence и завершить исходные G0–G8. Нельзя переходить прямо к G4: Architect source review выявил F01–F10, G1 требуется переоткрыть.

Обязательные документы:

- `docs/architecture/P8C_R1_ARCHITECT_REVIEW_AND_DECISION_20261020.md` — решение D1–D3 и findings F01–F10.
- `docs/tasks/TASK_P8C_R1_PORTAL_MVP.md` — полный исходный task, API/DB/UI/evidence требования остаются обязательными.
- `docs/architecture/p8c/openapi.json`, `rbac-design.yaml`, `0001_portal_observations.sql`, `tls-design.yaml`.
- `docs/architecture/P8_PORTAL_DB_CONTRACT.md`, `P8_PORTAL_PLATFORM_API_CONTRACT_R0.md`, `P8B_POSTGRES_BACKUP_CONTRACT.md`, `P8_BACKUP_POLICY_GAPS.md`.
- `docs/network/P4B-NETWORKPOLICY-BASELINE.md`, `docs/governance/project-governance.md`.

Review target: `00b491771230556f061280fb914b6dd6806e2264`. Начальный HEAD исполнения — **фактический origin/main, содержащий этот task**; не hardcode старый SHA как HEAD. Проверить Connector/readback и ancestry. В этой подготовке runtime не выполнялся.

Не выполнять P8D/E/F/G/P9, base backup/latest restore/PITR/failover/P7/P7C failure tests. Не менять CNPG Cluster/ObjectStore/ScheduledBackup/Velero/S3/LINSTOR/DRBD infrastructure spec или чужие данные. Нет cluster-admin/BMC/root/SSH/shell/kubectl/generic mutation API внутри Portal. Read-only platform access остаётся get/list, без write verbs; инженерный deployment access не передаётся приложению.

После передачи Owner можно автономно пройти внутренние R0–R7 в пределах этой задачи. На unmet gate — прекратить зависимые/опасные операции, продолжить только независимую разрешённую source/test работу, затем STOP AND REPORT. Финальная приёмка — только Chief Architect.

## 2. R0 — recovery и честный baseline

1. Проверить remote, clean worktree, branch/main HEAD, последние commits, diff/ancestry от review target. Никаких force/rebase published history. Необъяснённый drift -> STOP.
2. Прочитать исходный result `evidence/P8/20261020T073609Z-task-p8c-r1-portal-mvp/result.md` как historical Hermes report. Не изменять его и не удалять failures.
3. Новый evidence directory: `evidence/P8/<actual-UTC-runid>-task-p8c-r1-resume-portal-mvp/`. Фиксировать actual UTC, command, context без credentials, exit code, sanitized output, tool version, source SHA. Не восстанавливать старые raw outputs по памяти.
4. Свежий read-only runtime precheck: nodes3/3, CNPG3/3, current primary/replicas из CR status, Velero BSL Available, Barman/WAL conditions, served GVR, GatewayClass eg, cert-manager, LB capacity, CA Secret name из Cluster status, API/DNS endpoints, resources/capacity. Не создавать backup или restore для проверки.
5. Fingerprint неизменяемых infrastructure specs/существующих policies до работы; volatile status/counters выделять отдельно. Если baseline нездоров — STOP, не чинить платформу внутри P8C.

R0 PASS — источник/границы подтверждены, фактический baseline здоров. G0 summaries прошлого запуска не заменяют новые доказательства.

## 3. R1 — исправить source до build/release

Сохранить выбранный стек: Go1.27.3/net/http/embed, native ES module frontend, client-go/api/apimachinery v0.36.2, pgx v5.11.0, scratch image. Framework/SSO/DRBD adapter не добавлять. Исправления обязаны соответствовать существующему OpenAPI и task, а не уменьшать их требования.

### F01, F07 — identity, secrets, DB startup

- У `portal-reader` automount=false; добавить explicit projected volume в `/var/run/secrets/kubernetes.io/serviceaccount`: serviceAccountToken path `token`, expirationSeconds=3600, audience принятый Kubernetes API (default API audience допустим); API public CA `kube-root-ca.crt` key `ca.crt`; namespace через downwardAPI. Проверить token rotation поддерживаемым client-go; не выводить token. Kubelet projection не требует Portal read ConfigMap/Secret RBAC. Migrator token не получает.
- DB password строго `valueFrom.secretKeyRef: {name: portal-db-app, key: password}` в Deployment и migration Job; config получает значение без log/dump и assigns `pgx.ConnConfig.Password`. Auth verifier аналогично secretKeyRef `portal-ui-auth/password-sha256`. Убрать заменяющие парольные file paths/mounts. CA остаётся публичной key projection, без private keys.
- Фиксировать host=`portal-db-rw.portal.svc`, port=5432, DB=`portal`, user=`portal_app`, sslmode=verify-full; TLS>=1.2, ServerName/CA. Запретить ambient PG overrides/fallback, URI/Pod IP/RO target и изменение DB identity. Не выводить DSN/errors с connection credentials. Применить timeout/pool/search_path из исходного task.
- Первоначальная readiness требует успешной DB/schema проверки exact version+checksum и ожидаемой структуры, config/auth/assets. Не сравнение version>=1. После первоначальной валидации временный DB outage показывает disconnected/persistence degradation, но оставляет диагностическую UI доступной. Liveness не зависит от DB/K8s.
- Migration existing-object precheck, advisory xact lock/checksum ledger, atomic forward-only DDL. Поскольку G4 не запускался, подтвердить отсутствие ledger/runtime apply перед правками migration v1; если обнаружена уже применённая версия — не менять checksum задним числом, STOP на drift.

### F02, F09 — API contract и UI pagination

- Все 11 endpoints и error responses валидировать против неизменённого `docs/architecture/p8c/openapi.json`, включая required/nullable/enums/additionalProperties=false. Примеры: Nodes data.items, ready True/False/Unknown; Summary overall/subsystems/coverage; Backups отдельные velero/postgresql/policyGaps; Events storage/auditComplete/items.
- Структурированные Warning/Source DTO и null unknown вместо invented zero/empty success. Корректные 400/401/404/405/429/503, allowed query keys, filters/cursors. Unknown path не превращать в SPA success.
- Kubernetes list page<=200, continue handling, cap500/category, max4 concurrent, QPS5/burst10, per-request5s, cycle20s, без overlapping. Стабильная сортировка, partial/coverage при cap/error; нельзя показывать первый page как complete inventory.
- Cursor связан с immutable snapshot/filter/sort; expiry честно CURSOR_EXPIRED. UI умеет next page/filters/refresh и показывает incomplete/unknown вместо молчаливого обрезания.

### F03, F06 — фактические статусы и полнота источников

- Source registry с отдельным результатом каждого фактического GVR read. Ошибки не перезаписываются последующим fresh. Обновлять age при ответе, использовать реальные source observation timestamps. Failed/unsupported/timeout/403 не equivalent healthy empty list; для mandatory served API отсутствие данных — явно error/unknown.
- Overall/subsystem aggregation основана на Nodes Ready и pressure, workload kind-specific state, storage PVC/PV/snapshot observations, Velero BSL/backup/restore и CNPG/Barman. Базовая Kubernetes storage view не доказывает DRBD quorum. Не считать historic успешно пройденные restore/PITR текущим recovery test.
- VolumeSnapshot readyToUse читать boolean; absent/error -> unknown, false -> not-ready. Ready nodes считать по condition, не len(nodes). CNPG ready=0 не создаёт replicas=-1; primary из CR status, SQL всё равно только RW service.
- Подключить named GET `portal-db-daily`, `portal-db-backup`, `portal-gateway`, HTTPRoute `portal`; безопасные EndpointSlice ready endpoint counts; обе metrics node/pod usage с quantities, timestamp и window. Replica count inferred маркировать, не заявлять фактическую готовность реплик по недоказанному арифметическому вычитанию.
- Отдельные Velero и PostgreSQL backup DTO; age/phase/conditions/recovery mode/retention policy gaps из разрешённых источников. Barman три разрешённые metric families доходят до API/UI; отсутствие sample, NaN/invalid, body overflow и optional exposition timestamp обрабатываются честно. Один endpoint sample не доказывает состояние всех instances.
- UI overview: общий статус, Ready nodes3, DB3/3, storage scope/health, две backup области, warnings и latest timeline. Удалить hardcoded healthy; успешное чтение counts не есть здоровье. Fetch failure/stale >90s/unknown >5min заметны, без «нет предупреждений» при недоступном источнике. Реальные значения, русский операторский layout.

### F04, F05 — рабочая persistence/timeline

- Подключить цикл bounded persistence для observation_batches и Kubernetes Events/status transitions. Не хранить raw objects/events messages. Сформировать безопасные шаблонные сообщения из allowlisted codes, escaped text только в UI.
- Dedup по source identity/resourceVersion/count семантике; повторный poll неизменившегося Event не увеличивает occurrence_count. Source time и ingested time различать; idempotent retry не плодит batches/events.
- Реализовать bounded queue/backpressure, persistenceLag/dataLoss и memory fallback по исходному task. Ошибка записи видна, не объявляется DB_CONNECTED на основании одной прошлой миграции. DB retries конечные/с deadline.
- Prune через PostgreSQL17-valid CTE/subquery. TTL7d **ИЛИ** excess over caps20000/50000; выбор <=1000 идентификаторов за batch, bounded cleanup loop. Очистка только этих прикладных таблиц, не системных/P8A/P8B объектов. Без наружного destructive API.
- Readback nullable fields безопасен. Tests доказывают insert->API timeline, dedup, TTL независимо от cap, cap независимо от TTL, повторную migration no-op и mismatch rejection. DB failure тестировать изолированным fixture/test DB, не остановкой production DB.

### F08 — transport/security

- Kubernetes RoundTripper guard: GET only, fixed cluster host/scheme, exact permitted API path/resource/subresource rules, no redirects/custom host/proxy. Никаких пользовательских URL/verbs/GVR; RBAC остаётся основной границей. Metrics отдельный fixed URL client с timeout/body bound/no redirects.
- Вместо `err.Error()` в API — fixed bounded code/message; не логировать credential-bearing connection errors/Authorization. Проверить error paths fixtures с sentinel secret strings.
- HTTP server ReadHeaderTimeout/WriteTimeout/IdleTimeout/MaxHeaderBytes, bounded handlers/auth rate limits, graceful shutdown. Management8081 не включать в Service/HTTPRoute. Basic Auth только за HTTPS и restricted dataplane -> Portal ingress.
- Sanitize API/DTO/error/evidence; image без shell, os/exec только запрещён в runtime-приложении (Owner-side provisioning utility может вызывать разрешённый kubectl).

### Проверки R1

`go build`, `go vet`, `go test` и race tests на concurrency-критичных paths с фактическими outputs/exit codes. Contract tests на **все 11 реальных handlers**, а не только вручную изготовленные JSON fixtures. Negative fixtures missing/stale/403/404/429/timeout/malformed/null/partial/NotReady/failed snapshot/backup. Source static review F01–F10 closure matrix с file references и тестовым доказательством.

Migration/persistence integration tests запускать на разрешённом изолированном test PostgreSQL17, не создавать новый privileged builder/cluster и не писать test мусор в production schema. Если необходимый тестовый runner отсутствует — подготовить его в уже разрешённой CI среде без новых расходов; runtime gate остаётся закрыт до тестов.

R1 PASS только после закрытия всех findings. Одной успешной компиляции недостаточно.

## 4. R2 — NetworkPolicy decision D1

### Inventory и план до любого apply

Собрать санитарно безопасный inventory всех существующих Pods/controllers/jobs/services/endpoints/policies в portal, labels/ports/peers, DNS/API destinations, operator/control-plane paths, CNPG replication/application/instance-manager/exporter paths, Barman plugin/S3 TLS, monitoring/backup clients. Secret **values** не читать и не выгружать; CA/public certificates допустимы. Зафиксировать актуальные S3/API/DNS IP/ports из разрешённых источников; не угадывать CIDR или считать Service VIP гарантированным policy destination при DNAT.

Матрица `source selector/namespace -> destination selector/IP:port/protocol -> purpose -> evidence -> policy rule`. Входящие и исходящие стороны, существующие scheduled/on-demand control dependencies и kubelet host traffic учитываются отдельно. Для существующих sidecar/plugin соединений различить same-pod localhost/unix и сеть. Unknown peer/port, необходимость broad internet/SSH/BMC или смены CNI -> STOP до apply.

Сформировать exact new-object manifest и diff allowlist. Подтвердить effective union всех policies: узкая policy не отменяет старую широкую. Не считать kubectl dry-run доказательством связи/порядка применения.

### Безопасный порядок, разрешённый этим Architect decision

1. На существующих CNPG Pods первая выбирающая их policy `p8c-cnpg-existing-flows` содержит **полный проверенный ingress+egress allowlist в одном объекте**, включая DNS/API/S3/replication/operator/monitoring и точные Portal/migrator connections. Не применять отдельную DNS-only policy перед ней: первая allow тоже включает isolation. No temporary allow-all.
2. Если есть другие существующие pod classes, сначала отдельный полный allowlist для каждой; неизвестный workload -> STOP. Не редактировать их Pod labels/spec.
3. После каждого шага — ограниченный read-only health/flow check существующих clients/status. Любое ухудшение -> немедленно rollback только новых policies этого task к сохранённому исходному набору, STOP. Не ждать падения всего CNPG, не запускать failover/backup test.
4. Ввести `portal/baseline-default-deny-all` ingress+egress и `baseline-allow-dns-egress` по проверенному P4B DNS selector. Создать `p8c-portal-flows`, `p8c-migrator-flows` до соответствующих workloads: Portal ingress только от Portal Envoy dataplane TCP8080; egress DNS, Kubernetes API, CNPG5432 и metrics9187. Migrator только DNS/CNPG5432, без API. Management probes учесть согласно фактической CNI/node traffic semantics, не открывать8081 в LB/Service.
5. Новый Portal Envoy dataplane — exact Gateway-owned labels, complete listener/xDS/DNS/backend flow policy до допуска внешнего трафика. Existing Envoy controller/system namespace-wide deny не создавать. Если безопасно preselect future dataplane невозможно, STOP на concrete selector issue, не трогать controller spec.
6. Подтвердить actual effective rules и стабильность CNPG3/3/WAL condition/BSL/replication/control paths без destructive probes. Scheduled backups не форсировать. Не заявлять проверку не наблюдавшегося пути как runtime PASS — использовать evidence configuration+observed flows и явно указывать пределы.

Разрешённые новые NetworkPolicy имена выше и `p8c-portal-dataplane-flows` в фактическом namespace нового dataplane; expanded inventory-derived names фиксировать **до apply** в change-allowlist с точными selectors и основанием. Namespace-wide Deny за пределами portal не разрешён. Существующие infrastructure policies не удалять/не ослаблять.

R2 PASS: inventory complete, no unknown existing flows, policy YAML+effective union reviewed, apply/postcheck+rollback procedure documented. Если supply/auth/pull preconditions ещё не готовы, допускается подготовить всё read-only; не вводить live policies без необходимости deploy.

## 5. R3 — supply chain decision D2

Разрешён новый release workflow `.github/workflows/p8c-portal-release.yml`. Это CI build/sign, **не доступ в ПАК**.

- Manual workflow_dispatch only; `github.repository` exact и ref main; checkout exact `github.sha` данной main execution, проверка clean source tree и expected source SHA. Никаких произвольных checkout ref/command inputs, pull_request_target, fork execution, external download-and-execute без verification.
- `permissions: {contents: read, packages: write, id-token: write}` только release job. Checkout persist-credentials=false. Никаких kubeconfig/DB/S3/UI secrets в workflow. Доступность Actions и существующий бюджет/runner подтвердить; не включать платные сервисы/runner registration/менять account settings.
- Все actions — exact verified upstream commit SHA, версии и источники в lock/evidence. Не использовать mutable action tags как pins. tool versions/SHA сохраняются из исходного task; pinned Go download verify, go.sum/sumdb/mod verify, SBOM Syft, Trivy code/binary/OCI scan с version+DB timestamp, Cosign3.1.3. Не объявлять signature verified на основании checksum.
- Rootless BuildKit0.34.0 в разрешённой ephemeral hosted среде; никакого privileged build Pod/root/SSH на ПАК. Scratch final image содержит только нужный binary/static assets; provenance commit/build args; фиксированный build timestamp от commit для воспроизводимости, source revision полный40hex. Сборка source tree до manifest/evidence follow-up commits связана явными SHA.
- Две чистые сборки должны дать одинаковый application binary/image либо конкретное объяснение metadata-only различий с воспроизводимой командой; не выдавать текущее `date`/mutable tool download за reproducibility.
- `ghcr.io/dedvmedved-dot/otus-diplom-portal` только private. Первый push через workflow GITHUB_TOKEN с repo linkage; existing package rights/visibility проверить. Никаких PAT write:packages в чат/репозиторий. Ошибка доступа -> BLOCKED с concrete action/permissions, не смена registry/visibility.
- SIGN/VERIFY exact digest, exact identity из D2 и exact issuer. Проверить SAN/workflow/ref/source SHA, provenance subject/SBOM subject/digest. Сохранить bundle/public certificate/transparency proof, immutable evidence refs и результаты verification. При public transparency не публиковать credentials/internal payloads.
- Build logs/artifacts в public repo публикуют только sanitized application source/tool/scan metadata; не runtime inventories, DSN, private registry credentials или secrets.
- Scan HIGH/CRITICAL и лицензий — исходный gate, без bypass/автоматического acceptance CVE. Если исправление требует смены pinned version, отдельный STOP с конкретной безопасной версией/официальным источником; не silently latest.
- Private kubelet pull: `portal/portal-registry-pull` с protected credential, имеющим только необходимые read:packages и доступ к этому package. Новый Owner credential не создавать от его имени; не хранить GITHUB_TOKEN из job для future pulls. Secret reference в Deployment/Job, API read Secret permissions Portal не получает. Отсутствие долгоживущего разрешённого pull mechanism -> отдельный BLOCKED_REGISTRY_PULL; public fallback запрещён.
- Финальные deployment/Job refs `@sha256:<actual-verified>`, lock со статусами и доказательствами. Проверить registry pull и затем runtime imageID соответствие manifest/platform digest mapping. Placeholder не применим и не PASS.

R3 PASS — build/tests/SBOM/scan/provenance/signature/private push+pull доказаны; architecture approval само по себе не PASS.

## 6. R4 — Owner provisioning и final pre-deploy gate

### UI password

Owner хранит base64url encoding32randombytes (43 ASCII chars, без padding) в своём password manager. Это login password; SHA256 вычисляется от точной ASCII строки. Не отправлять пароль или verifier в чат/Hermes report.

Hermes подготовить `portal/tools/provision-ui-auth.py` и короткую инструкцию:

```text
python3 portal/tools/provision-ui-auth.py --context <explicit-approved-context>
```

Helper Owner-side only, не запускается agent/CI. Getpass без echo дважды; no logging/argv/env/raw temporary files; проверка формата/совпадения. Фиксированные namespace/name/key, context обязателен, никаких permissions changes. SHA256 вычисляется в памяти; JSON Secret создаётся через stdin существующего защищённого kubectl/client, output capture; не `--from-literal`, не apply last-applied annotation с data. При existing Secret — no overwrite/no rotation, STOP с безопасным сообщением. На success только namespace/name/key/status, без verifier/hash/password. Ошибки не печатают request body/credentials. Обеспечить локально отсутствие session recording/debug; helper не обещает очистку всей памяти ОС. Tests synthetic/mock, без production Secret чтения.

Owner должен выполнить этот последний credential шаг сам; Hermes получает только подтверждение provisioning metadata. Runtime mounts/validation/login test доказывают правильность. Если Owner не имеет разрешённого context/secure manager — concrete BLOCKED, без нового SSH/root/login обхода.

### Private image pull

Если уже есть подходящий Owner-managed pull Secret/механизм, использовать после проверки metadata/access без dumping data. Иначе подготовить аналогичный Owner-side helper `portal/tools/provision-registry-pull.py`: getpass для разрешённого read-only package token, `.dockerconfigjson` только в памяти/stdin, фиксированный Secret `portal-registry-pull`, без logging/data-in-argv, без перезаписи существующего Secret. Owner выбирает/создаёт credential в своём защищённом интерфейсе; secrets не передаются через Hermes. Record только name,type,access verification,expiry/rotation responsibility. Не просить admin PAT.

### G3 closure

До production apply проверить одновременно: R0 healthy, F01–F10 closure, R3 supply chain, auth/pull ready, complete R2 policy plan, DB privileges/schema/CA, cert-manager/Gateway capability, свободный actual LB allocation и approved client trust path. Подготовленные manifests/schema dry-run и exact allowed diff. Не перепутать create/update инженера для **названных Portal объектов** с запрещённым write RBAC приложения.

Дополнение к change-allowlist: новые policies по R2; новые protected UI/pull Secrets (values OUT_OF_BAND); projected API CA/token wiring; исправленные Portal manifests; workflow/source/test/docs/evidence. Certificate Secrets управляет cert-manager. Readonly references на существующие portal-db-app/DB CA; их значения/права не менять. БД принимает только новые application tables и ограниченную lifecycle очистку этих таблиц.

Live policy rollout выполнять только при готовности перейти к migration/deploy. После rollout ещё раз health check. При любом unmet precondition не запускать G4, не считать G3 закрытым «решением Architect».

## 7. R5 — выполнить исходные G4–G7

1. Migration Job на verified image, portal-migrator/no token, fixed DB contract. Completed<=120s; SQL session TLS protocol/cipher/servername verification evidence без credential; `current_user`, DB/schema, non-superuser и exact ledger/checksum. Подтвердить repeat no-op безопасным runner validation, drift negative только fixture. Migration failure -> STOP, no web deploy.
2. Portal Deployment+Service+metrics Service Ready, real `/startupz`, `/readyz`, `/livez` и `/api/v1/health`. Independent read-only source projections в том же временном окне, не только self-reported Portal. Реальные DB observation rows/timeline readback; empty history не заменяет event pipeline proof.
3. TLS Certificates Ready, dedicated Gateway/HTTPRoute accepted/programmed/resolvedRefs по actual observedGeneration. Новый LB IP фактически выделен и свободен; не hardcode .110. Owner/test client доверяет только public UI CA в выделенном профиле. HTTPS hostname `portal.demo-pak.test`; без `-k`, без browser certificate-warning bypass, no port80 fallback. Controller infrastructure не изменять.
4. Проверить все11 API responses against OpenAPI + независимые источники, authenticated UI/assets и rejected unauthenticated access; methods/query/cursor errors. Подготовить sanitized browser screenshots overview+sections (real nodes/DB/storage/backup/timeline), отсутствие console errors. UI tests pagination/freshness/error states через fixtures; production dependency outages не вводить.
5. RBAC full allow/deny matrix, exact groups/identity impersonation. Один ConfigMap create на unique nonexistent name с `dryRun=All` от portal-reader -> HTTP403 именно RBAC; подтвердить отсутствие объекта. Никаких real writes/deletes ради negative test. Если не403 — FAIL/STOP.
6. Effective NetworkPolicy, runtime digest, securityContext/capabilities, no host mounts/shell/secret read. Secret scan source+rendered manifests+evidence+logs перед публикацией; actual credentials не извлекать ради сравнения, использовать synthetic sentinels/static patterns и redaction.
7. Platform postcheck read-only: nodes3/3, CNPG3/3/WAL/replication, BSL, ScheduledBackup/ObjectStore без неразрешённого spec drift, Gateway healthy; сохранить pre/post fingerprints. Background planned activity не считать нашей mutation; не стирать реальные изменения.

## 8. R6 — evidence, Git, failure handling

Минимальные группы нового evidence:

| Группа | Обязательное доказательство |
|---|---|
| Recovery | exact initial HEAD/ancestry/diff, commands+raw safe precheck projections, timestamps |
| Source closure | F01–F10 matrix, build/vet/test/race outputs, all11 contract tests, failure fixtures, DB integration tests |
| Network | existing flow inventory, exact selectors/ports, effective union, policy source hashes, apply sequence, rollback recipe, healthy postchecks |
| Release | workflow source SHA/run URL/runner identity, tool verification, binary+image digests, SBOM, scans+DB timestamp, CVE disposition, provenance, signature verify/public bundle, private visibility/pull proof |
| Secrets | helper synthetic tests/review, provisioning metadata only, secretKeyRef projections, no plaintext artifacts |
| Database | migration SQL/checksum/ledger, TLS+role evidence, actual insert/readback, bounded retention result, no infrastructure tables changed |
| Application | probes, Deployment/Service/EndpointSlices,11 API JSON samples, source comparison, pagination/freshness/error fixtures |
| Ingress/UI | cert public fingerprint, Gateway/HTTPRoute statuses, assigned IP, HTTPS response, real browser screenshots |
| Security/postcheck | RBAC matrices+dryRun403, no object created, safe transport tests, secret scan, runtime imageID, full postcheck/spec fingerprints |

Каждый PASS связан с output и command/exit code, а не только таблицей утверждений. SANITIZED не означает выдуманный вывод; отсутствующее evidence -> NOT_VERIFIED. Capture только нужные поля, не raw Pod specs/env/secrets/Secret YAML. Binary/SBOM large artifacts — immutable permitted references+checksums, без больших binaries в Git.

При утечке credential — STOP на дальнейшее распространение; не коммитить/не замазывать прошлую историю молча. Owner решает rotation безопасным каналом. Старый compromised S3 password не искать/не запрашивать.

Git: main sole SoT; один логический шаг — осмысленный commit. Перед каждым push fetch main и объяснить diff, secret scan, clean tree. Только fast-forward/no-force. Не переписывать accepted evidence и прошлый `result.md`; новый review/rework result ссылается на него. На concurrent unexpected main change — STOP, не auto-resolve историю.

Сначала source/helpers/workflow с lock+tests; затем verified release refs и manifests; затем runtime/evidence commits. Не собирать образ из uncommitted source и не представлять последующий evidence commit как embedded build revision. Документировать source SHA -> CI run -> digest -> runtime -> evidence HEAD.

## 9. R7 — STOP AND REPORT

После выполнения или адресного blocker сообщить:

```text
TASK: P8C-R1 RESUME PORTAL MVP
INITIAL_REMOTE_MAIN_SHA:
APPLICATION_SOURCE_SHA:
RELEASE_WORKFLOW_RUN:
IMAGE_DIGEST:
FINAL_REMOTE_MAIN_SHA:
F01-F10_CLOSURE:
G0/G1/G2/G3/G4/G5/G6/G7/G8:
PORTAL_UI: RUNNING | NOT_DEPLOYED | FAILED
PORTAL_API: RUNNING | NOT_DEPLOYED | FAILED
PORTAL_DB: CONNECTED | NOT_CONNECTED | DEGRADED
PLATFORM_STATUS: VISIBLE | NOT_VISIBLE | PARTIAL
PORTAL_URL: <verified HTTPS URL or NONE>
BLOCKERS: <precise unmet gate + safe next action; never credentials>
HERMES_RESULT: PASS | BLOCKED | FAIL
P8C: NOT_FINAL_ACCEPTED
P8D-P8G/P9: NOT_AUTHORIZED
```

Не присваивать себе CONNECTOR VERIFIED/FINAL ACCEPTED. Даже при рабочем UI final acceptance требует независимого Connector audit Chief Architect. Runtime не запускать на основании одного этого документа, пока Owner не передал task Hermes; никакой автоматической отправки/запуска при публикации документа.
