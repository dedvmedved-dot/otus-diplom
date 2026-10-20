# P8C-R1 RESUME-R3 — Architect review c3cfec6

Дата: 2026-10-21 (Europe/Moscow).
REVIEW_TARGET_MAIN: c3cfec621f87fb496f35099b08bc3feeb00ba309
APPLICATION_SOURCE_SHA: ffed5d83feffaa91c75bb42cce0b3d48f936078c
REVIEW_TARGET_TREE: 8f755827dec7c215e8910d95efed45be32010c54
DECISION: REWORK_REQUIRED (source package is not fully closed).
P8C: IN_PROGRESS / NOT_FINAL_ACCEPTED.

## Recovery и граница проверки

GitHub Connector независимо подтвердил HEAD, recursive tree, source/evidence и сравнения:
90f626b→c3cfec6: 2 ahead, 0 behind, 9 files в Portal/new evidence.
ffed5d8→c3cfec6: только четыре новых evidence-файла.
Существующие P8A/P8B acceptance и infrastructure не переоткрывались. Неожиданного delta вне заявленной области нет.
Прочитаны все Portal source/manifests/tests/template (кроме неизменённого go.sum), OpenAPI и новый evidence.
Наличие пакета и ancestry CONNECTOR VERIFIED; полное A–G closure НЕ подтверждено.

Действует `docs/tasks/TASK_P8C_R1_RESUME_R3_CLOSURE_EXECUTION.md` от e2cfd53.
Этот review — адресный остаток того же задания; новая стадия/расширение scope не разрешены.
Исправление примеров ниже не заменяет полноту acceptance criteria R3 A–G.

## Принятый прогресс — не повторять без регрессии

- Исторический getpass echo-fallback удалён; atomic create-only и UNKNOWN_OUTCOME сохранены. Самостоятельно повторены опубликованные14 helper tests: PASS. Остаток EOF/cancel — RV-07.
- Cursor теперь содержит endpoint/namespace; nil envelope arrays, requireNoQuery health, dynamic source age, application-db Ping и node pressure добавлены. Не считать это закрытием всей coherent pagination/freshness модели (RV-04).
- Deterministic batch ID + ON CONFLICT DO NOTHING, nullable object fields, обработка Prune error присутствуют.
- Integration suite использует actual embedded migration, отдельную disposable test DB, reset schema между последовательными tests, recorded_at для TTL, 20005 rows для cap, checksum/ledger mismatch. Опубликованный transcript содержит6 PASS. Architect признаёт наличие source и execution evidence Hermes; сам PostgreSQL/Go здесь не запускал.
- Реальный jsdom renderer test теперь существует; transcript содержит его PASS. Error-vs-empty и Health cell изменены. Остатки factual UI — RV-05.
- Raw transcript стал содержательнее прежней сводки; не утверждается, что Hermes не выполнял tests. Он не доказывает отсутствующие сценарии или полное closure.

## Остатки и обязательные regression checks

### RV-01 / R3-E — release template всё ещё нельзя публиковать/dispatch

Файл: `portal/tools/p8c-portal-release.yml.template`.

