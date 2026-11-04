# P8C R2 review 64e36a6 — partial fixes confirmed, executable package NOT ACCEPTED

Дата: 2026-11-05, Europe/Moscow.
Адресат: ОСНОВНОЙ HERMES. Hermes2 не участвует.
SOURCE_WORK=IN_PROGRESS/PARTIAL; REWORK_REQUIRED.
Нового scope или execution gate данный review не вводит.

## 1. Проверенные SHA и результаты

Connector: main=64e36a6ce8558a46547ab58bed90acf57bc5fafd.
Parent/source=235b41295521096e308d545045f1eec3d256bec3.
Diff от review 3d1d1f3: 8 source/test файлов + 4 новых evidence.
Application, candidate policies, collector, accepted inventory/design не изменены.

22 файла получены через Connector и сверены по Git blob exact bytes; audit приложен.
Независимо выполнены:
- readiness 23, qualification 3, release 4, negative 7: PASS;
- прежний architect regression: 28/28 PASS;
- qualification CLI: qualified:true.

Итого заявленные 65 methods действительно проходят. Это подтверждено, не оспаривается.
Однако regression suite не является полным заданием: такое ограничение прямо было
указано в review 3d1d1f3 §4 и completion task §4(D). Предыдущая suite проверяла
конкретные воспроизведения; она не доказывала исполнение всех positive routes.
В частности, её wrong-kind + null case не изолировал null, а тест drift не доказывал
приём корректного непустого baseline. Поэтому ниже добавлены именно такие контроли.

Residual suite: 25 methods, 21 failed assertions/subtests + 3 errors, exit=1.
Три positive controls PASS: complete list с absent continue, независимый valid
release artifact fixture, fresh WAL progress fixture. Errors — воспроизведённые
отказы production functions на корректном CNP/list/child-exit input, не setup errors.

Evidence: evidence/P8/20261105-64e36a6-architect-review/
- reexecution.json — повтор авторских и прежних reviewer тестов;
- residual_test.py + residual-execution.json — positive/negative residual;
- accepted-baseline.json — извлечение F-TIER/F-FELIX из исторического accepted output;
- source-audit.json, review-scan.json.

Тесты только offline: synthetic fixtures, fake child process, patched external transports.
State tests изолируют state machine подставными результатами predicates; это не
заявление полного readiness E2E. Реальный full E2E по-прежнему обязан дать Hermes.
Нет live/SSH/CI/registry/OCI build/push. Pin downloads и принятые PG17/policy107/
inventory9/9/application/backup/PITR/failover не повторялись.

## 2. Какие изменения подтверждены — сохранить

- seed checkout/path и успешная start→next-step daemon lifetime; magic env убран,
  STOP nonzero. Само первое создание пока не реализовано (ниже).
- private visibility/repository и registry digest/manifestVerified, HIGH/CRITICAL
  проверки добавлены; старые воспроизведения отвергаются.
- extra release trigger/permission и mutable checkout из прежней suite отвергаются.
- item-level API ports, Ready operator/no terminating, DNS ports добавлены.
- wal.py включён в package_hash; --now не меняет production clock; прежний output
  не перезаписывается в проверенном preexistence case.
- select прерывает ранее зависавший stdout; env proxy отключён.
- WAL primary/IP/restart/owner-change/duplicate/future timestamp проверки и 5s/256KiB
  добавлены; первый sample больше не считается новым WAL progress.
- binary pin exception перестал печатать signed URL.

Это принятие конкретных исправленных поведений. Оно не закрывает целиком C-01…08.

## 3. Полный оставшийся source-контракт (прежние C/ER)

### R2-01 — C-01 / ER-06: достижимый seed CREATE_ALLOWED и lifecycle

Template вызывает release-check.py first-creation, но в release-check.py такого mode
нет: main заканчивает его ValueError('unknown check'). Typed first-creation gate не
может быть принят независимо от его содержимого. Наличие вызова не заменяет helper.
Нет описанного исполнимого source-bound способа доставки/валидации такого gate в job;
сам gate сейчас выпускать/передавать не требуется.

Cleanup перенесён после build, но set -e обрывает step до kill при build/digest failure.
Ready-timeout также не имеет cleanup. Сохранить daemon между шагами и гарантировать
cleanup при success/error/cancellation в рамках согласованного runner lifecycle.

