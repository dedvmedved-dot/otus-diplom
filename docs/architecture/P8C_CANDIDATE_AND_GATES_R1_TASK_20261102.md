# TASK: P8C-R1 CANDIDATE-AND-GATES-R1

Дата: 2026-11-02 (Europe/Moscow).
Исполнитель: **основной Hermes**. Hermes2 не участвует.
Репозиторий: dedvmedved-dot/otus-diplom. Source of Truth: GitHub main.

## Цель и допуск

Подготовить один законченный reviewable package:
1. исправленный candidate NetworkPolicy YAML;
2. адресные offline-проверки реальных manifests;
3. конкретные проекты release / runtime-readiness / deployment gates.

Это следующий этап после приёмки offline-дизайна, не повтор A/B/C.
Новый допуск разрешает только перечисленные ниже изменения исходников candidate/tests/template
и подготовку документов. Он не разрешает исполнение будущих gates.

```text
VERIFIED_BASELINE_MAIN=3bbc818245e19f42b9ffb64a14bf510d424ee7e8
OFFLINE_DESIGN=ACCEPTED_WITH_RUNTIME_LIMITS
CANDIDATE_SOURCE_EDIT_AUTHORIZED=YES (только scope этого задания)
GATE_DRAFT_PREPARATION_AUTHORIZED=YES
COLLECTOR_REWORK_REQUIRED=NO
DOCUMENT_ABC_REWORK_REQUIRED=NO
PHASE2_NEW_RUN_APPROVED=NO
NETPOL_APPROVED_FOR_APPLY=NO
CI_RELEASE / WORKFLOW_PUBLICATION / WORKFLOW_DISPATCH=NOT_AUTHORIZED
OWNER_HELPERS / PRODUCTION_MIGRATION_DEPLOYMENT=NOT_AUTHORIZED
P8C=NOT_FINAL_ACCEPTED
P8D–P8G/P9=NOT_AUTHORIZED
```

Не запрашивать новый «продолжай» между подпунктами. Независимую offline-работу завершить всю.
Отсутствие runtime-допуска, credentials, готового image digest или свежего inventory — ожидаемая
граница этого задания, не основание остановить подготовку остальных результатов.

## G0 — Recovery и границы

Через Connector сверить HEAD main, последние commits, ancestry относительно baseline и diff.
Локально: fetch, состояние worktree, отсутствие необъяснённого ahead/behind; чужие изменения
не сбрасывать. Если новые commits противоречат допуску или меняют затронутые контракты — STOP
с конкретным diff; не принимать SHA из чата без проверки.

Прочитать целиком:
- docs/architecture/P8C_RV02_ACCEPTANCE_1b32e4d_20261102.md;
- docs/architecture/P8C_RV02_OFFLINE_ROLLOUT_DECISION_20261102.md **из baseline или его проверенного потомка**;
- portal/networkpolicy/PLAN.md и flow-matrix.md, актуальные верхние статусы;
- portal/manifests/networkpolicy.yaml, deployment.yaml, gateway.yaml и существующий RBAC;
- docs/architecture/P8_PORTAL_DB_CONTRACT.md, P8_PORTAL_PLATFORM_API_CONTRACT_R0.md,
  P8B_POSTGRES_BACKUP_CONTRACT.md;
- portal/tools/p8c-portal-release.yml.template, install-verified-go.sh, release-check.py,
  test_release.py, Containerfile; существующие Owner helpers — только читать.

Зафиксированные blobs (ориентир для независимой сверки):
- canonical offline plan: 872c9b5870121dc10569cb2338595c3a3c69a088;
- candidate networkpolicy.yaml: fccb8432135a18f8b7099e131471a48808df1ed7;
- flows_test.go: 14e347c34f9ed01d3c074234bcf194af6d294cb0;
- release template: 0e713e47f7f7a9e940b3113a7481e393aa961f9e;
- deployment.yaml: 2cb27165330fe4b6772af3a06a1940d661efc72f.

