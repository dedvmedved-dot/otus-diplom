# TASK: P8C-R1 RESUME-R2 — correctness and Owner readiness

Дата: 2026-10-20. Chief Architect. STATUS: PREPARED FOR OWNER DISPATCH.

## Решение после независимого Connector review

Проверен main `17fdf97b96ab19498d973f969bddc6244cb95af0`, tree `43eab119d3b576de221ea937652d87a9545569c5`. Compare от `8f7acffd05b7814a56a03e5feaaf82cbeeb87eae`: 3 commits ahead, 0 behind, 27 changed files в Portal и новом evidence. Пакет существует, изменения полезны, runtime не развёрнут по опубликованному отчёту. Live runtime Architect в этой сессии не опрашивал.

**G1/F01–F10 closure не принимается. Статус: REWORK_REQUIRED, а не только OWNER_BLOCKED.** R2 policy plan и R3 workflow не READY_FOR_APPLY/RUN. Два Owner helper в проверенной версии не запускать с настоящими credentials. Ни права workflow, ни Secret provisioning не нужны для исправления нижеперечисленных дефектов.

Сохраняются решения D1–D3 из `docs/architecture/P8C_R1_ARCHITECT_REVIEW_AND_DECISION_20261020.md` и требования `docs/tasks/TASK_P8C_R1_RESUME_PORTAL_MVP.md`. Этот task адресно закрывает обнаруженные остатки, не расширяет P8C. Не переписывать прежние evidence/заявления PASS: новое evidence отдельно фиксирует корректирующее решение.

## Проверенные остатки и требуемое доказательство

### R2-01 — Owner helpers: create-only и fail-closed

Факт: оба `portal/tools/provision-*.py` после любого ненулевого результата `get secret` выполняют `kubectl apply -f -`. `Forbidden`/network failure трактуются как отсутствие. Apply способен изменить существующий Secret при гонке и создаёт last-applied annotation с конфигурацией Secret. Это прямо противоречит исходному заданию. Локальный mock воспроизвёл write attempt и exit0 после Forbidden у обоих helpers; реального Kubernetes доступа не было.

Исправление:

- Единственная операция записи — atomic `kubectl create -f -` через JSON stdin, без save-config/apply/patch/replace/force. AlreadyExists/409 -> STOP, без retry overwrite. Сам create гарантирует no-overwrite при гонке.
- Проверку существования либо убрать (create-only достаточно), либо различать отсутствие и прочие ошибки: `--ignore-not-found -o name`, success+empty допускает create, success+name -> STOP, любой nonzero -> STOP без записи. Не распознавать NotFound по свободному тексту stderr.
- Требовать защищённый интерактивный ввод до чтения секрета: getpass fallback/`GetPassWarning`/EOF/non-TTY -> STOP до записи, без echo. Нельзя полагаться только на комментарий «no echo».
- Catch timeout/OSError/encoding/input errors, ограниченные безопасные сообщения; subprocess timeout; никаких captured stderr/request body/tracebacks с credentials, argv/env/temp files. No implicit rotation. Пароль по-прежнему генерирует/хранит Owner, verifier вычисляется от точной строки.
- Registry dockerconfig: оставить один согласованный способ auth, удалить фиктивное `password: REDACTED`; при auth-only кодировать фактическую разрешённую identity. Не считать имя владельца repo универсальным registry username: Owner вводит username соответствующего read-only credential, либо явно документируется и проверяется фиксированная identity. Токен не печатать.
- Mock tests: success, exists, forbidden, network error, AlreadyExists race, create denied, timeout, отсутствующий kubectl, non-TTY/getpass fallback. Проверить отсутствие secret material/annotations/записи при ошибке и no-overwrite. `py_compile` не заменяет эти tests.

### R2-02 — Kubernetes transport блокирует собственные разрешённые запросы

Факт: `newClients` передаёт `cfg.Host` в guard. В upstream client-go v0.36.2 `InClusterConfig` устанавливает `Host: "https://" + net.JoinHostPort(host, port)`. Guard сравнивает `req.URL.Host` с полным cfg.Host. `host:port != https://host:port`; реальные разрешённые запросы будут отвергнуты до отправки.