1. BUILDKIT_VERSION=`0.34.0`, а URL строится как releases/download/0.34.0/buildkit-0.34.0.linux-amd64.tar.gz. Официальный tag/asset через Connector: **v0.34.0 / buildkit-v0.34.0.linux-amd64.tar.gz**. Исправить source URL; не угадывать names.
2. Cosign checksum template `9d6f25a9a4dcd0dd097e4f45a76cba8ddc9d40c980a25c9150d33d85d8b4a19d` противоречит официальному digest cosign-linux-amd64 v3.1.3 и versions.lock:
`4629c757b7618056f8ddd7e2625ae9fdd94c0372a65049520bc7d9df9efc7f71`.
Не отключать checksum gate. Сверить фактические bytes с первичным источником; metadata verification Architect не является byte verification.
3. RootlessKit SHA/archive layout/prerequisites не доказаны. Template предполагает rootlesskit/bin/rootlesskit, использует slirp4netns, устанавливает только uidmap. Проверить фактический asset layout, зависимости, socket и non-root builder health. RootlessKit release существует; его checksum Architect получить не смог (Connector404/web fetch disabled), поэтому здесь НЕ объявляется неверным.
4. Go checksum выполняется только `if [ -f "$dl" ]`; отсутствие архива молча пропускает проверку, release job её вообще не делает. Сделать гарантированную проверку используемого toolchain, verified action pins.
5. test job запускает только fixture-smoke.test.mjs; renderer-smoke.test.mjs не вызывается. Нет committed package.json/lock для jsdom; package-lock.json игнорируется. Добавить pinned test-only dependency + lock и reproducible install/run. Framework в runtime не добавлять.
6. Provenance/SBOM attestation generation+verify по D2 отсутствует; upload сохраняет только SBOM, без signature/verification/scan/build metadata/provenance. Добавить exact identity/issuer/source/digest/subject проверки и retained artifacts с fail-on-missing; scope job permissions минимальный.
7. Private package visibility proof и pull wiring отсутствуют. Ни Deployment/Job, ни их ServiceAccounts не ссылаются на portal-registry-pull. До deploy зафиксировать явную привязку без credentials в Git.
8. Candidate digest непустой — недостаточный test: строгая sha256 форма, registry verification именно pushed artifact, никакой повторной сборки для определения digest.

Regression/acceptance: validate expanded URLs/checksums/asset layout and script syntax; actual allowed local rootless build/scan where available; test job executes renderer + DB integration; all mandatory artifacts declared and generated. Private push/sign по-прежнему NOT_EXECUTED до разрешённого CI Gate. Не выдавать описание template за прошедший release.

### RV-02 / R3-F — Gateway/NetPol cross-file mismatch

Файлы: `portal/manifests/{gateway,networkpolicy,deployment,rbac}.yaml`, `portal/networkpolicy/PLAN.md`.

Gateway + HTTPRoute/RBAC используют `portal-gateway`; Portal ingress и dataplane NetPol ищут `gateway.envoyproxy.io/owning-gateway-name: pak-portal-gateway`. Это несогласованная identity: Portal ingress не пропустит intended dataplane с canonical Gateway label.
Новый dataplane policy разрешает egress только DNS53 и backend8080; xDS/controller flow отсутствует. После исправления selector он будет изолировать egress без полного control-plane flow inventory.

PLAN по-прежнему содержит8008, нет actual selector→destination:port→raw evidence matrix, API egress всё ещё /24:6443 без доказанного service/DNAT path. Комментарий «verified, transcripts in evidence» не заменяет ссылку на конкретный raw safe runtime вывод.

Исправить согласованность canonical Gateway name+namespace/labels (проверить оба owning labels), full listener/xDS/backend/DNS matrix, actual CNPG/operator/monitoring/S3/API flows и точный rollback. Actual read-only inventory допустим; live policies не применять. Не использовать blanket allow и не угадывать dataplane port/labels.
Regression: offline flow/selector tests по реальным manifests, включая migration5432, Portal9187, intended Envoy8080, denied unrelated Pod, xDS egress и absence of system-namespace-wide deny. Подтверждённые CNPG/migrator ingress fixes сохранить.

### RV-03 / R3-B — guard запрещает собственный EndpointSlice collector

`collect_methods.go` вызывает `DiscoveryV1().EndpointSlices("").List`, RBAC правильно разрешает discovery.k8s.io.
Но transport allowlist содержит `endpointslices` в core resources и НЕ содержит `discovery.k8s.io/v1/endpointslices`.
Тест позитивно проверяет несуществующий core path `/api/v1/endpointslices`; настоящий path `/apis/discovery.k8s.io/v1/endpointslices` будет отвергнут.

Исправить allowlist и тестировать запросы фактических typed/dynamic clients через fake transport, а не вручную выдуманные routes.
Также R3-B требует exact namespace/named GET restrictions, HTTPS canonical validation и per-request5s deadline: текущий grammar разрешает любые namespace/name для approved GVR; newClients не задаёт request timeout, только cycle20s в collector. Не ослаблять RBAC.
Regression: actual path каждого collector допускается, unapproved collection/named object/ns/subresource/host/scheme отвергается; deadlines наблюдаемы.

### RV-04 / R3-C — pagination и contract ещё частичны

