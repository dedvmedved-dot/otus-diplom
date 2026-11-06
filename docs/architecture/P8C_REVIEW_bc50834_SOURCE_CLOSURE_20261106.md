# P8C — независимая проверка single-pass пакета bc50834

Дата: 2026-11-06 (Europe/Moscow). Основной Hermes; Hermes2 не участвует.
Вердикт: SOURCE_PACKAGE=REWORK_REQUIRED. Это продолжение задания
P8C-SOURCE-CLOSURE-SINGLE-PASS-20261106 (4786107c41c8e1ed9e69a17190a4bdf490f430b1),
не новый этап и не новый набор требований.

## 1. Что действительно проверено и принято

Проверены через Connector:
- evidence HEAD: bc50834eb9a9757ba44643c0084226133d07880b;
- source: d2e8598a8720cb2dc5935ac33d218498cf846c45;
- source parent: 4786107c41c8e1ed9e69a17190a4bdf490f430b1;
- 31 файл локального snapshot сверен с точными Git blob bytes.
Source commit 02:00:48Z предшествует авторскому прогону 02:01:04Z–02:01:50Z;
новый evidence commit идёт после source. Этот порядок теперь подтверждён.

Независимо выполнены **119/119 штатных test methods PASS**:
23 readiness + 25 active residual + 3 qualification + 4 release + 7 release-negative +
28 regression + 14 scheduler + 15 contract. Qualification CLI = qualified:true;
bash syntax (installer и launcher) и py_compile = PASS.

**C — исправление изоляции принято.** В активной копии assertions сохранены, изменены
fixture path и per-test authority. Historical residual неизменён. Полные 25 методов
прошли, четыре StateAndExecution прошли также в обратном порядке. Не переоткрывать C.
Первоначальный FileNotFoundError независимого запуска был отсутствующим в локальном
snapshot accepted-baseline.json; файл получен, blob проверен, повтор 25/25 PASS.
Это ошибка подготовки reviewer snapshot, не дефект Hermes.

Сохранить исправленные failed/completed/inflight replay guards, S0 baseline route,
WAL-first, shared DB/ARCH GET, предыдущие positive/negative controls и принятые pins.
Положительный synthetic S0→S4 через настоящий main проходит; seed REUSE control проходит.

Но 119 PASS не подтверждают весь A/B. Дополнительная проверка прежнего контракта:
**34 метода: 2 PASS, 32 failed assertions, 0 errors**. Это не 32 новых задания:
ниже единый остаток в четырёх блоках. Четыре проверки структуры templates диагностические;
остальные выполняют production функции/main или shell steps с fake tools.
Строковые structural checks не предписывают имена будущих helpers: при рефакторинге
проверить тот же outcome через новый entrypoint, без ослабления требования.

Evidence: evidence/P8/20261106-bc50834-architect-review/:
completion_contract_test.py, completion-execution.json/.txt, reexecution.json,
reexecution-raw.txt, isolation-reordered.txt, isolation-diff.txt, source-audit.json,
review-scan.json.

Только offline. Python 3.12.14 у reviewer, Python 3.11.15 в авторском transcript.
Все внешние ответы synthetic; фактический subprocess только локальный fake executable.
SSH/cluster/live HTTP/CI/private registry/OCI build/push/sign не выполнялись.
Public pins не скачивались заново. Авторские 10/10 сохранены с прежними пределами доказательства.
Полный shell launcher reviewer НЕ запускал: он удаляет глобальную authority и всегда
запускает network pin verification. Выполнены все его 119 test methods отдельно с private TMPDIR.

## 2. A — budgets, state и action binding ещё не завершены

Authority: single-pass §A; прежние R4-02/R4-05 и completion task §3–5.

