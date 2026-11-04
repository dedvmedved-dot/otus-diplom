# Architect review: 713a745 — executable release/readiness R1

Дата: 2026-11-04 (Europe/Moscow). Исполнитель исправлений: ОСНОВНОЙ HERMES; Hermes2 не участвует.
Reviewed main: 713a745bc83ff7b90453c001f4f8d32914f9028b.
Parent/task: 5d71dfc345cfacfe98bff42381b7aa36984a7bed.
Действующее задание: docs/architecture/P8C_EXECUTABLE_RELEASE_AND_READINESS_R1_TASK_20261104.md.

## Решение

SOURCE_PACKAGE=REWORK_REQUIRED
SOURCE_WORK=IN_PROGRESS/PARTIAL
RELEASE_TEMPLATE_SOURCE_QUALIFIED=NO
PRIVATE_SEED_TEMPLATE_SOURCE_QUALIFIED=NO
READINESS_WRAPPER_SOURCE_QUALIFIED=NO
PUBLIC_PINS_VERIFICATION=AUTHOR_REPORTED_10_MATCHES_WITH_PROVENANCE_LIMITS
EXECUTION_GATE_READY=NO

Авторский STOP принят как checkpoint, но завершение G1–G6 не подтверждено.
Это не новые требования: ниже воспроизводимые нарушения и пропуски исходного задания.
Одного CLOCK_EVIDENCE_METHOD=UNRESOLVED недостаточно для объяснения незавершённой реализации:
реализация health/WAL, ограничения и тесты могут быть закончены без clock live evidence.

## Что проверено независимо

Connector: HEAD/parent/diff; 15 изменённых/новых файлов (только tools и новое evidence).
19 прочитанных файлов проверены по Git blob; 9/9 записей авторского source-manifest совпали
по blob и SHA-256. Recursive tree не усечён; Seed.Containerfile отсутствует, иных seed/readiness
реализаций, компенсирующих недостающий код, не найдено.

Локально, без сети/SSH/кластера/CI:
- авторские readiness tests: 14/14 PASS;
- авторские qualification tests: 3/3 PASS;
- static qualification: qualified=true; bash -n install-verified-go.sh: exit 0;
- supplied regression_test.py: 22 test methods, 29 failures с учётом subtests, exit 1.
  Тесты требуют корректного поведения; failures воспроизводят дефекты reviewed source.
  Все внешние transport paths в regressions замокированы. Это НЕ результаты live run.

Evidence: evidence/P8/20261104-713a745-architect-review/.
author-reexecution.json и regression-result.json содержат полный stdout/stderr/argv/UTC/Python/exit.
source-audit.json содержит hashes, ограниченную оценку pin evidence и границы проверки.
Git state рабочего дерева Hermes извне не подтверждается; Connector подтверждает опубликованные bytes.
Публичные binary downloads Architect повторно не выполнял; 10 VERIFIED — авторское наблюдение,
не независимое подтверждение скачивания. Отсутствие production-действий не выводится из unit tests.

Принять и сохранить: исходный read-set как заготовку, timeouts 20/30 в release, совпавшие 9 hashes,
выполненные авторские тесты в их реальном узком объёме. Они не доказывают полноту qualification.
Candidate YAML/fixture/107 policy subtests, collector/9-of-9, app, DB, offline design не переоткрываются.

## ER-01 — readiness predicates и исполнение read-set (G4/G5)

Факты:
- classify(): HC-DB/HC-ARCH-STATE возвращают PASS для любого status-объекта;
  HC-PORTAL/HC-GW — даже при readyReplicas=0 / Programmed=False.
- PR-3/PR-5/HC-OP/HC-DNS принимают пустой items; выражение len(items)>=0 всегда true.
  Комментарий про predicates у caller не реализован: main() других predicates не вызывает.
- PR-6 run_read() возвращает list из 9 responses, classify() вызывает doc.get:
  AttributeError покидает main, safe disposition/evidence не формируются.
