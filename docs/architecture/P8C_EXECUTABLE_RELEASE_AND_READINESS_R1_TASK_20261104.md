# TASK: P8C-R1-EXECUTABLE-RELEASE-AND-READINESS-R1

Дата: 2026-11-04 (Europe/Moscow).
Исполнитель: ОСНОВНОЙ HERMES. Hermes2 не участвует.
Репозиторий: dedvmedved-dot/otus-diplom. Source of Truth: GitHub main.
RECOVERY_BASELINE_SHA: 9c8a45f12f3c47993f58930c6c7d5693feaf5e54.
Принятый source package: 4a55a7ec799243e0804b12c939dd2dd29c2366f0.
Приёмка: docs/architecture/P8C_ACCEPTANCE_4a55a7e_CANDIDATE_AND_GATE_DESIGNS_20261104.md.

## 1. Цель и выданный допуск

Разрешена разработка, локальная квалификация и публикация SOURCE-ONLY пакета:
A. Исполнимый release workflow TEMPLATE + helpers + отдельный private-seed TEMPLATE.
B. Исполнимый read-only readiness wrapper для принятых PR/HC/WAL-проверок.
C. Тесты, проверенные pins, manifests, точные инструкции и новые evidence.

Итог — законченные reviewable исходники для следующего разрешённого исполнения.
Не ещё один проект документа вместо кода. Предоставить один общий итоговый пакет A+B+C.
Продолжать автономно до завершения всей независимой работы; промежуточные коммиты допустимы
и не требуют нового «продолжай».

SOURCE_IMPLEMENTATION=AUTHORIZED
OFFLINE_TESTS=AUTHORIZED
PUBLIC_UPSTREAM_PIN_VERIFICATION=AUTHORIZED_WITH_SCOPE_BELOW
LIVE_CLUSTER / SSH / PRIVATE_REGISTRY_PROBES = NOT_AUTHORIZED
WORKFLOW_PUBLICATION / DISPATCH / CI_RELEASE / SEED_PUSH = NOT_AUTHORIZED
OWNER_HELPERS / NETPOL_APPLY / PRODUCTION_MIGRATION_DEPLOYMENT = NOT_AUTHORIZED

Ни этот TASK, ни fixtures/mock gate не являются разрешением выполнить подготовленный live-код.
Не использовать /etc/hermes/gh_token.txt или парольный fallback. Не запрашивать секреты в чате.

## 2. G0 — Recovery и замороженные части

Fetch main, проверить HEAD/последние commits/parent и clean worktree. Прочитать:
- указанную приёмку;
- docs/architecture/P8C_REVIEW_c96a998_AND_R4_FINALIZATION_20261103.md;
- docs/architecture/P8C_RELEASE_GATE_DRAFT_20261102.md;
- docs/architecture/P8C_RUNTIME_READINESS_GATE_DRAFT_20261102.md;
- docs/architecture/P8C_DEPLOYMENT_GATE_DRAFT_20261102.md;
- docs/architecture/P8C_RV02_OFFLINE_ROLLOUT_DECISION_20261102.md;
- docs/architecture/P8_PORTAL_DB_CONTRACT.md;
- текущие release template/helpers, Containerfile и принятые read projections.

Новые commits после baseline: изучить diff; STOP при конфликте с scope/допусками. Не откатывать
чужую работу и не исправлять историю по памяти. Допустимые изменения этого TASK не являются drift.

Не переоткрывать F1/F3/editorial, inventory 9/9, accepted-policy-contract, 14-flow design,
app/DB migrations, CNPG/Barman/Velero backup, PG17 integration и failover/PITR tests.
Не запускать полный старый Portal/PG17/collector suite ради этого задания.
Будущий CI template сохраняет свои ранее согласованные app tests: это не разрешение запустить их сейчас.