Не переоткрывать принятые source eed114e, collector/S1, inventory 9/9 c872eed,
native PG17 integration, backup/restore/PITR/failover/P7 failure tests.

## G1 — Candidate NetworkPolicy: реализовать принятую delta

Изменяется **portal/manifests/networkpolicy.yaml**; статус остаётся CANDIDATE / NOT_APPROVED_FOR_APPLY.
Сохранить шесть объектов, имена, namespaces и policyTypes. Не вводить новые namespace-wide
политики, Calico policies, CNP, monitoring adapter или разрешения «на всякий случай».

### NP-01. Точные API tuples
В p8c-cnpg-existing-flows и p8c-portal-flows убрать egress 172.30.140.0/24:6443.
В каждой policy сделать два отдельных egress rule:
- to: 10.96.0.1/32; ports: TCP443;
- to: три отдельных ipBlock 172.30.140.101/32, 172.30.140.102/32, 172.30.140.103/32;
  ports: TCP6443.

Не объединять оба набора адресов и оба порта в одно правило: это разрешило бы лишние tuples.
Не добавлять VIP .100, другие адреса /24, 0.0.0.0/0 или UDP.
Migrator не получает API egress. Это configuration candidate; не доказательство DNAT/enforcement.

### NP-02. Убрать неподтверждённый Barman controller→DB5432
Удалить из CNPG ingress peer cnpg-system + app=barman-cloud → TCP5432 и устаревший комментарий.
Не заменять на controller→DB/S3/9090 разрешения. Controller RPC9090 и per-instance sidecar
разделены принятым дизайном. Сохранить sidecar/CNPG Pod→172.30.143.10/32 TCP443.
Адрес остаётся historical candidate до отдельной freshness проверки.

### NP-03. Согласовать точные dataplane selectors
В podSelector p8c-portal-dataplane-flows и соответствующем ingress peer Portal использовать
одинаковую принятую identity:
- app.kubernetes.io/component=proxy;
- app.kubernetes.io/managed-by=envoy-gateway;
- app.kubernetes.io/name=envoy;
- gateway.envoyproxy.io/owning-gateway-name=portal-gateway;
- gateway.envoyproxy.io/owning-gateway-namespace=portal.

Portal ingress peer дополнительно ограничен namespace envoy-gateway-system через
kubernetes.io/metadata.name; namespaceSelector и podSelector — **один peer (AND)**.
Это уточнение selector по принятому дизайну/P6, не создание новой identity-модели.
Dataplane policy остаётся Egress-only. Не вводить новый dataplane ingress allowlist.

### NP-04. Сохранить существующие необходимые потоки
Без расширения: CNPG peer5432/8000, operator→8000, Portal→DB5432/metrics9187,
migrator→DB5432, DNS UDP/TCP53 с совместным namespace/pod selector,
dataplane→xDS18000 и Portal8080. Mgmt8081 не открывать.
Не смешивать Velero domain с Barman, не добавлять scraper по предположению.

Комментарии обновить: первая policy уже изолирует CNPG; rollback union-aware и с UID-preconditions
по принятому plan; 9/9 inventory уже выполнен, но свежий runtime baseline ещё не установлен.
Не называть allowlist «полностью runtime-verified».
PLAN/flow-matrix можно дополнить компактным candidate revision/status и ссылкой на новую delta;
принятый canonical plan и acceptance не переписывать.

## G2 — Адресная проверка candidate, не повтор всего проекта

Расширить существующий portal/networkpolicy/flows_test.go. Он уже читает реальный
../manifests/networkpolicy.yaml и моделирует ingress+egress union — сохранить этот принцип.
Не тестировать отдельно вручную переписанную копию YAML. Test fixtures обозначить SYNTHETIC;
reference identity из P6 не выдавать за live Portal dataplane.