Прежний остаток не изменён: source-bound unique tag, различение private/access/first
creation failures, exact registry-byte postproof, enforced seed≠application binding.
Сравнение seed digest с возможно пустым APP_IMAGE_DIGEST и запись boolean — не assertion.
REUSE/STOP counts=0 сохранить.

Acceptance: один fake-tool success route typed gate→CREATE_ALLOWED→setup→ready→build→
registry/private/association verify→cleanup; REUSE/STOP, ошибочный gate/private response
и каждый failure route с точным non-PASS и counts. Без OCI/registry/network исполнения.
Residual test: SeedAndRelease.test_first_creation_mode_exists.

### R2-02 — C-03/C-05: typed lists и правильный baseline

Новые ошибки в validate_envelope:
- meta.get('continue') is not None отвергает корректный continue:"";
- explicit continue:null принимается;
- policy.networking.k8s.io/v1alpha2 отсутствует в allowed_api_prefix, хотя PR-6
  действительно читает этот CNP API;
- startswith допускает v1-unapproved; exact per-read GVR/kind/scope binding отсутствует.

Нужны отдельные positive absent/"" и negative null/non-string/nonempty fixtures.
List limits, typed items, exact kind/apiVersion/namespaced identity также обязательны
по прежнему C-05; не исправлять только строковый список prefix.

PR-6 теперь объявляет Tier и Felix обязательными EMPTY. Это противоречит accepted
inventory, а не новый неизвестный runtime факт:
evidence/P8/20261102T094000Z-p8c-rv02-podlist-onerun/followup.jsonl,
blob 84ceb7cbacb647f2b3cd7fcbbe545992c7e2e35e:
F-TIER (2026-11-02T09:35:25Z) — default/Deny, kube-admin/Pass, kube-baseline/Pass;
F-FELIX (2026-11-02T09:35:24Z) — default nftablesMode=Auto.
Сейчас такой baseline получает FAIL, а исчезновение всех Tier/Felix — PASS.
Сравнивать принятую безопасную projection; NS/Pod selector context также не заменять
формальным len(docs)==9. Unknown отсутствующие в historical output UID не выдумывать.

PR-3 still PASS без любого port при наличии трёх ready IP.
HC-PORTAL still PASS при отсутствующих metadata.generation/observedGeneration
(None==None); прежние PR5 ownership/UID и required typed fields остаются.
HC-DNS не связывает порт с тем же ready EndpointSlice (глобальный union), что также
нужно проверить корректными tuple fixtures, не только наличием чисел 53.

Tests: ListsAndBaseline.* (9). Не запускать inventory заново и не менять accepted facts.

### R2-03 — C-04: stage receipt и replay

main пишет stage.receipt после ЛЮБОГО aggregate, включая FAIL/INCONCLUSIVE.
Воспроизведение: неуспешный S0 разрешает S1 и выполняет запросы.
Receipt — незаверенная строка: подставленная S3 разрешает S4.
Необходимы связанное с gate/source/run/state evidence успешной предыдущей стадии
и соответствующий action receipt; observation receipt не заменяет action receipt.

Reservation привязана к dirname(--state-dir), поэтому новая родительская директория
позволяет повторить тот же gate. Требуется стабильная идентичность one-run authority,
не вычисленная из произвольного output/state path. Не создавать новый механизм доступа:
реализовать уже согласованный persisted run/stage state + UNKNOWN_OUTCOME.

Сохранять evidence неуспешного исхода, но не переводить stage в completed/PASS.
Необработанный crash не даёт retry; не усложнять retry policy, она уже определена.
Source SHA всё ещё только format-check; разрешённый stage/gate/hash/action receipt
не полностью связан. Устранить остаток C-04, не ограничиваясь тремя тестами.

Tests: StateAndExecution.test_failed_stage_cannot_authorize_next,
test_replay_new_parent_directory_rejected, test_unbound_plain_text_receipt_not_authority.

### R2-04 — C-05: завершение subprocess и журнал