Начальные source pins, сверенные Architect через Connector:
| Файл | Git blob |
|---|---|
| portal/tools/p8c-portal-release.yml.template | 0e713e47f7f7a9e940b3113a7481e393aa961f9e |
| portal/tools/install-verified-go.sh | 2b6e0c9a0127ac0a641feef791f017d287719543 |
| portal/tools/release-check.py | 88598da050c07c6475ebcafb793876567c730e87 |
| portal/tools/test_release.py | cf31c99d9e9d152c8b267007744e19444f7debe9 |
| portal/Containerfile | e158e2f77d76a0e775b853c0968b38167fc02078 |
| portal/manifests/networkpolicy.yaml | 15f0b3245586bf5086e5a24ed02b0460121f7712 |
| portal/networkpolicy/testdata/accepted-policy-contract.json | 91a4e571ea36395b3cafd8490f057a28e78cf4d6 |

Containerfile FROM scratch: base-image digest NOT_APPLICABLE_EMPTY_BASE, не выдумывать.
Эти pins фиксируют старт; изменяемым helpers/template в результате дать новые hashes.

Разрешённые изменения:
- portal/tools/p8c-portal-release.yml.template;
- install-verified-go.sh, release-check.py, test_release.py и адресные новые release helpers/tests;
- новый portal/tools/p8c-portal-seed.yml.template + нужные seed helpers/tests;
- новый каталог portal/tools/readiness/ (wrapper, declarative read-set, fixtures, tests);
- source lock/manifest/check scripts внутри portal/tools/;
- три gate-draft, отдельный runbook/qualification matrix, активная ссылка PLAN.md;
- новое evidence.

Не менять .github/workflows/, application/web/migrations, Containerfile, production manifests,
RBAC, принятые collectors/inventory scripts, frozen policy fixture/tests, historical evidence.
Использовать принятые projection-функции как зависимости с pin, не редактировать их.
Если нужен модуль вне allowlist — представить конкретный diff/proposal как blocker этого изменения;
остальную независимую работу завершить.

## 3. G1 — source/supply-chain qualification

Проверить имеющиеся pins, не обновлять автоматически версии:
Go 1.27.3; BuildKit v0.34.0; rootlesskit v2.3.1; Syft v1.55.0; Trivy v0.76.0;
Cosign v3.1.3; postgres:17.10-bookworm digest; три action commit SHA из release draft.
Проверяется фактическое существование версии/asset и точных bytes/ref, не совпадение с пересказом.

Разрешены публичные HTTPS GET к официальным upstream release/checksum/source endpoints и
анонимные metadata/blob GET только публичного postgres image для проверки его закреплённого digest.
Следовать только официальным download redirect/CDN, фиксировать конечный источник.
Это исключение из offline-режима касается ТОЛЬКО supply-chain источников:
никаких обращений к ПАК, SSH, GHCR private package, user/package settings или новых credential.
Публичный registry bearer exchange допустим только автоматически для pull этого публичного image;
token в памяти, не в evidence. Не использовать Owner/production credentials.

Для каждого pin: точный URL/commit/asset, declared checksum/digest, фактический checksum точных bytes,
источник upstream checksum/provenance, verification method, UTC/exit и конечный VERIFIED /
MISMATCH / UNAVAILABLE. Manifest-list, platform-manifest и config digest не смешивать.
Для action SHA проверить source repo/commit; optional tag annotation не является authoritative pin.
Никаких fabricated hashes, «tag существует значит digest verified» или curl|sh.

Скачивать в изолированный task-cache. Не устанавливать ничего глобально, не делать sudo apt upgrade.
При необходимости проверенного binary --version — только из task-local path после checksum verification.
Не выполнять OCI build/push/sign/attest и не запускать downloaded postgres service.
Верификация bytes не означает успешное выполнение CI.

Отдельно перечислить runner dependencies (Ubuntu runner, Node/npm, Python, uidmap/slirp4netns и др.).
Не называть workflow полностью герметичным. Не оставлять неограниченный apt-get install:
задать проверяемый runner dependency contract (явные supported versions/source/проверки либо
закреплённые package versions). Неподтверждённую runner availability честно оставить CI-only prerequisite.
Новые qualification tools также pin/verify либо использовать уже имеющиеся, записав версии.

Если pinned upstream asset отсутствует/не совпал: не заменять «на latest». Зафиксировать blocker
конкретного компонента и кандидат замены отдельно, закончить остальные G1–G5.
Новый version/pin требует Architect review до дальнейшего исполнения.

## 4. G2 — release package: исполнимый template и fail-closed helpers

В .template, НЕ в .github/workflows/, реализовать:

R-01. Только workflow_dispatch, exact repository + refs/heads/main, checkout immutable SHA,
persist-credentials=false. Разделить workflow revision и application source revision, если они
различаются из-за последующей Owner publication; явно привязать оба в manifest/evidence.
Не создавать circular self-SHA. Future gate pin = hashes исполняемых файлов + разрешённый
source commit; publication-only diff не должен молча разрешать app/source drift.

R-02. test timeout-minutes=20; release=30; manual run max1, no automatic rerun.
24h launch expiry от явного future issued_at UTC; gate absence/expiry/source/hash mismatch =>
STOP ДО первого protected action. При rerun attempt>1 — отказ; concurrency не заменяет run budget.
Gate control plane не разрабатывать заново: минимальный typed gate manifest + checks,
который будущий Architect gate закрепит отдельно. TEST_ONLY gate не принимается live-режимом.
В текущем пакете нет настоящего разрешающего execution manifest.

R-03. Job permissions: test contents:read; release contents:read/packages:write/id-token:write.
GITHUB_TOKEN выдаёт Actions, Owner не передаёт его значение. Нет cluster credentials/SSH/kubectl/
deploy step/production token. Secret values не попадут в argv/debug/artifacts.

R-04. Verified Go bytes -> используемый go binary -> build: GOTOOLCHAIN=local, checksum/version/path
proof, no silent alternate toolchain. Rootless BuildKit ready wait с hard deadline и cleanup.
Одна image build, один полученный digest: binary/SBOM/scans/signature/attestations относятся к нему.
Mutable tag не использовать как доказательство. Отдельные подписи/attestations — не повторная build.

R-05. private-before до app-image push, private-after после. Exact package/repository association.
403/404/timeout/malformed/redirect — не доказательство отсутствия/private. STOP с value-free кодом.
Проверка registry manifest bytes по digest и Docker-Content-Digest. Не печатать auth headers/bodies.
Сохранить deny redirects, response size/timeout ограничения в release-check.

R-06. Final-image SPDX SBOM, binary/image Trivy HIGH+CRITICAL fail-closed; отсутствие scan result,
scanner error или неизвестный статус — не clean. Keyless Cosign sign+verify exact issuer/identity;
проверить обе attestations, subject=image+digest, provenance=source+builder+buildType,
SBOM predicate=именно сохранённый final-image SBOM. Payload parsing не выдавать за crypto verification.
Считать PASS только после успешных реальных verify subprocess в будущем CI, не на одном JSON.

R-07. Полный конечный список обязательных артефактов. Проверять не только is_file/size>0:
schema/identity/source/digest bindings и фактические exits соответствующих шагов.
Частичный failed-run diagnostic artifact не должен выглядеть accepted release.
Upload artifacts на error допустим, aggregate result остаётся FAIL/INCOMPLETE.
Проверить формат provenance по реально закреплённому Cosign; не менять SLSA version без основания.

R-08. Сохранить прежние app test steps в template, исправить только доказанные integration issues
квалифицируемого release-маршрута. Сейчас локально запускать только release/helper/template checks;
не повторять accepted native PG17 tests или весь app suite.

Адресные тесты R: good path; source/digest/identity mismatch; wrong/private/missing package metadata;
403/404/redirect/timeout/oversize/malformed; missing/empty/invalid required artifact; expired/missing/
TEST_ONLY gate, rerun; failed signature/attestation/scanner; checksum mismatch до исполнения tool;
verified-Go path binding; ready-wait exhaustion; no token/raw-body canary leakage.
Проверки YAML через parser с корректной трактовкой on (не YAML1.1 bool); syntax checks shell/Python.
Не утверждать Actions runtime PASS по static YAML или mocks.

## 5. G3 — отдельный private seed TEMPLATE

Реализовать source template отдельного bootstrap, не запускать и не публиковать.
Exact target: ghcr.io/dedvmedved-dot/otus-diplom-portal.
Seed: минимальный фиксированный OCI image/artifact без Portal binary и без секретов;
явная маркировка bootstrap-only/not-deployable, уникальный source-bound tag, записываемый digest.
Выбрать один поддерживаемый GHCR media type и конкретный способ создания на verified toolchain;
описать literal artifact/config/labels и repository association, не оставить «seed по решению позже».
Seed digest не может быть accepted application IMAGE_DIGEST.