- max_items и per-read bytes в readset не применяются; PR-5 с двумя item принимается.
- HC-DB и ARCH-STATE выполняют два одинаковых GET вместо shared response.
- Stage applicability есть, но scheduler W/I/N/freshness отсутствует.

Исправить конечные predicates всех PR/HC по G4 и принятому design:
PR3 exact ready API tuples; PR5 exact one generated Service/identity/443->10443/LB/Local;
PR6 отдельная typed complete проверка девяти ответов + pinned baseline comparison;
DB spec/status/readyInstances/Ready, ContinuousArchiving, operator/DNS nonempty ready set,
Portal replicas/generation, Gateway Accepted/Programmed/observedGeneration.
Проверки не делегировать отсутствующему caller или непроверяемому gate boolean.
Сохранить exact read paths и stage applicability. Новая policy в S0, Tier/Felix/labels drift,
API_NOT_SERVED/ошибка, отсутствующий/пустой обязательный ready-set не равны PASS.
Различать read completeness и health verdict.

Тесты: все predicates good + negative из исходного G5; PR6 через настоящий main с mock transport,
не только вызов одной функции; shared response/call counts; stage W/I/N/freshness.

## ER-02 — gate/state/exit/no-overwrite (G2 R-02, G4 budgets)

Факты:
- source_sha проверяется лишь как 40 hex, ни одного сравнения runtime hash/source с gate нет.
- mode кроме TEST_ONLY принимается любой/отсутствующий; future issued_at принимается,
  expiry_hours задаётся входом произвольно; time.mktime интерпретирует UTC как локальное время.
- production CLI --now позволяет подменить текущее время.
- произвольный --stage TYPO: все NOT_APPLICABLE, aggregate=PASS, exit 0.
- повтор с тем же gate и новым --out снова выполняет reads; persistent reservation/budget отсутствуют.
- aggregate=INCONCLUSIVE всё равно даёт process exit 0.
- exists()+write_text() не атомарны; нет exclusive reservation, restrictive modes, устойчивого
  crash/UNKNOWN_OUTCOME state. Ошибки JSON/OSError/неожиданного типа могут выйти traceback.

Реализовать минимальный source/hash/run/stage-bound future gate по исходному заданию,
не новую систему управления допусками. Точные allowed mode/stage/context, UTC-aware issued/expiry
<=24h, reject future issue/invalid types, package dependency hashes до любых requests/output.
Test clock/transport injection остаётся в тестах, без production CLI bypass.
Атомарно резервировать run/stage до первого I/O; повтор/skip/wrong receipt/unknown outcome STOP,
даже если выбран другой output path. Restrictive state/output, no-overwrite including race/symlink.
Фактический неполный/непройденный результат — nonzero exit и safe persisted disposition;
unknown stage не может дать PASS. Нельзя выводить новое разрешение из failed process.

Тесты: supplied gate/UTC/stage/replay/exit cases плюс source hash mismatch, race, state crash,
valid receipt и законная последовательность. Source-only fixtures не являются execution gate.

## ER-03 — typed safe transport/journal (G4/G5)

Факты:
- path regex запрещает shell metacharacters, но допускает /api/v1/namespaces/portal/secrets.
  run_read доверяет изменяемому readset, его bytes gate не связывает.
  Это не утверждение, что текущий fixed readset сам читает Secret; отсутствует требуемая защита границы.
- validate_envelope принимает continue:null, неверные apiVersion/items/metadata; нет exact
  GVR/kind/scope/identity/resourceVersion проверок и typed projection.
- subprocess.run(capture_output=True) буферизует полный stdout/stderr до проверки len:
  cap после чтения не ограничивает память/обработку ответа.
- journal не содержит требуемых UTC/path/real exit/counts; transport categories схлопнуты.
  Реальный exit=0 и PARSE_ERROR нужно различать; None — только когда exit не получен.