Обязательные positive/negative случаи:
- CNPG и Portal: четыре разрешённых API tuples проходят;
- 10.96.0.1:6443 и каждый endpoint:443 запрещены (нет cross-product);
- .100/.104 и любой другой представитель прежнего /24:6443 запрещены;
- UDP на API ports запрещён; migrator не достигает ни одного API tuple;
- Barman controller→DB5432 запрещён; CNPG sidecar→S3443 сохранён;
- Portal/migrator→S3 запрещены; operator→8000, DB peers5432/8000 сохранены;
- правильные пять dataplane labels + namespace → Portal8080; wrong/missing owning-name,
  owning-namespace, app-label или wrong namespace → deny; mgmt8081 → deny;
- DNS UDP/TCP53 разрешён только целевому peer; правильная pod label в чужом namespace,
  правильный namespace с чужой pod label → deny;
- union S1/S2a/S2b не теряет разрешённые CNPG потоки; removal existing-flows при остающемся
  default-deny НЕ трактуется как восстановление S0;
- набор объектов/namespace/policyTypes сохранён; нет широкого API CIDR/пустого unrestricted
  peer/rule, неожиданного нового port/protocol. Ожидаемые baseline empty selectors допустимы.

Не менять evaluator так, чтобы подогнать итог; учитывать и описать его предел:
он проверяет Kubernetes NetworkPolicy candidate semantics, не реальные CNI/DNAT/Calico tiers.
Unsupported конструкция должна быть явной, не silently allowed.

Выполнить из portal/:
```sh
go test -count=1 -v ./networkpolicy
```
Записать точный source SHA, Go version/GOTOOLCHAIN, UTC start/end, команду, stdout/stderr и exit.
Если требуется небольшая правка evaluator/fixtures для новых selectors, она разрешена с объяснением.
Не запускать весь Go/PG17/collector/UI/backup suite, kubectl apply --dry-run=server или cluster tests.

## G3 — Release gate draft: завершённая подготовка, без CI-запуска

Создать docs/architecture/P8C_RELEASE_GATE_DRAFT_20261102.md.
Статус DRAFT / NOT_AUTHORIZED_FOR_EXECUTION. Не копировать template в .github/workflows.

Сопоставить существующий template и helpers с реальным будущим процессом:
1. source SHA → test job → verified Go bytes → binary → один OCI build → immutable digest;
2. final-image SBOM + vulnerability scan → signature + обе attestations → exact verification;
3. repo/ref/workflow/OIDC identity/source/digest binding;
4. private package до и после push; точные условия GHCR push/pull и visibility;
5. минимальные permissions test/release jobs, main/manual dispatch, absence PAK credentials;
6. artifacts, отказ при любом missing/invalid result, отсутствие promotion/deploy при ошибке;
7. публикация Owner через GitHub UI после приёмки template; dispatch — только отдельный допуск.

**Разрешено:** статическое чтение repo/pinned официальных upstream sources для точных
версий/refs/checksums; source-level review существующих scripts; адресные offline mocks.
Не обновлять версии «до последних». Ранее принятые pins использовать повторно с provenance.
Если независимой проверки конкретного pin нет, отметить UNVERIFIED, дать точный источник
для будущей проверки, не объявлять supply-chain PASS.

При воспроизводимом дефекте именно release template/helper разрешена минимальная правка
portal/tools/p8c-portal-release.yml.template, install-verified-go.sh, release-check.py и
test_release.py с адресным regression. Не менять app/Containerfile/dependencies/Owner helpers.
Запускать test_release.py только если менялся release-код либо нужен конкретный новый
offline regression. Не выполнять release-check.py private/registry с реальными credentials.

Обязательно разобрать bootstrap-зависимость: private-before требует уже существующий private
package. Не обходить это «первым публичным push» и не считать package существующим без evidence.
Дать конкретное Owner/Architect prerequisite или BLOCKED_EXTERNAL будущего release gate;
это не мешает завершить source package. Credentials не запрашивать/не читать.