Bootstrap uses future automatic GITHUB_TOKEN/packages:write и отдельный one-shot gate/run-id.
Existing exact private associated package -> подтверждённый no-op/reuse, без push.
Public/wrong association/ambiguous access -> STOP.
404 не даёт права создать: future gate обязан содержать отдельно подтверждённое Owner основание
для first creation и проверенные package/repository permissions. Не выдумывать наличие этих facts.
После разрешённого seed push — exact digest + private visibility + association proof;
перед main release заново private-before. No public-first workaround, PAT или workflow-token.
Тестировать только mocks/fixtures: existing-private, public, wrong repo, ambiguous404, missing Owner
prerequisite, malformed result, seed mistakenly offered as app digest. Никаких package settings changes.

## 6. G4 — read-only readiness wrapper: точный read-set

Отдельный модуль portal/tools/readiness/, без Kubernetes mutations и без SSH provisioning.
Он исполняется будущим оператором в уже разрешённой сессии; сам не ищет доступы/hosts.
Не читать kubeconfig/SSH credential в разработке и не подключаться к узлам.
Source implementation может использовать argv kubectl get --raw без shell=True; никаких exec/log/proxy,
arbitrary command/url/path/namespace, discovery fallback или arbitrary query inputs.

Контекст только kubernetes-admin@pak-portal, future kubeconfig остаётся на node-01.
Input validation до subprocess/output creation; no-overwrite, restrictive files, bounded outputs.
Фиксированные read IDs, методы, paths, predicates, stage applicability и limits — machine-readable
read-set; это не свободный Kubernetes query API.

Реализовать:
- PR-3: exact API EndpointSlice path/selector из принятого offline design, max1 GET, limit200,
  полный ready TCP tuple set {.101,.102,.103}:6443.
- PR-5: exact generated Service path с обоими owning labels, max1 GET, limit2, ровно один item;
  LoadBalancer/Local/TCP443->10443, source-defined selectors, actual LB/UID/ports; только S4.
- PR-6: ровно девять version-pinned paths из design §5, limit200, no continuation/fallback.
  Только S0 baseline freshness: после создания новых policies нельзя снова ожидать empty baseline.
  Tier/Felix/labels сравнивать с pinned accepted sanitized evidence; новые/unknown semantics => STOP.
  Empty policy lists сравниваются как empty, API_NOT_SERVED/ошибка не заменяются пустотой.
- HC-DB/ARCH-STATE: тот же named Cluster response, readiness/conditions точно по принятому design.
- HC-OP/DNS/PORTAL/GW: literal paths, predicates и W/I/N из design. HC-PORTAL только S3/S4,
  HC-GW только S4; phase-inapplicable = NOT_APPLICABLE, не PASS.
- HC-WAL-PROGRESS: новый принятый RD-01 заменяет историческую строку «запросов0/нет источника»,
  не меняя её историческое evidence. Primary-bound 5-request sample, no redirects, фиксированный9187.
- PR-4 отдельного DNS/traffic probe не делать: WAL даёт только согласованный proxy archive success,
  НЕ независимый S3 readback/DNS proof. Незакрытый prerequisite не скрывать aggregate PASS.

При typed List: envelope/version/scope/item context, required fields, null/type errors, limit и
metadata.continue валидировать; не повторять прежний дефект optional item TypeMeta.
Для нового namespace/name использовать только значение из проверенного named Cluster currentPrimary
после безопасной name validation; Pod owner UID/name должен совпасть с Cluster, IP — literal validated
status.podIP этого Pod. Запрещены arbitrary host, env proxy substitution и HTTP redirects.
IP backend не передаётся в Portal DB config: приложение остаётся Service:5432 verify-full.
Bracketing сравнивает тот же Pod/Cluster до и после; не переключаться автоматически на новый primary.

Существующие принятые projections допускается импортировать byte-identical; включить все runtime
dependencies в package manifest. Импорт не должен незаметно запускать старый inventory collector.
Новые projection checks ограничить этим read-set, не строить универсальный Kubernetes sanitizer.
Raw bodies/annotations/env/Secret/ConfigMap/credential никогда не сохранять/печатать.
Finite error codes, safe journal (UTC/monotonic duration/read-ID/path/attempt/exit/count/disposition),
без токенов, stdout/stderr raw fallback и traceback с payload.