Исправить exact request allowlist + hash-bound readset; typed per-read envelopes/items,
optional item TypeMeta только из проверенного typed-list context; explicit presence/null semantics,
finite numbers, limits, no unknown semantic loss. Не делать универсальный sanitizer.
Bounded streaming и hard deadline всей операции (headers/body для metrics, subprocess для kubectl),
ограничить stderr без вывода payload, terminate/wait/cleanup, no late process/request.
Сохранять только безопасную проекцию и конечные value-free коды; parse/projection failure
не должен ронять весь процесс или раскрывать raw data. No overflow processing.
Выполнить весь safe-journal контракт G4. Mock tests: slow body/oversize/process timeout/canary,
wrong GVR/scope/null/limit; no arbitrary path и отсутствие вызова при неверном package hash.

## ER-04 — WAL, clock contract и суммарные бюджеты НЕ реализованы (G4 §§6–7, G5)

В run_read для method=wal единственная реализация — raise ReadError
("WAL read requires the wal executor ..."). Другого wal executor в пакете нет.
Нет HTTP exporter client, primary/UID/IP/owner/role binding, metrics parser, before/after bracket,
sample history, operation boundary, 0/300/600s scheduler, 90/233-request counters и clock validator.

Реализовать принятый 5-request sample Cluster->Pod->metrics->same Pod->same Cluster.
Сохранить точные нормы: 5s/request, 30s/sample, 660s/window, 6 windows, max3 samples/window;
WAL90req/36MiB/3960s; overall233GET/179MiB/5265s observation ceilings.
Каждый реальный запрос/byte/time учитывается; gate может сузить ceiling, но не расширить.
HC-DB/ARCH-STATE shared. Уложиться в HC freshness без непосчитанного final sweep.
No env proxy/redirect/arbitrary backend, только validated primary Pod literal IP:9187.
Same identity до/после; failure/reset/restart/role swap приоритетнее archive growth.
Idle исчерпывает только planned slots -> INCONCLUSIVE, не бесконечный retry.

Реализовать clock evidence input format/hash/provenance/node/backend/validity/numeric bound validator.
Clock live evidence остаётся NOT_EXECUTED; отсутствие источника допустимо честно оставить UNRESOLVED
с ОДНИМ конкретным future read proposal. Это не разрешает пропустить validator/fixtures/WAL code.
Без actual valid clock evidence live verdict не PASS. S0/pre-operation/post-operation baseline
и time inequalities сохраняются из исходного task, не упрощаются.

Полная G5 WAL/clock/state test matrix: happy path synthetic data; malformed/missing/duplicate/nonfinite
metrics, reset/failure/idle/identity swaps, old/future timestamps, expiry/skew/missing provenance,
budgets и slow-read. Virtual clock: никаких реальных ожиданий 300/600s и никаких live probes.

## ER-05 — release execution gates + qualification (G2 R-01…08)

Connector diff release template содержит ТОЛЬКО две добавленные timeout-minutes.
Не реализованы typed future gate/hash/24h expiry/run-attempt control и различение
workflow publication revision/application source revision.
Existing rootless wait не имеет bounded individual buildctl probe/cleanup; runner dependency
contract отсутствует, apt-get install uidmap/slirp4netns остаётся unpinned/unqualified.
Runner availability действительно CI-only; описание/проверки dependency contract — source work.

release_qualification.py:
- seed parsed object вообще не проверяется (checks(release,{}) -> []);
- on проверяется regex по исходному файлу, parsed push trigger не учитывается;
- action @main проходит; проверяется только последний checkout;
- extra permissions проходят; отсутствие seed gate/body не обнаруживается.
Три теста проверяют собственные слабые predicates, а не G2/G3.

release-check.py unchanged: verified проверяет непустые файлы, но не parse/binding scans,
private-before/after, registry/build metadata и другие required artifacts.
Supplied synthetic test получает payloadBinding=PASS при INVALID_NOT_EVIDENCE в этих файлах.
Это не обход Cosign-криптографии: тест фиксирует недостающую G2 R-07 валидацию артефактов;
реальные cosign verify steps в будущей CI всё равно необходимы.