Исправление: разобрать/валидировать canonical base URL один раз; сравнивать scheme, hostname/port/authority корректно, без userinfo и alternate Request.Host. Ввести exact path/GVR/subresource allowlist исходного task, запрет proxy/log/exec/Secret paths и redirects. Request deadline5s, cycle20s. Tests обязаны включать **положительный** разрешённый запрос, а также wrong host/scheme/path/method/redirect. Проверка только deny недостаточна. Тестирование через fake transport, без platform API mutation.

### R2-03 — frontend остался на старом API

Факт: `portal/web/app.js` не изменён в resume diff. Он вызывает `(nodes.data || []).map`, ожидает summary.overallHealth и прежние DB поля; backend теперь отдаёт data.items/overall/readyInstances. Локально воспроизведены TypeError на list endpoint и unknown вместо переданного healthy. В UI по-прежнему hardcoded healthy для storage/Velero/workloads; string `"False"` нельзя проверять как boolean readiness.

Исправление: привести **все** UI sections к текущему утверждённому OpenAPI, включая structured warnings/backup domains/Barman/events, null/empty/error/stale, pagination, current warnings+recent events на overview. Убрать invented green и ложное «нет предупреждений» при недоступности. Tests на реальных JS renderers с contract-shaped responses и browser smoke в изолированной среде, без credentials/production API. Screenshot показывает полезные реальные либо явно помеченные fixture данные; fixture screenshot не runtime evidence.

### R2-04 — contract/freshness/pagination остаются неполными

Факты: envelope выдаёт nil slices как null для sources/warnings, хотя schema требует arrays. Subsystem observedAt создаётся `time.Now()` при ответе, ageSeconds источников заморожен при сборе. Health/subsystem aggregation не учитывает возраст должным образом; application-db всегда unknown в summary. Nodes subsystem игнорирует node.Health pressure warnings. Cursor не привязан к endpoint/filter и несколько раз читает текущий snapshot, допускает смену snapshot между parse/data/cursor. Kubernetes Lists преимущественно читают только один page; continue не проходит полноценный цикл, backups используют Limit500. Events читает top200 до namespace filter, дальнейшие строки недоступны. Эти детали не подтверждают заявленное полное F02/F03/F09 closure.

Исправление: non-null empty arrays где требует contract; source timestamps не подменяются временем HTTP ответа; вычислять текущий возраст и честную degradation; coherent snapshot один на весь ответ/cursor. Cursor должен связывать resource+filter+snapshot и корректно истекать; sorted continuation до cap500 с page<=200 и coverage warnings. Event filtering/pagination на согласованном DB/query snapshot, без скрытой потери строк. Проверить missing/error/stale/partial pressure и schema validation всех 11 реальных handler responses, включая error/empty cases и пределы массивов.

### R2-05 — persistence пока искажает историю и скрывает ошибки

Факты: persistOnce создаёт новый random batch ID даже для того же snapshot; event key не содержит UID/resourceVersion; каждое повторное UpsertEvent увеличивает occurrence_count. Ошибки UpsertEvent/Prune игнорируются; LagSeconds устанавливается0 даже при InsertBatch failure. Nullable SQL columns всё ещё сканируются в plain string. /events при DB failure возвращает503 без предусмотренного memory fallback; status-transition events отсутствуют. Исправление синтаксиса CTE полезно, но не закрывает F04/F05.

Исправление: identity/source count-aware dedup и idempotent retry; bounded queue/backpressure/deadline; достоверный lag/dataLoss на **всех** путях записи/cleanup; безопасное nullable scanning; bounded memory fallback и status transitions исходного task. Не фиксировать overall_health='unknown' независимо от вычисленной оценки. Изолированные PostgreSQL17 integration tests: insert/readback, unchanged event не увеличивает count, новый source count обновляется, recreated object UID не склеивается, повтор batch не дублируется, NULL fields, TTL отдельно от cap, event/cleanup failure виден, fallback ограничен. Production DB не останавливать, тестовые failure scenarios только локальные fixtures/test DB.