Deadline — на ВСЮ операцию headers+body, а не только connect/один read; slow-drip/body test обязателен.
No overflow processing после лимита, no background request leaks после timeout/kill.
Aggregate FAIL/INCONCLUSIVE/NOT_EXECUTED различаются; нет тихого успеха при partial.

## 7. G4 budgets, state, clock: нормы уже приняты, не проектировать заново

WAL: S0/S1/S2a/S2b/S3/S4 максимум6 окон; offsets0/300/600s, max3 samples/window.
Sample = Cluster GET -> Pod GET -> metrics GET -> SAME Pod GET -> SAME Cluster GET.
5s/request;30s/sample;660s/window;4×256KiB metadata+1MiB metrics=2MiB/sample;
15req/6MiB/window;90req/36MiB/3960s observation upper bound.
No retries при transport/parse failure. Idle допускает только remaining planned slots.
Monotonic deadlines + injected test clock; tests не должны реально ждать300/600s.

S0 first sample baseline, later sample fresh progress. Post-stage сравнивать последний accepted
pre-operation sample с той же identity, failures/reset markers приоритетнее archive growth.
Сохранять operation_end UTC и source/gate/run/stage/identity binding в локальном защищённом state.
Missing/stale/wrong baseline, repeated/skipped stage, invalid action receipt => STOP.
Wrapper сам не делает stage operation/apply/rollback и не выдаёт разрешение на них.

Для PASS необходим bounded exporter/observer UTC skew <=5s:
last_archived_time > operation_end+5s AND <= sample_end+5s; S0 uses first_sample_end.
Clock evidence — отдельный pinned input будущего gate: source/provenance, observed UTC, coverage
нужного node/backend, numeric bound, validity window. Gate связывает его hash.
Файл с числом5 или CLI-флаг trusted=true без происхождения не является clock proof.
Сейчас определить source-bound формат/валидацию, positive/negative fixtures и точный способ
получения через уже документированный механизм, если источник есть в repo.
Если подходящего текущего источника нет — явно CLOCK_EVIDENCE_METHOD=UNRESOLVED и сформулировать
один конкретный future read proposal. НЕ выполнять его и НЕ блокировать независимую реализацию
fail-closed wrapper. Без реального clock evidence будущий live verdict INCONCLUSIVE.

Read-set ceilings при полном S0–S4 цикле (не разрешение выполнить его):
- WAL:90 requests/36MiB.
- HC-DB+ARCH-STATE:36 GET; HC-OP36; HC-DNS36; HC-PORTAL12; HC-GW12 =>132 GET.
- PR-3 one + PR-5 one + PR-6 nine =>11 GET.
- Non-WAL responses capped1MiB before projection:143MiB.
- Максимум233 GET/179MiB; observation windows <=5265s, НЕ время deployment operations.
  HC:6×(60+60+30)+2×60+120=1140s; PR:11×15=165s; WAL3960s.
Это ceilings, не обязательство расходовать весь budget; совместно используемый ответ считать один раз.
Источник HC-DB/ARCH-STATE общий. Freshness last successful GET <=30s, Gateway<=60s сохранить;
порядок/параллельность read-only checks должен укладываться в freshness и исходные N/W, без
дополнительного непосчитанного final sweep. Если невозможно — INCONCLUSIVE/STOP.
Полный execution budget будет отдельно выдан будущим gate, может быть уже этих source ceilings.

Обязательны future gate checks и сохранённый run/stage budget:
gate missing/expired/source-hash mismatch/TEST_ONLY/wrong context/existing output =>0 live requests.
Один future run нельзя перезапустить молча после timeout/crash; UNKNOWN_OUTCOME сохраняется,
новое разрешение не выводится из EXIT!=0. Offline fixtures не являются live gate.
Разрешены test-only injected transport/clock/state; production entry point не включает bypass.

## 8. G5 — конечная test matrix

Тестировать только новый/изменённый executable package, без реального ПАК/CI/registry:
- Readiness: успешные S0/post-stage; count/time/byte ceilings и boundary; timeout/slow body;
  wrong-context/gate/hash/expiry/output/reused run =>0 calls; no-overwrite/atomic state.