- `listWithContinue` усечение исправлено, но вызывается только для Pods с cap=listPage=200; остальные List одностраничные, backups Limit500. Сам collector не изменён этим финальным delta.
- snapshot всё ещё отдельно читается при query parsing, данных и encode cursor. Нужен один coherent snapshot per response.
- events cursor не связан с since/severity; SQL OFFSET идёт по меняющемуся набору, upsert меняет ingested_at. Нет стабильной query boundary; нет binding к DB/memory mode.
- health/summary/subsystem state не учитывает старение snapshot должным образом; dynamic ageNumbers сами по себе не меняют status.
- fallback Database.Conditions остаётся nil, а schema требует array; проверка envelope fields этого не замечает.

Довести существующие требования R3-C: все Lists page<=200/до cap500 с coverage warnings и tests на201/501 objects; cursor endpoint+filters+snapshot/backend mode; устойчивое events paging при concurrent update; nil/stale/error/partial schema cases. Не править OpenAPI под дефекты.
Frontend должен дать доступ к следующим страницам, а не только написать о наличии cursor (RV-05).

### RV-05 / R3-C — UI всё ещё искажает факты

Самостоятельно выполнены actual app.js renderers в Node VM с synthetic DOM/fetch (не browser):
- `storageHealth([{health:'unknown'}])` возвращает healthy.
- setOverall('critical','stale') меняет красный critical на warning; подпись остаётся critical. Для stale healthy тоже остаётся healthy текст, а карточки Nodes/DB не учитывают freshness.
- Barman API/model/OpenAPI поле **firstRecoverabilityPointTimestamp**, UI читает **firstRecoverabilityPoint**. Реальное значение1792469710 не отображается. Renderer test использует тот же ошибочный fixture key, поэтому ошибку пропускает.
- schedule/target выбираются из expectedSchedule/expectedTarget прежде наблюдаемых schedule/target: расхождение фактической политики скрывается.
- null lastFailedBackupTimestamp показан как0; WAL state/ContinuousArchiving не показаны, только expected timeout.
- nextCursor используется лишь для текстового примечания в Events. Нет запроса следующей страницы или UI navigation; остальные lists молча ограничены первой страницей.
- «нет предупреждений» возможно при unavailable/stale summary с пустым alerts.

Regression: fixtures из утверждённого schema/actual handler DTO; missing/unknown не становится healthy/0; critical не понижается из-за stale; expected/observed отдельно; реальный recoverability/WAL вывод; usable pagination и stale/error handling во всех sections. Не наращивать дизайн/scope, исправить достоверность.

### RV-06 / R3-D — store tests не закрывают runtime persistence/startup

Принятые insert/dedup/TTL/cap/nullable fixes сохранить. Осталось:
- readiness ledger check выполняется единожды; bounded initial retry и expected table-structure validation отсутствуют.
- Store.New по-прежнему ParseConfig без explicit minimum TLS/ambient overrides hardening по исходному contract. Это НЕ утверждение, что verify-full отключён: он указан. Нужны именно оставшиеся гарантии/test.
- snapshotHealth смотрит только warnings/Partial; Node/DB critical в DTO без warning может записаться healthy.
- LastSuccessUnix=0 при первых write failures оставляет LagSeconds=0; между failures lag не вычисляется динамически. Нужен определённый initial/no-success state и elapsed lag.
- status-transition generation отсутствует (предыдущая единичная write-failure event вставка удалена). Memory fallback — текущие snap.Events, не bounded queue переходов/recovery/backpressure.
- sourceUID/resourceVersion не переносятся persistOnce; upsert обновляет count+ingested_at, но не source time/version fields. Нужна согласованная history identity/refresh и pagination semantics.
- нет tests failure/recovery/fallback, startup retry/schema drift и persistence aggregate health. Шесть успешных store tests этого не проверяют.

Regression: isolated fixtures/test DB, first failure then recovery, initial lag, cleanup/event write failure, transition dedup, source-count refresh, bounded fallback, real schema drift, TLS config/identity. Не останавливать production DB и не повторять P8B tests.

### RV-07 / R3-A — EOF/cancel не fail-closed

В read_secret_noecho обеих helpers `c == ""` (EOF) трактуется как успешный конец строки.
Offline reproduction исполнил реальные helper functions с mocked terminal/subprocess: EOF без завершающего newline → get/create → exit0 у обоих helpers. Terminal/calls только synthetic, настоящих secrets не было.
Raw mode также требует явной обработки cancel/control characters; сейчас они добавляются в строку. Registry helper проверяет только non-empty.