Результат — точный manifest path/blob/SHA-256 template+helpers, таблица
requirement→step/helper→offline proof→CI-only proof, список внешних условий и run budget DRAFT.
CI-only проверки остаются NOT_EXECUTED. Signature/SBOM/scan placeholders не считаются доказательством.
Никаких OCI builds, push/sign/attest, registry probes, workflow token или публикации workflow сейчас.

## G4 — Runtime-readiness и deployment gate drafts

Создать:
- docs/architecture/P8C_RUNTIME_READINESS_GATE_DRAFT_20261102.md;
- docs/architecture/P8C_DEPLOYMENT_GATE_DRAFT_20261102.md.

### RD-01. Снять неопределённость способа проверки S3/WAL на уровне источников
Offline исследовать **существующие** pinned CNPG1.30.1/Barman0.13.0 API/metrics и принятый P8B
evidence/Portal metrics code. Выбрать один минимальный подходящий источник свежего естественного
архивирования, если он есть: exact field/metric, кто его публикует, endpoint, timestamp/counter
semantics, reset/error/idle, требуемый read-only доступ, bounded samples/window, sanitization.

Не использовать firstRecoverabilityPoint, старый LastBackupSucceeded или node DNS как свежий
Pod→S3 proof. Указать отдельно DNS resolution и успешность S3 operation: одно не доказывает другое.
Не делать вывод «источника нет», если он лишь не был предусмотрен прошлым read-set.
Если источник нельзя достоверно выбрать offline — конкретный unresolved prerequisite,
что именно необходимо от Architect/Owner; никакого нового общего inventory/adapter.
Не писать/запускать новый collector, не выполнять exec/log/proxy, DNS/SSH или metrics reads.
Предложенные дополнительные чтения помечать NEW_PROPOSAL / NOT_AUTHORIZED.

### RD-02. Текущий baseline
PR-3/5/6, HC-* из принятого plan не перепроектировать. Показать, какие нужны ДО политики,
какие ПОСЛЕ создания объекта. Привязать их к future pinned read mechanism, если уже существует;
отсутствие готового безопасного execution wrapper честно указать как отдельное prerequisite,
не реализовывать универсальный collector в этом задании. Не выдавать read-set за effective union.
Старые evidence dates не обновлять и их freshness не продлевать чтением Git.

### DEP-01. Порядок и ownership
В одном конечном dependency-плане:
- accepted candidate SHA + current baseline/S3/WAL proof;
- accepted CI run/source/image digest + private pull readiness;
- Owner-provisioned UI auth/pull credentials (только безопасный локальный механизм; здесь не запускать);
- разрешённые RBAC/CA/Service/миграция/Deployment/Gateway объекты и их names/namespaces;
- S0→S1→S2a→S2b→S3→S4 по принятому plan; policies до соответствующих workloads;
- migrator до application readiness, Gateway последним после TLS/auth/backend prerequisites;
- pin одного verified image digest для Deployment и migration Job;
- rollback новых объектов с UID-precondition, no-overwrite; migrations не откатывать произвольным
  destructive SQL и не затрагивать CNPG инфраструктуру. Сохранить отдельный deployment/NetPol scope.

До настоящего CI digest оставить UNAVAILABLE — не подставлять fake hex в deployment.yaml.
DB: portal-db-rw.portal.svc:5432, portal/portal_app/schema portal, verify-full,
password только secretKeyRef. Не искать primary Pod/Pod IP и не давать superuser.

### DEP-02. Конечные acceptance критерии
Матрица proof→command/endpoint→expected→error/STOP→artifact для:
migration ledger/schema, DB TLS, API health/readiness, UI/assets,
Service/Gateway/HTTPRoute/TLS hostname, 11 API responses, actual platform data,
bounded event persistence, RBAC allowed reads/denied mutations, secret scan и platform postcheck.
Реальную mutation в denied-test не выполнять: определить безопасный authz-test с denied verbs;
не создавать destructive объект ради отказа.
UI/summary: три node и CNPG3/3 — наблюдаемые данные, не hardcoded PASS; stale/unknown видимы.