- PR3 changed tuple; PR5 0/2 items/wrong identity/targetPort; PR6 new policy/Tier/Felix/peer labels;
  API absent/forbidden/timeout vs empty; list partial/null/TypeMeta/oversize; no unbounded continue.
- HC missing/False/Unknown/stale/observedGeneration mismatch; phase applicability.
- WAL same-primary good; UID/IP/primary/restart/reset swap до/после; counter failure despite success;
  idle exhaustion; missing/duplicate/NaN/Inf series; old timestamp/future timestamp; operation boundary.
- Clock bound<=5 vs>5, missing/expired/wrong-node/source hash; false trusted flag must not pass.
- Raw/secret/canary stderr/error/HTTP payload suppression. No actual live API/SSH call from test runner.
- Release/seed cases из G2/G3, template syntax и scope assertions.
- Final package manifest covers EVERY imported/executed file, fixture/runtime distinction,
  source SHA/blob/SHA256, literal future command, required versions, supported architecture.

Mocks доказывают ветвление/границы, НЕ криптографическую подлинность, приватность GHCR,
реальную сеть/clock/WAL, rootless runner availability или успешный релиз.
Указывать CI_ONLY/NOT_EXECUTED для недоступных здесь фактических подтверждений.
Не требовать Owner secrets для завершения тестов. Один блокированный внешний pin/clock факт
не останавливает остальные независимые части.

## 9. G6 — evidence, Git, итоговый STOP

Evidence-first, новое evidence/P8/<actualUTC>-p8c-executable-release-readiness-r1/.
Сначала source commit; локальные тесты на exact source SHA; затем отдельный evidence commit.
Фиксировать реальные UTC/Python/Go/grep/tool versions/commands/exits, public-pin verification results,
full source/runtime dependency manifest, requirement->code->test->evidence matrix.
Hash всех frozen scan inputs ДО scan. Output вне inputs; полная команда без <files>/многоточий.
0=match,1=no-match,2=error для grep различать. Для новых evidence файлов отдельный frozen scan set;
не утверждать проверку всего repo по шести файлам. Не выводить секретные значения.

Исторические evidence не исправлять. ff only/no force. Если main сдвинулся — fetch/review/rebase
без потери чужих изменений; при конфликте accepted/source scope STOP. После rebase изменённые
исполняемые bytes требуют релевантной повторной проверки; doc-only publication не выдумывает новый test run.
Verify remote HEAD/readback, clean/ahead/behind. Предоставить один итоговый отчёт, а не серию partial STOP,
кроме конкретного непреодолимого внешнего blocker после завершения независимой работы.

Финальные поля:
TASK_ID
RECOVERY_MAIN_SHA / FINAL_SOURCE_SHA / FINAL_REMOTE_MAIN_SHA
RELEASE_TEMPLATE_SOURCE_QUALIFIED
PRIVATE_SEED_TEMPLATE_SOURCE_QUALIFIED
PUBLIC_PINS_VERIFICATION (per item)
READINESS_WRAPPER_SOURCE_QUALIFIED
READINESS_OFFLINE_TESTS / RELEASE_OFFLINE_TESTS
CLOCK_EVIDENCE_METHOD / CLOCK_LIVE_EVIDENCE
RUNTIME_PACKAGE_MANIFEST (full hashes)
REMAINING_EXTERNAL_PREREQUISITES
CI_RELEASE=NOT_EXECUTED
WORKFLOW_PUBLICATION_DISPATCH=NOT_EXECUTED
BOOTSTRAP_PUSH=NOT_EXECUTED
LIVE_READINESS=NOT_EXECUTED
NETPOL_APPROVED_FOR_APPLY=NO
OWNER_HELPERS=NOT_EXECUTED
PRODUCTION_MIGRATION_DEPLOYMENT=NOT_EXECUTED
P8C=NOT_FINAL_ACCEPTED
P8D–P8G/P9=NOT_AUTHORIZED

Итоговый STOP — для независимого Architect review готового исполнимого SOURCE пакета.
Не запускать его против кластера/registry и не присваивать FINAL ACCEPTED самостоятельно.