Сделать EOF/cancel безопасным STOP до записи, обработку input/terminal errors и корректное восстановление terminal state; не вводить echo fallback. Tests должны исполнять реальные input functions (а не только mock read_secret_noecho), проверять оба helper, body/argv/output/annotations, probe/create timeouts, missing kubectl, denied create и no-overwrite. Запрещённые реальные Owner operations не нужны.

### RV-08 / R3-G — schema validation и воспроизводимость

contract_test.go остаётся прежним presence/shapes test: не загружает OpenAPI, не проверяет all required types/enums/additionalProperties/nullability на реальных handler responses. fixture-smoke проверяет собственноручно созданные объекты без app.js/API. jsdom suite выполняет actual app.js, но только3 cases и содержит неверное Barman field name; testBackupHealthCellShowsHealth даже не assert Health cell.

Добавить meaningful regressions RV-01…07 + actual11-handler OpenAPI validation startup/error/stale/partial. Существующие6 DB tests и14helper tests повторить вместе с новыми после окончательной ревизии, не заменять проверку приложением cached summary. Go cache сам по себе НЕ нарушение и не означает отсутствия прошлых прогонов; для итогового DB evidence нужен fresh `-count=1` и test-server identity, поскольку внешний DB state не зафиксирован cache output.

Зафиксировать actual command lines, source SHA/clean tree, exact test dependency versions/lock, stdout/stderr/exit, test-case→requirement links, local DB server version и safe isolated target identity (без credentials), secret scan.
В raw-transcript c3cfec6 написано «source sha will be appended», но он не добавлен; source SHA есть только в result.md. Исправить traceability новым evidence, исторический файл не редактировать.

## Итоговая матрица Gate

| Gate | Решение |
|---|---|
| Recovery/publication/ancestry | PASS — Connector |
| Source package A–G complete | REWORK_REQUIRED |
| WORKFLOW_TEMPLATE_APPROVED_FOR_OWNER | NO |
| OWNER_HELPERS_APPROVED_FOR_REAL_CREDENTIALS | NO |
| NETPOL_APPROVED_FOR_APPLY | NO |
| CI release digest/signature | NOT_EXECUTED / NOT_VERIFIED |
| Portal runtime / production migration | NOT_DEPLOYED / NOT_EXECUTED по опубликованному evidence; live Architect не опрашивал |
| P8C FINAL ACCEPTED | NO |

## Исполнение без нового согласования

Продолжить тот же RESUME-R3 автономно. Закончить все RV-01…08, включая остающиеся первоначальные требования; один проверяемый пакет с actual outputs и честной closure matrix. Не ждать Owner credentials ради source/test/plan/template.
STOP после полного пакета или точного непреодолимого external blocker после завершения независимых действий. Самостоятельно не присваивать Architect approval.
До положительного review не запускать реальные helpers/dispatch/live NetPol/migrations/deployment. P8D–P8G/P9 NOT_AUTHORIZED; backup/latest restore/PITR/P8A failover/P7/P7C failure tests не повторять.
Git main — SoT; FF/no force, scope Portal/new evidence; не переписывать исторические доказательства. После Git publication сверить final remote HEAD.

## Evidence и пределы независимой проверки

`evidence/P8/20261021-p8c-c3cfec6-architect-review/`: source-index.json, upstream-release-metadata.json, Python/JS reproducible harness + результаты, helper unittest output.
Architect выполнил14helper unit tests, Python synthetic EOF reproduction, Node VM actual renderers и static cross-file checks. Go runtime/PG17/jsdom здесь не установлены; их прогоны Hermes независимо не повторялись. Нет CI/registry/cluster/production/Owner действий. Static source findings явно отделены от executed reproductions.
Primary upstream Connector metadata:
- https://api.github.com/repos/moby/buildkit/releases/tags/v0.34.0
- https://api.github.com/repos/sigstore/cosign/releases/tags/v3.1.3
- https://api.github.com/repos/rootless-containers/rootlesskit/releases/tags/v2.3.1 (checksum остаётся unverified).