| Воспроизведение | Факт на проверенном source | Что завершить в текущем контракте |
|---|---|---|
| overall remaining=1 | main выполняет 23 I/O, requests=255, aggregate=PASS при cap233 | remaining reserve/check внутри каждого I/O, не только перед стадией |
| WAL remaining=1 | wal_requests становится 94 при cap90 | sample не получает право на пять запросов при остатке одного |
| exhausted budget + новый state-dir + тот же valid receipt | S1 выполняет чтения | budget_path объявлен, но main всё ещё read/write_budget(args.state_dir); authority должна хранить общий расход |
| crash после начала попытки | budget отсутствует и в state-dir, и в stable authority | atomic persistent charge до I/O, bytes/elapsed на всех исходах |
| stdout 64 bytes, затем exit1 | попытки учтены, bytes=0 | partial/error bytes учитывать во время transport |
| 300s ожидания между слотами | wal_seconds=0 | WAL elapsed включает окна/ожидания, не только время sample |
| budget.requests=NaN | чтения выполняются | typed finite nonnegative schema, не только v<0 |
| receipt с другим issued_at | read_receipt возвращает S0 | связать receipt с конкретным gate/run, не только source/package |
| S1 operation_end_utc=1, без action receipt | aggregate=PASS | проверенный action receipt / stage / gate / operation boundary, не произвольное число |

Методы test_overall_remaining_one_request_stops_before_second_io,
test_wal_remaining_one_request_stops_before_second_wal_io,
test_budget_cannot_reset_with_new_state_directory_and_same_receipt,
test_inflight_attempt_persisted_before_crash, test_partial_error_body_bytes_are_charged,
test_wal_elapsed_includes_slot_waits, test_nan_budget_blocks_before_io,
test_receipt_from_different_gate_not_authority,
test_post_operation_boundary_requires_bound_action_receipt.

Остаток проверяется целиком: separate WAL/HC/PR/global caps, finite schema,
before-I/O remaining request/body/time, atomic crash/concurrency accounting.
Window replay исправлен; это НЕ автоматически исправляет budget authority.
Не менять лимиты 5/2MiB/30s, 15/6MiB/660s, 90/36MiB/3960s, 233/179MiB/5265s.
source_sha в validate_gate пока проверяется regex, а не trusted manifest/source binding;
gate identity и package identity также остаются разными сущностями по прежнему контракту.

## 3. A — readiness observations, transport и baseline ещё не завершены

Authority: single-pass §A; прежние R4-01/R4-03/R4-04.

| Воспроизведение/проверенный код | Результат | Требуемое завершение |
|---|---|---|
| HC-DB сначала нет Ready, следующий ответ готов | единственный GET, INCONCLUSIVE, окна W/I/N нет | исполнить согласованные bounded health windows с shared DB/ARCH response |
| S4: каждый HC GET укладывается в 14s | PASS при возрасте HC-DB 56s (>30s) | freshness проверяется при финальном verdict, в пределах бюджета |
| incomplete metrics | неполный dict заменяет valid baseline | сохранять baseline только после явной полной валидации; reset/identity/malformed не baseline |
| pod role=replica | S0 PASS | primary role/cluster/name/UID/IP/owner binding до и после |
| sidecar первым, postgres restartCount меняется | S0 PASS | сравнивать нужные containers по имени, не containerStatuses[0] |
| HC-DB kind=Pod с Cluster-подобными полями | S0 PASS | exact per-read kind/apiVersion/scope/identity |
| K8s NetworkPolicy response заменён PodList/v1 | PR-6 PASS | exact GVR→envelope, все 9 ответов и typed namespace/pod selector context |
| 201 operator objects при max_items=200 | PASS | max_items реально enforced |
| PR-5 без metadata/UID/namespace/ownership | S4 PASS | полная принятая identity + tuple/protocol/selector проверка, не только наличие LB IP |
| malformed operator items=[null] | uncaught AttributeError | typed validation, bounded error journal, независимые чтения по контракту |
| Ready.status=CANARY_PRIVATE_VALUE | значение попадает в journal.detail | value-free dispositions; invalid enum не сериализуется как диагностическое значение |
| fake kubectl отвечает через 1.6s при timeout=1 | ответ принят | убрать дополнительные +5s из hard_deadline; remaining sample/window передавать внутрь |
| fake HTTP body завершён после deadline | ответ принят | absolute monotonic deadline во время read, не только socket timeout/post-return |

Методы test_health_transient_missing_then_ready_is_polled,
test_health_freshness_rechecked_at_final_pass,
test_incomplete_metrics_do_not_overwrite_valid_baseline,
test_secondary_role_cannot_pass_primary_sample,
test_postgres_restart_is_checked_by_container_name,
test_hc_db_wrong_kind_cannot_pass_actual_read_path,
test_pr6_wrong_resource_list_cannot_pass, test_list_item_cap_enforced,
test_pr5_without_uid_namespace_ownership_cannot_pass,
test_malformed_health_returns_journal_not_uncaught_exception,
test_journal_does_not_echo_malformed_condition_value,
test_kubectl_hard_timeout_not_plus_five_seconds,
test_http_read_receives_absolute_deadline_not_only_socket_timeout.