Дополнительно закрыть DB startup/TLS требования исходного task: explicit minimum TLS/servername/no ambient overrides, exact ledger+structure validation, bounded initial retry и сохранение диагностической UI после успешной первичной validation. Migration v1 не менять после фактического применения; пока проверить historical NOT_EXECUTED.

### R2-06 — workflow template не готов для публикации/dispatch

Факты в `portal/tools/p8c-portal-release.yml.template`: `ubuntu-latest`; docker build вместо pinned rootless BuildKit0.34.0; mutable image :latest; Syft dir SBOM не привязан к final image; `trivy rootfs ./portal` направлен на binary file, отсутствует итоговый OCI scan; GO_SHA256 объявлен, но не используется шагом setup; cosign-installer без version input не фиксирует Cosign3.1.3. Нет cosign verify exact identity/issuer, provenance generation/verification и сохранения всех proof artifacts. Комментарий о необходимости будущей проверки action SHAs не является verification evidence.

Исправление: выполнить **все** требования R3 исходного resume task: exact verified tools/actions, reproducible source SHA/build metadata, pinned rootless builder, immutable candidate digest, binary/final OCI SBOM+scan, safe private push, Cosign3.1.3 sign+verify exact D2 identity/issuer+source/digest, provenance/SBOM subject match, retained artifacts and private visibility proof. Race/contract/DB integration tests не пропускать. Никакого CI доступа в ПАК, новых расходов, public registry fallback, credentials в logs. Не называть runtime source SHA ee1fc1d после дальнейших source изменений: записывать фактический source commit workflow execution.

Разрешена доработка template и build/test scripts **без** workflow scope. Проверить YAML/schema/action pins и доступные build/scan этапы на уже разрешённом builder. Signing/push без доступа честно NOT_EXECUTED. Не пытаться обойти GitHub permission denial или добывать более широкий credential. Сохранить sanitized фактическую ошибку отказа если она доступна; текущий evidence файл лишь сообщает NOT_RUN и не содержит ответа GitHub. Не реконструировать старый response.

После исправления возможен Owner web-editor handoff вместо нового PAT: Owner с правом записи создаёт `.github/workflows/p8c-portal-release.yml` из **проверенной** template через GitHub UI, затем manual dispatch. Это самостоятельное действие Owner с его доступом, не обход ограничений текущего токена. Новый broad PAT не является единственным решением. Текущую template не публиковать/не запускать.

### R2-07 — NetworkPolicy inventory ещё не достаточен для apply

Факт: PLAN содержит описательный список без требуемой полной source-selector -> destination:port -> evidence матрицы и exact policy manifests; instance-manager указан8008. Upstream CNPG1.30 указывает status/instance-manager TCP8000. Не переносить ни8008, ни8000 вслепую: сверить фактические Pod ports/operator paths и сохранённый runtime inventory. Название API VIP не доказывает destination Kubernetes Service после DNAT; фактический in-cluster путь и dataplane selectors/xDS должны быть проверены.

Исправление: полная матрица D1 с actual namespace+labels+ports+purpose+raw safe source refs, exact YAML/union/rollback, без unknown flows и broad allows. Данные из другого namespace не называть Pods в portal. Никаких live NetworkPolicy до готовности deploy по прежним gates. Без SSH/root к узлам, packet disruption, новых backup/failover tests. Scope остаётся portal+точно выбранный новый Envoy dataplane.

### R2-08 — evidence не доказывает заявленное полное closure

В проверенном tree только 3 Go test files: auth, metrics parser, query/pagination helpers. Нет всех11 handler contract tests, transport positive tests, DB integration и Owner helper negative tests. `03-build-test-race.txt` — четыре строки PASS/exit0 без командного transcript/package results/source/tool identity; это сводка, а не требуемые raw outputs. Не объявлять race coverage code path, который тесты не исполняют.