Завершить весь G2, сохраняя уже принятые build/sign/attest/private/checksum steps.
Gate/rerun/expiry/source/hash controls ДО protected actions; minimum exact job permissions,
all immutable actions/checkouts, tested bounded rootless lifecycle, explicit runner contract.
Required artifacts: schemas/identity/source/digest/exit binding; failed scan/signature/attestation
или incomplete diagnostics не превращаются в release PASS.
Один build/verified digest, two attestations и actual future verify exits, без смешения seed.
Квалификатор проверяет переданные parsed templates и исполнимые helpers, а не наличие строк
в комментариях. Все R-08 negative cases исходного задания, включая mutations и HTTP failures.

## ER-06 — seed не является исполнимым bootstrap (G3)

Доказанные пропуски:
- buildctl вызывается без установки/проверки/старта BuildKit и без созданного Seed.Containerfile;
- step private вызывает helper, требующий env GITHUB_TOKEN, но step его не передаёт
  (secrets.GITHUB_TOKEN в login action автоматически не экспортируется в другие steps);
- existing private package не делает no-op: затем выполняется push;
- 404 всегда STOP, отсутствует предусмотренная separate Owner-confirmed first-creation ветка;
- нет future gate/expiry/run budget/timeout, source-bound unique tag и repository label;
- глобально packages:write + лишний id-token:write; не минимальные job-scoped permissions;
- echo KEY=VALUE создаёт не JSON файл seed-evidence.json;
- отсутствуют post-push registry byte/digest proof и тесты, исключающие seed как app IMAGE_DIGEST.

Реализовать конечный G3-маршрут, выбранный media type и literal artifact recipe на verified toolchain.
Existing private+associated -> NOOP/REUSE без login/push при отсутствии необходимости;
public/wrong/ambiguous -> STOP; разрешённая first-creation ветка проверяет отдельное будущее Owner
основание и package permissions, а не делает вывод из 404.
Никаких реальных Owner settings/credentials сейчас не получать.
Минимальные job permissions, bounded preparation, digest/visibility/association verification,
валидный typed evidence, mocks всего decision tree и zero push при отказе.
Контракт private-before основного release не ослаблять.

## ER-07 — pins/provenance/output hygiene (G1)

9 source file hashes совпадают; в авторском pin-verification есть 10 reported VERIFIED.
Но source_sha=RECORDED_AT_COMMIT, lock.source_sha=TO_BE_RECORDED_AT_VERIFY; нет per-item UTC,
полных command/exits и upstream checksum/provenance references, runner dependencies не покрыты.
Binary verification сравнивает download только с declared lock checksum. Postgres record не
фиксирует media type/platform level. Action record доказывает существование SHA, не tag equality.

verify-pins.main возвращает None/exit0 даже при MISMATCH/UNAVAILABLE (mock reproducer).
http_get_follow допускает любой redirect, нет проверки HTTPS/official CDN allowlist.
final_url сохраняет весь query: пять GitHub CDN URL содержат sig/jwt.
Это временные download параметры публичных release assets; нет оснований объявлять их
Owner/production credentials. Их значения не воспроизводить в новых отчётах/логах.

Исправить verifier: explicit aggregate failure, strict input/redirect/source scope, sanitize query/
fragment/userinfo до persistence, safe error codes, per-item provenance/UTC/actual exit.
Официальный original asset URL + sanitized final origin/path + exact byte hash достаточно для
адресации; подписанный query не требуется. Никакого credential rotation workflow этим review не выдано.

Существующие правильные hashes не менять. Для unchanged downloaded bytes допустим cached
re-hash + immutable source evidence; не требовать повторного массового download без причины.
Недостающие официальные checksum/provenance/manifest facts получить в уже разрешённом public scope,
либо точно обозначить limit/UNAVAILABLE. Не подменять версию/пин на latest.
Историческое evidence не редактировать/не force-push: новый sanitized replacement artifact + ссылка
SUPERSEDES_FOR_CURRENT_USE, без копирования прежних signed URL.
Новый scan должен охватывать source И новые evidence, проверять URL credentials/query tokens,
ошибки и canaries, различая regex no-match и доказательство отсутствия всех секретов.