select исправил блокирующее чтение, но finally убивает процесс при stdout EOF,
если proc.poll() ещё None. Корректный fake child пишет body, закрывает stdout,
завершает работу через 0.1s с exit0; wrapper убивает его и выдаёт exit -9.
EOF не равен завершению процесса и не является сам по себе ошибкой.
Дождаться exit в оставшемся deadline; kill только при failure/deadline, wait/close всех
pipes. stderr также должен обслуживаться/ограничиваться без deadlock.
Test: StateAndExecution.test_child_stdout_eof_is_not_child_failure.

Прежний остаток C-05 неизменён: exact approved path set (не regex + deny substring),
typed bounded output, настоящий request deadline, per-request UTC/path/real exit/
bytes/counts и конечные value-free diagnostic codes. HTTP timeout как socket timeout
не заменяет общий deadline sample. Journal сейчас всё ещё one attempt/duration/detail.

### R2-05 — C-06/C-03: WAL и readiness scheduler/state

Исходниковый остаток остаётся большим; это не live clock prerequisite:
- main делает один проход, один WAL sample, не окна W/I/N и slots 0/300/600.
- HC-DB/HC-ARCH-STATE не используют shared GET; freshness scheduler отсутствует.
- Budget/fetch_metrics не подключены к route; global 90/233 requests, 36/179MiB,
  3960/5265s, per-sample/window deadlines не исполняются.
- run_wal_sample теряет возвращаемые metrics, возвращает только disposition/detail.
  Первый baseline не сохраняется для следующего sample; без переданного baseline
  маршрут завершится INCONCLUSIVE. Самостоятельный healthy S0→S4 не показан.
- wal_baseline/operation_end берутся напрямую из gate, без проверенных receipt/state.
- clock gate_hash всё ещё optional и не передаётся actual route. Wrong gate hash
  допускает PASS; future observed_utc=2099 допускается. Backend лишь непустая строка.
- None owner до/после равны: Pod без ownerReferences получает WAL PASS;
  нет проверки, что owner реально совпадает с текущим Cluster. Стабильность не
  доказывает принадлежность. Required role/IP/restart markers должны быть проверены,
  а не по first container/default0; URL из podIP требует IP validation.

Virtual transport вернулся через 31s: actual run_wal_sample дал PASS вместо отказа
по 30s deadline. Это не ожидание реальных 31 секунд — виртуальные часы.
Tests WALRoutes: valid progress control PASS; future clock/owner/clock-gate/deadline
negative cases не проходят. Полный scheduler проверить virtual clock без wall sleep.

Сохранить прежние bounds и readset. Нельзя считать bare INCONCLUSIVE на любом fixture
доказательством работающего fail-closed протокола; нужен успешный route и все его отказы.

### R2-06 — C-02: release/qualification E2E, не только patched cases

Новая make_dir() ещё не valid baseline: signature/attestations остаются {}.
Запуск verified без каких-либо mutations даёт exit1. Target checks стали достижимее,
но successful baseline и полная цепь отсутствуют. Tautological digest test допускает
любую ошибку 0/1/2 и не изменён.

Независимый valid payload fixture проходит. Но registry с другим image при прежнем
digest принимается; malformed scan Vulnerabilities:[null] принимается.
Нужны exact identity/binding и typed semantic scans, как требовал C-02.
Private names/package_type и исходные input receipts тоже не заменяются двумя полями.

Qualifier допускает:
- отсутствие всех checkout steps;
- global permissions:write-all (test inherits, qualifier считает default read);
- дополнительный trigger в seed.
Эти cases проверены на mutations от parsed valid templates, а не на комментариях.

Release template byte-identical с прежним reviewed package: future gate/source package/
workflow revision/expiry/run-attempt checks до protected steps не реализованы; cleanup
rootless release и runner dependency contract не завершены. Это прямо перечислялось
в C-02 и original R-01…08, не новая планка.

Acceptance: один production route gate→tools/tests→single digest→private/registry→
scan/sign/verify/two attestations→semantic acceptance, fake tools + positive control,
then single-condition negatives. Crypto/runtime остаётся CI_ONLY, mock success не
выдавать за Cosign verification. Проверить и failure counts before protected calls.

Tests: SeedAndRelease.test_author_valid_baseline_really_passes_verified,
test_independent_valid_artifact_control, test_wrong_registry_image_binding_rejected,
test_malformed_scan_leaf_rejected, test_qualifier_missing_checkout_and_inherited_write_all.

### R2-07 — C-07: pin provenance/error paths целиком