Собрать fresh evidence из actual execution исправленной ревизии: source SHA/clean tree/go version/command/UTC/exit code/package output; test-case matrix -> R2-01…08; reproducible commands; negative outputs сохранять. Исторические результаты не редактировать. Architect не утверждает, что Go build не выполнялся; он не может подтвердить этим пакетом полноту и заявленное closure.

## Исполнение одним законченным пакетом

1. Recovery origin/main/ancestry/clean diff; прочитать этот task и оба предыдущих. Если main содержит только новый Architect docs/evidence commit поверх review target, это ожидаемое продолжение, не повод откатываться на17fdf97.
2. Самостоятельно закрыть R2-01…08 в исходниках, тестах, plan и template. Source/tool verification и safe read-only inventory разрешены. Не ждать Owner credentials ради этой работы. При недоступном конкретном внешнем ресурсе продолжить независимые действия и точно отделить remaining gate.
3. Полная source-level validation всего исправленного MVP: Go build/vet/tests/race meaningful paths, actual11 handler schema tests, JS integration/smoke, helper safety tests, isolated DB integration, workflow validation. Проверить взаимодействие UI/API/DB, не только отдельные функции. Не добавлять framework/SSO/P8D integration и не ослаблять OpenAPI под код.
4. Оформить один reviewable пакет и свежий evidence index с closure matrix. Git commits по логическим шагам, fast-forward/no force, exact source provenance, secret scan. Не изменять accepted infrastructure/history.
5. Отдельно подготовить короткую Owner-инструкцию с точным reviewed commit/hash template и helpers: (a) publish via authorized GitHub UI/approved credential and dispatch; (b) own UI password provisioning; (c) protected read-only private registry pull credential. Никаких настоящих credentials для проверки helper; не просить secrets в чат. Указать проверку AlreadyExists без ротации, expected safe success и rollback/expiry responsibility.
6. STOP AND REPORT для независимой проверки исправленного source/Owner package. До этой проверки Owner helpers и workflow dispatch не выполнять, G3 не закрывать; live NetworkPolicy/migration/Portal deployment остаются NOT_EXECUTED. Это целевой gate из-за воспроизведённых дефектов, не переоткрытие P8A/P8B.

## Критерий результата и ограничения

Ожидаемый отчёт: INITIAL_MAIN_SHA; FINAL_MAIN_SHA; SOURCE_SHA; R2-01…08 factual disposition; test/evidence refs; WORKFLOW_TEMPLATE_REVIEW_READY; OWNER_HELPERS_REVIEW_READY; NETPOL_PLAN_REVIEW_READY; remaining external permissions отдельно. `HERMES_RESULT=PASS` возможен для **source corrective package**, не Portal runtime/FINAL ACCEPTED. Непройденные проверки -> BLOCKED/FAIL, не общая фраза «всё закрыто».

P8C остаётся IN_PROGRESS / NOT_FINAL_ACCEPTED. P8D–P8G/P9 NOT_AUTHORIZED. Backup/latest restore/PITR/P8A failover/P7/P7C failures не повторять. Source review не является runtime validation. Model/provider policy и запрет самовольной multi-agent делегации сохраняются.

## Источники и воспроизведение

- Immutable project source: https://github.com/dedvmedved-dot/otus-diplom/tree/17fdf97b96ab19498d973f969bddc6244cb95af0/portal
- client-go exact tag: https://github.com/kubernetes/client-go/blob/v0.36.2/rest/config.go (Connector read; InClusterConfig Host includes https://).
- https://kubernetes.io/docs/tasks/manage-kubernetes-objects/declarative-config/ (apply/last-applied semantics).
- https://cloudnative-pg.io/docs/1.30/security/ (instance manager/status port8000; runtime verification still required).
- https://docs.github.com/en/actions/get-started/quickstart (Owner can create workflow through authorized GitHub web UI).
- Local mock evidence: `evidence/P8/20261020-p8c-resume-r2-architect-review/reproduction-results.json`; reproducer принимает checkout root17fdf97. Mocked subprocess не обращается к Kubernetes; browser renderer test использует synthetic responses. Это failure reproduction, не production tests.