## ER-08 — реальные тесты, runtime manifest и отчётность (G5/G6)

raw-transcript.txt имеет 12 строк summary без команд/UTC/exits и readiness test count.
Новый code+evidence снова опубликован одним commit, вопреки G6 source-then-tests-then-evidence.
source-manifest покрывает 9 changed files, но не полный runtime package/imports/executed helpers;
нет runbook, requirement->code->test->evidence matrix, clock proposal и synchronized drafts.
These are source deliverables, not external prerequisites.

Сохранить старый checkpoint; новый результат:
1. Завершить ER-01…08 и весь исходный task, включая подпункты вне этого summary.
2. Source commit; реальные адресные тесты на exact source SHA; полный raw transcript
   (команды/cwd/versions/UTC/exit), затем отдельный evidence commit.
3. Package manifest: все runtime dependencies (в том числе unchanged accepted helpers/imports),
   full source/blob/SHA256, runtime/test-only roles, literal future commands/architecture/versions.
4. Полная matrix всех G1/G2 R-01…08/G3/G4 predicates+budgets/G5/G6.
   Source condition / mocked proof / CI-only/live prerequisite обозначены раздельно.
5. Frozen source scan + отдельный frozen NEW evidence scan, output вне input,
   full argv/files/patterns/versions/exits/limitations. Не сканировать только source и заявлять
   безопасность pin evidence. Не печатать обнаруженные реальные значения.
6. Runbook и drafts синхронизировать со способом исполнения и конкретными remaining prerequisites.

Авторский test_successful_run_fail_closed создаёт fake kubectl с cat JSON как имя файла;
реальные ответы не подаются, transport падает, assertion допускает INCONCLUSIVE и exit0.
Исправить harness: проверять literal argv, отдавать realistic fixtures по read ID,
утверждать точный verdict/exit/call-count/state/output, а не PASS OR INCONCLUSIVE.
Supplied 22-method regression — минимальный reproducer, НЕ вся acceptance suite.
Если helpers реорганизованы, сохранить смысл assertions через публичный entry point, не обходить
их удалением проверок/подменой fixture. Отдельно зафиксировать positive controls.

## Продолжение без нового разрешения

Основной Hermes продолжает тот же P8C-R1-EXECUTABLE-RELEASE-AND-READINESS-R1.
Source-only допуск исходного task остаётся действующим; этот review задаёт конкретную коррекцию.
Не ждать нового «продолжай» между ER-пунктами. Промежуточный progress/commit допустим.
Следующий итоговый STOP — после полного source package либо конкретного непреодолимого
внешнего blocker, когда независимая работа завершена. Stub/caller-not-implemented не blocker.

Все execution запреты сохраняются: никаких SSH/live/private registry probes, workflow publication/
dispatch, CI/seed push, реальных Owner helpers, NetPol apply, production migration/deployment.
Не использовать workflow token/раскрытый пароль. Не повторять accepted 9/9/PG17/backup/PITR/failover.
Никаких новых манифестов политик, app/RBAC/Gateway изменений этим review не разрешено.
До независимой приёмки SOURCE_WORK=IN_PROGRESS/PARTIAL; PASS только конкретным проверкам.

PHASE2_NEW_RUN_APPROVED=NO
NETPOL_APPROVED_FOR_APPLY=NO
CI_RELEASE / WORKFLOW_PUBLICATION / WORKFLOW_DISPATCH / BOOTSTRAP_PUSH=NOT_AUTHORIZED
OWNER_HELPERS=NOT_EXECUTED
PRODUCTION_MIGRATION_DEPLOYMENT=NOT_EXECUTED
P8C=NOT_FINAL_ACCEPTED
P8D–P8G/P9=NOT_AUTHORIZED