Binary diagnostic исправлен. verify_action/verify_image по-прежнему сохраняют str(e):
action mock с ?sig=SYNTHETIC_CANARY попадает в JSON.
Test: SeedAndRelease.test_action_pin_error_diagnostic_no_signed_url.

Неизменённый остаток C-07: source_sha=RECORDED_AT_COMMIT, неполные per-item UTC/
manifest mediaType/provenance, redirect host policy, честный documented cache method.
Pin versions не менять, assets массово не скачивать. Авторское 10/10 не объявляется
опровергнутым; independent download verification здесь не выполнялась.

### R2-08 — C-08: отчёт не подтверждает полный маршрут

Runbook не изменился относительно предыдущего review: шесть широких rows с 20 PASS,
clock_skew_bound вместо фактического clock_evidence, отсутствие полной per-requirement
matrix и CLI/state schema. Package_hash теперь совпадает с формулой runbook, но это
не закрывает весь C-08. Release gate draft manifests/code bindings не синхронизированы.
Принимаемый design не переписывать; обновить implementation binding/manifest/matrix.

Новый source-manifest содержит полезные полные 15 blobs/hashes. Raw transcript при этом
начинается с пустого SOURCE_SHA=; полные argv и per-command UTC/exit отсутствуют.
Result.md содержит общий source SHA/time, но не заменяет raw execution record.
Исправления публиковать новыми evidence, старые не менять.

Нужен один suite entry point для полного completion §4 A/B/C/D, фактические commands,
source commit до execution и отдельный evidence commit, source/evidence frozen scan.
Успешные 65 тестов сохранить; не выдавать сумму methods за покрытие всего контракта.

## 4. Рабочий порядок без дополнительных согласований

Authority остаётся 940c4e7 completion task + 6249b97 ER review + 3d1d1f3 C review.
Работа уже разрешена. PRIMARY HERMES продолжает автономно до полного §5.
Прежде чем следующий итоговый STOP:
1. Исполнимые positive сценарии должны проходить: seed CREATE_ALLOWED; complete lists
   и accepted baseline; successful readiness stages с persisted WAL/receipts; release chain.
2. Negative tests должны исходить из проходящего positive fixture; не создавать PASS
   отказом на другом раннем условии. При изменении API адаптировать harness с traceability.
3. Сверить весь текст R2-01…08 и исходный контракт, включая не покрытые supplied tests
   subpoints. Новые tests — дополнение, не замена полного technical task.
4. Полный source/package manifest/matrix/runbook + одно offline execution evidence.
   Только после этого один final STOP.

Reproduction from repository root:
P8C_REVIEW_ROOT="$PWD" python3 evidence/P8/20261105-64e36a6-architect-review/residual_test.py
Dependencies: Python3 + PyYAML, предыдущий archived regression по его repository path.
accepted-baseline.json должен находиться рядом. Без сети/OCI/cluster.
Исходниковые assertions могут потребовать адаптации интерфейса, но не ослабления смысла.

## 5. Решение

PREVIOUS_REVIEW_REGRESSION=28/28_INDEPENDENTLY_REPRODUCED_PASS
AUTHOR_METHODS=37/37_INDEPENDENTLY_REPRODUCED_PASS
C01..08_FULL_CLOSURE=NOT_CONFIRMED
SOURCE_PACKAGE_ACCEPTED=NO
SOURCE_WORK=IN_PROGRESS/PARTIAL
NEXT_STEP=COMPLETE_EXISTING_EXECUTABLE_CONTRACT
EXECUTION_GATE=NOT_ISSUED

CI_RELEASE / WORKFLOW_PUBLICATION / WORKFLOW_DISPATCH / BOOTSTRAP_PUSH=NOT_AUTHORIZED
LIVE_READINESS / SSH / PRIVATE_REGISTRY_PROBES=NOT_AUTHORIZED
NETPOL_APPROVED_FOR_APPLY=NO
OWNER_HELPERS / PRODUCTION_MIGRATION_DEPLOYMENT=NOT_EXECUTED
P8C=NOT_FINAL_ACCEPTED
P8D–P8G/P9=NOT_AUTHORIZED

Реальные clock evidence, private GHCR и CI runtime остаются будущими prerequisites.
Они не препятствуют завершению перечисленной offline source работы.