```text
PORTAL_UI=RUNNING
PORTAL_API=RUNNING
PORTAL_DB=CONNECTED (TLS verify-full доказан)
PLATFORM_STATUS=VISIBLE
PORTAL_URL=<фактически проверенный URL>
```
Это будущие критерии, не текущий результат. Не повторять принятые failover/backup/restore/PITR tests.

В обоих drafts: точные scope/budget/STOP conditions/evidence/истечение допуска, actor основной Hermes,
Owner actions отдельно; все флаги live/apply/CI/prod по-прежнему NO.
Не давать оператору инструкцию «запустите сейчас».

## G5 — Evidence и Git

Новая директория evidence/P8/<UTC>-p8c-candidate-and-gates-r1/.
Исторические evidence не редактировать и не переиспользовать как файл нового результата.
Не запускать secret-helper ради проверки. Secret scan только затронутых файлов/diff;
не печатать найденные значения. Указать scanner/version/scope/exit/ограничения, heuristic ≠ proof absence.

Обязательные файлы:
- result.md: requirement→code/doc→test/check→evidence;
- candidate-delta.md: before/after rules и связь с 14 FLOW-ID;
- raw-transcript.txt: фактические команды, UTC, версии, exit codes;
- source-manifest.json: полные path/blob/SHA-256 candidate/tests/drafts/template/helpers;
- список ACCEPTED_NOT_REOPENED и runtime-only NOT_EXECUTED.

Зафиксировать candidate source commit до evidence commit; tests должны относиться к финальным
изменяемым bytes. Если после tests меняется candidate/test/release logic — повторить только
затронутые проверки. Документальная правка сама по себе не требует всего suite.

Публикация main fast-forward с проверкой ожидаемого HEAD, без force и history rewriting.
При гонке fetch/reconcile; не перетирать новые Architect/Owner commits.
Connector readback окончательных файлов и HEAD. Промежуточные commits допустимы;
не останавливаться для нового «продолжай». Никаких PR merge/workflow публикаций по этому заданию.

## Итоговый STOP — один полный пакет

```text
TASK=P8C-R1-CANDIDATE-AND-GATES-R1
RECOVERY_MAIN_SHA=
ACCEPTED_DESIGN_SHA=3bbc818245e19f42b9ffb64a14bf510d424ee7e8
CANDIDATE_SOURCE_SHA=
FINAL_REMOTE_MAIN_SHA=
CANDIDATE_YAML=REVIEW_READY|PARTIAL
OFFLINE_POLICY_TESTS=PASS|FAIL|NOT_EXECUTED (точный count/exit)
RELEASE_TEMPLATE_CHANGED=YES|NO (причина)
RELEASE_GATE_DRAFT=REVIEW_READY|PARTIAL
RUNTIME_READINESS_GATE_DRAFT=REVIEW_READY|PARTIAL
DEPLOYMENT_GATE_DRAFT=REVIEW_READY|PARTIAL
S3_WAL_OBSERVATION_METHOD=SOURCE_BOUND_PROPOSAL|UNRESOLVED
EXTERNAL_PREREQUISITES=<конкретный список>
COLLECTOR_AND_ACCEPTED_EVIDENCE_UNCHANGED=YES|NO
SOURCE_PACKAGE=REVIEW_READY|PARTIAL
CI_RELEASE=NOT_EXECUTED
PHASE2_NEW_RUN_APPROVED=NO
NETPOL_APPROVED_FOR_APPLY=NO
OWNER_HELPERS=NOT_EXECUTED
PRODUCTION_MIGRATION_DEPLOYMENT=NOT_EXECUTED
P8C=NOT_FINAL_ACCEPTED
P8D–P8G/P9=NOT_AUTHORIZED
```

REVIEW_READY означает выполненную offline-подготовку, не runtime success.
Не объявлять Architect acceptance самому. STOP только после всего пакета либо доказанного
непреодолимого внешнего blocker после завершения всей независимой работы.