Подтверждение кодом:
- main по-прежнему проходит readset один раз; W/I/N/freshness отсутствуют;
- run_wal_window сохраняет m при любом disp != FAIL, включая missing/reset/nonfinite;
  persist_wal_baseline сохраняет metrics без observation identity/time;
- default_http_get остаётся opener.open(timeout) + resp.read(cap+1);
- run_kubectl_raw hard_deadline = monotonic + timeout + 5;
- validate_envelope использует общий API allowlist и kind.endswith("List");
  singleton kind/identity не проверяются, max_items из readset не используется;
- PR-6 последние два ответа (namespace/pods) семантически не проверяются;
- success cache не должен делать observation старее разрешённого возраста.

Восстановить прежний полный контракт, а не отдельные значения fixtures.
Не менять принятую inventory baseline и не выводить EFFECTIVE_POLICY_UNION из неполных данных.
Все новые проверки offline; новый live inventory для исправления source не требуется.

## 4. B — seed/release не прошли сквозную квалификацию

Authority: single-pass §B, completion task Seed/Release и прежний R4-04.

### Seed: конкретные ошибки исполнимого маршрута

1. Новый Deliver step подставляет ${{ github.event.inputs.first_creation_gate }} прямо
   внутрь single-quoted shell script. Валидный JSON с апострофом позволяет исполнить
   shell fragment ДО schema-validation. Независимый локальный sentinel-test это подтвердил.
   Передавать input как данные через env/stdin/file API, без expression interpolation
   в shell source; проверка должна предшествовать protected operations.
2. first-creation принимает любой 40hex source, без сверки с GITHUB_SHA/manifest/repository/
   package/workflow authority. CLI с source=bbbb... вместо рассматриваемого source → VERIFIED.
   Проверка даты/mode теперь есть, но это не полная binding.
3. Private precheck: ЛЮБОЙ private error при наличии такого gate ведёт в CREATE_ALLOWED.
   Исполненный shell step с fake private exit7 дал result=CREATE_ALLOWED и exit0.
   Public/wrong-association/403/timeout/ambiguous-access — STOP; first creation допускается
   только по согласованному конкретному основанию, не после generic nonzero.
4. SEED_TAG всё ещё literal bootstrap-seed; source-bound unique tag отсутствует.
5. kill выполняется только после успешного build. readiness/build/digest failure и cancellation
   не имеют cleanup-route. Даже цикл 30×1s не ограничивает зависший buildctl debug workers:
   bounded command/remaining deadline должны быть частью исполнимого маршрута.
6. Post-seed шага release-check.py registry нет. private-after не доказывает bytes/digest seed.
   registry/private/association/digest evidence должно реально проверяться до успешного seed.
7. seed_not_application_digest лишь записывает bool. При равных seed/app digest step
   завершается exit0; при отсутствующем APP_IMAGE_DIGEST сравнивает с пустой строкой.
   Нужна enforced artifact distinction с надлежащим binding, не запись флага.
   Это не требует наличия реального app-image сейчас: проверяется synthetic route.

### Release и qualification

- Release template неизменён: protected operations не проверяют future execution gate,
  source/package/workflow revision/expiry/run-attempt. Immutable github.sha checkout
  сам по себе не привязывает запуск к принятому application source после workflow publication.
- BuildKit release cleanup на error/cancel также отсутствует.
- verified принимает scan-image.json с ArtifactName/RepoDigests от ДРУГОГО image,
  если Results=[]. Наличие signature/attestation binding не привязывает к image сам scan.
- Qualification принимает seed template после удаления всего precheck job.
  qualified:true поэтому не является полным R-01…08 verdict.
- Нет полного fake-tool исполнения CREATE_ALLOWED/setup/build/postproof/cleanup и release
  gate→tools→single build→private/scan/crypto command outcomes→artifact route.
  Unit artifact checks остаются полезными, но не заменяют этот маршрут.

Методы ReleaseCompletion в completion_contract_test.py; positive seed REUSE сохранён.
No actual build/push/registry/sign/attest требуется или разрешается.
Статические диагностические assertions по именам шагов заменять outcome-проверкой при
выносе в helper; нельзя обходить их добавлением искомого слова в комментарий.
Например, gate должен блокировать fake build/push с нулевым счётчиком, а cleanup —
подтверждаться при fake readiness/build/proof failures и предусмотренной отмене.

## 5. Итоговый пакет, launcher и отчётность

C принято, но runner/evidence ещё не дают оснований объявлять A/B complete:
- run_offline_suite.sh isolated() удаляет /tmp/p8c-readiness и /tmp/p8c-*.reserved.
  Это не private test fixture, а очистка пути production authority. Убрать глобальный rm;
  каждому тестовому процессу private TMPDIR/authority с cleanup только своего каталога.
- verify-pins.py всегда делает HTTP downloads/requests; существующий cache не читается.
  Комментарий launcher «cached; no download unless missing» и это описание результата
  неверны. Использовать уже проверенные bytes/immutable evidence offline; не расширять
  текущую source-задачу повторным скачиванием всех pins.
- test_release_negative.TestDigestPredicate принимает любой exit из (0,1,2) для вызова
  без обязательного file argument. Это не positive digest control. Проверить actual valid
  fixture → exact expected digest/exit0, invalid → nonzero.
- Runbook/matrix утверждают enforced hard transport, valid baseline, exact identities и
  complete routes, которые выше опровергнуты. Исправить матрицу по фактическому коду,
  включая все ранее перечисленные подпункты; не заменять её суммой тестов.
- Полный runtime/test package manifest должен включать реально импортируемые evidence
  fixtures/regression dependencies и роли, а не подразумевать файлы машины автора.
- Порядок source→tests→evidence исправлен и принят. Исторические evidence не переписывать.
  При новом source выполнить релевантную полную suite после commit; единый launcher
  nonzero на любую обязательную ошибку, per-command argv/cwd/UTC/exit/full output.

## 6. Продолжение без новых разрешений и промежуточных STOP

Основной Hermes продолжает **тот же** task 4786107, A/B и итоговый пакет.
Это review уже действующего объёма; нового «продолжай» для source-work не требуется.
C и принятые исправления сохранить. Промежуточные commits/report — PARTIAL, не final STOP.

Сначала закрыть все строки §§2–5 в production, затем все обязательные success/error
routes проверить вместе через реальные entrypoints с fake transport/tool/clock.
Не считать этот regression-файл единственной спецификацией: finite contract уже
зафиксирован single-pass A/B/§5 и исходным completion task, новых функций не добавлено.
Не создавать универсальную систему допусков и не переписывать принятые дизайны.

Итоговый STOP — полный source contract либо конкретный непреодолимый внешний blocker
после завершения всей независимой работы. Отсутствующая функция/полная проверка не
является внешним blocker. Real clock/CI runner/private registry/crypto остаются
внешними prerequisites; они не мешают исправить перечисленные исходники offline.

НЕ менять application/PG17/candidate YAML/6-policy frozen contract/107 policy tests/
collector/inventory9/9/S1/14-flow/offline design. НЕ выполнять SSH/live/cluster reads,
CI/workflow publication/dispatch/token, private registry, реальные build/push,
Owner helpers, NetPol apply, production или повтор backup/PITR/failover.

```text
REVIEWED_SOURCE_SHA=d2e8598a8720cb2dc5935ac33d218498cf846c45
REVIEWED_EVIDENCE_HEAD=bc50834eb9a9757ba44643c0084226133d07880b
EXISTING_SUITE=119/119 PASS (independently reproduced)
ADDITIONAL_CONTRACT=34 methods; 2 PASS; 32 failures; 0 errors
C_TEST_ISOLATION=CLOSED
SOURCE_TEST_EVIDENCE_ORDER=CONFIRMED
A_READINESS=PARTIAL
B_RELEASE_SEED=PARTIAL
SOURCE_PACKAGE=REWORK_REQUIRED
SOURCE_WORK=IN_PROGRESS/PARTIAL
EXECUTION_GATE_ISSUED=NO
CI_RELEASE / LIVE_READINESS / PRODUCTION=NOT_EXECUTED
NETPOL_APPROVED_FOR_APPLY=NO
P8C=NOT_FINAL_ACCEPTED
P8D–P8G/P9=NOT_AUTHORIZED
```
