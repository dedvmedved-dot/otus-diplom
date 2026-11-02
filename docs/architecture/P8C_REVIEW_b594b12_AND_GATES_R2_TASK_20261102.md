# P8C-R1 — review b594b12 и ограниченное corrective-задание

Дата: 2026-11-02 UTC. Исполнитель: основной Hermes; Hermes2 не требуется.
REVIEWED_MAIN_SHA: b594b12debd574baa614496b090068982a79da21
Предыдущее задание: docs/architecture/P8C_CANDIDATE_AND_GATES_R1_TASK_20261102.md (147324a8420a5060c051057bad4f458f34ee8bbc).

## Решение Architect

| Часть | Решение | Граница |
|---|---|---|
| NP-01…04 candidate YAML | ACCEPTED_SOURCE_ONLY | Семантическая delta принята; apply НЕ разрешён |
| Выполненный Hermes Go run | PASS по опубликованному transcript | Не означает полноту G2; Architect Go повторно не запускал |
| G2 coverage | REWORK_REQUIRED | DNS-направление и перечисленные ниже пробелы |
| Release/runtime/deployment drafts | PARTIAL | Не законченные executable gate proposals |
| Collector/S1, inventory 9/9, offline design | ACCEPTED_NOT_REOPENED | Не переоткрывать |
| CI, live/readiness, apply, production | NOT_AUTHORIZED | Ни один execution gate этим review не открывается |

Connector: main совпал с reviewed SHA; parent 147324a8420a5060c051057bad4f458f34ee8bbc; compare содержит ровно 10 ожидаемых файлов. App/collector/accepted design/исторические evidence не менялись.

Независимая конечная Python-модель проверила реальный YAML (blob 6212a016c783419d2e81c9a2325fdaeef9279bc7): 3124 checks PASS, включая точные API tuples и отрицательные комбинации, DNS, пять labels, Barman/S3. Это source-model, не CNI/DNAT/runtime proof. Go в review-среде отсутствует. Evidence: evidence/P8/20261102T205838Z-p8c-b594b12-review/.

## TASK: P8C-R1-CANDIDATE-AND-GATES-R2

Закончить только T1–T4 ниже и evidence. Не запрашивать «продолжай» между пунктами.
Приёмка candidate semantics сохраняется. Изменять networkpolicy.yaml разрешено только для исправления stale-комментария «FULL verified ... allowlist»: это принятый candidate, ещё не runtime-verified.
Разрешены flows_test.go, три gate-draft, компактные актуальные status-ссылки и новые evidence.
Release template/helpers менять только при конкретном воспроизведённом дефекте в пределах прежнего G3; иначе оставить byte-identical.
Не менять app, зависимости, accepted design/collector/fixtures исторического inventory, Owner helpers, deployment/gateway/RBAC YAML.

### T1 — закончить уже заданное G2 coverage

В flows_test.go отрицательные dns-wrong-label-kubesystem и dns-correct-label-wrong-ns направлены bad-DNS -> Portal. Они проверяют Portal ingress, а не DNS egress. Независимый reproduce.py доказывает: удаление DNS podSelector из egress оставляет оба reversed-теста зелёными; правильный Portal -> bad-DNS обнаруживает расширение.

Исправить направление. Таблично закрыть исходное G2:
- CNPG и Portal: все четыре TCP tuples; каждый cross-product, UDP, .100/.104/ещё представитель прежнего /24 запрещены; migrator — все четыре запрещены.
- DNS от CNPG/Portal/migrator/dataplane к правильному peer UDP/TCP53 и к двум неверным peers. Добавить один mutation regression для расширения DNS peer; реальный YAML остаётся источником.
- По каждому из пяти dataplane labels проверить missing/wrong; wrong namespace и 8081 deny. Не требовать запрета всего трафика у pod, который вообще не selected dataplane policy: здесь проверяется доступ к Portal через его ingress.
- S1/S2a/S2b по отдельности сохраняют необходимые CNPG flows; сохранить negative rollback union.
- Проверить точные 6 name/namespace/policyTypes; отсутствие незаданных broad CIDR/unrestricted peer/rule/port/protocol. Ожидаемые baseline empty selectors допустимы.
- Fixtures явно SYNTHETIC; model не доказывает реальную CNI enforcement. Неподдерживаемые конструкции не должны silently разрешаться.

Запустить только go test -count=1 -v ./networkpolicy из portal/. Не повторять весь проект/PG17/collector.
Приложить command, final tested source SHA, Go version, фактический GOTOOLCHAIN, UTC, stdout/stderr, exit; каждый test-ID связать с требованием.

### T2 — runtime-readiness: исправить ложный внешний blocker и выбрать bounded WAL proposal

Удалить утверждение «нет скрейпера -> нет metrics endpoint». Уже принятый P8B доказал endpoint PostgreSQL instance 9187/metrics. Operator metrics и instance metrics — разные поверхности.
Источники, проверенные Architect:
- evidence/P8/20261020T052255Z-task-p8b-r2-sot-metrics-credential-closure/11-barman-metrics-endpoint-discovery.md, blob 6fe4745774f0eac12fece655c69a6f312a6d73ec;
- 12-barman-metrics-raw-sanitized.txt, blob 2af8086164f4f9e003f28c9b9d3404dfe89b7fac;
- portal/internal/collectors/metrics.go, blob 73cb6a887f615ee0bcbc1067397e924b1b53a829: direct HTTP scrape, без обязательного Prometheus;
- cloudnative-pg/cloudnative-pg v1.30.1 docs/src/monitoring.md, blob 69aebcaceb1decacab29762da7046f768b248477;
- тот же upstream config/manager/default-monitoring.yaml, blob 91fc65b07b0b69c218c6eb407df004b808b510f7: pg_stat_archiver query содержит archived_count, failed_count, last_archived_time, last_failed_time, stats_reset_time; predicate — primary либо archive_mode=always.
  URL: https://github.com/cloudnative-pg/cloudnative-pg/blob/v1.30.1/config/manager/default-monitoring.yaml

Подготовить ОДИН минимальный source-bound proposal чтения existing instance exporter с конечным набором cnpg_pg_stat_archiver_* metrics. Сверить точные имена через upstream mapping. Не устанавливать scraper, не добавлять custom query/Secret/adapter, не создавать runtime wrapper сейчас.
Разделить: наличие в продукте, исторический endpoint, текущая доступность/экспорт конкретных families (ещё NOT_EXECUTED).
Три barman_* backup timestamp из P8B не являются доказательством свежего WAL; не подменять ими pg_stat_archiver.

Proposal обязан определить: actor и read-only access path, endpoint discovery/binding к instance UID/роли, transport/TLS/CA, точные series, maximum bytes/requests/window/interval, проекцию без raw body, baseline/post-sample, fresh natural progress, counter reset/restart/role change/error/idle (-1/нет series -> INCONCLUSIVE), отсутствие искусственного WAL switch/write/backup.
Стабильный backend между samples обязателен: случайные endpoints одного Service нельзя сравнивать как одну series.
Успешный archive_command — ограниченный proxy результата архивирования, не независимый S3 readback и не DNS proof.
Если конкретный access path нельзя выбрать по источникам, назвать именно этот недостающий механизм/допуск; отсутствие Prometheus НЕ prerequisite.
Не менять DB app contract: canonical write endpoint/verify-full/роль остаются прежними; диагностика exporter не превращается в Pod-IP DB connection.
PR-3/5/6 + прочие HC-* остаются принятыми; сослаться на точные bounds. Новые reads = PROPOSAL_ONLY/NOT_AUTHORIZED. Никакого live.

### T3 — довести release draft и provenance

Сохранить корректную dependency private-before; package existence сейчас не доказан. Не писать «пустой package/seed» как уже выполнимое Owner-действие. Описать конкретный bootstrap вариант с отдельным будущим разрешением, identity/artifact/visibility/repository binding и проверкой до основного run; либо точно обозначить невыбранный bootstrap-механизм как внешнее условие. Не выполнять push, не ослаблять private-before.

Исправить «Owner предоставляет secrets.GITHUB_TOKEN»: job token автоматически выдаёт GitHub Actions. Owner обеспечивает разрешённые workflow/package settings и publication, а не передаёт значение GITHUB_TOKEN.
Источник: https://docs.github.com/en/actions/concepts/security/github_token (проверен 2026-11-02).
Owner publication и manual dispatch разделены, оба сейчас запрещены.

Добавить полную таблицу existing tool/action/image pins: version/ref, полный digest/checksum, точный источник, прежнее evidence/acceptance либо UNVERIFIED. Не обновлять версии и не перескачивать ранее принятые pins без причины.
Manifest path/blob/SHA256 обязан включать template, install-verified-go.sh, release-check.py, test_release.py; указать exact workflow identity/ref/source/digest constraints и будущие artifacts. Отсутствующие независимые proofs оставить честно UNVERIFIED/CI_ONLY.
Предложить конечный run budget/timeout/retry policy/истечение разрешения (draft, не grant); source/byte change инвалидирует будущий pin. Никаких registry probes/credentials.

### T4 — deployment draft: точные существующие объекты и доказательства

Текущий /healthz отсутствует в исходниках. portal/cmd/portal/main.go (blob d9e8022098f01d777c2fe66e0a13f4742ad04a8f) определяет management /livez,/readyz,/startupz на 8081.
portal/internal/httpapi/server.go (blob c804bf231fc68bb0cfed1b4a0c058a1b938345d4) определяет защищённые /api/v1/*, включая health; перечислить все 11 из actual routes/OpenAPI. Не открывать mgmt8081 через внешний Service.

Заменить общие строки acceptance matrix точными source-derived proposals:
- inventory names/namespaces/kinds RBAC/CA/Secret references/Services/Job/Deployment/Gateway/HTTPRoute, actor/ownership/no-overwrite;
- migration Job success + версия/checksum ledger + schema verification, а не «schema portal в ledger» без query;
- /readyz 200 = готовность, не самостоятельное доказательство verify-full. Разделить pinned config/CA/SNI/no-fallback, observed application DB connection и возможный server TLS proof. Не выдавать ssl=true за hostname verification. Выбрать минимальные санитизированные evidence; если новый механизм нужен — обозначить prerequisite, не писать runtime PASS;
- auth: missing/wrong credentials и authenticated success, secret-safe ввод без argv/log/evidence; TLS/hostname/routing отдельно;
- все 11 API + UI/assets, actual nodes/CNPG, bounded event persistence (точные безопасные наблюдения, без создания искусственных K8s событий/мутаций);
- named ServiceAccount + allowed/denied verb/resource/scope matrix, безопасный authz-only механизм, без попыток destructive mutation. Возможные authorization-review API вызовы явно включить в будущий scope, не выдавать за обычные GET;
- scope/version/ограничения secret scan, platform postchecks и точные finite budgets/timeout/expiry.
Будущие runtime-only доказательства не подменять текущими source tests.

S0 не «readyInstances=3/3/3»: разнести spec.instances/status.instances/status.readyInstances и Ready condition по accepted plan.
Сохранить S0–S4 и rollback: политика до workloads, migration до readiness, Gateway последним. Копировать точную границу exposure из accepted design (не ждать Programmed как гарантии отсутствия внешнего доступа). Gateway cleanup/generated resources проверяется до снятия dataplane egress. NetPol rollback не удаляет existing workloads; DB migration без destructive down-SQL.
При unresolved WAL/access prerequisites S1 остаётся запрещён; это не мешает закончить документы.

## Evidence / Git / завершение

Только новая evidence-directory; исторические reports не исправлять. В b594b12 source/evidence объединены; историю НЕ переписывать.
В новом пакете source commit -> адресные проверки финальных bytes -> отдельный evidence commit.
Полные path/blob/SHA256 всех затронутых source/drafts и release helpers; requirement -> code/doc -> test/check -> evidence. Добавить фактический bounded secret-scan report (scanner/version/scope/exit/limits, значения не выводить).
Не писать новое время старым tests; не считать отсутствие runtime grant blocker для завершения offline-части.

Fast-forward main, no force, expected-HEAD check; unexpected relevant diff -> STOP с diff, без сброса чужой работы. Connector readback.
Один финальный STOP после T1–T4 либо конкретного непреодолимого внешнего blocker после независимой работы.

SOURCE_WORK=IN_PROGRESS/PARTIAL до завершения. PASS только конкретным проверкам.
Финал: SOURCE_SHA, FINAL_MAIN_SHA, T1..T4 status, exact tests/exit, manifest, remaining runtime prerequisites.
CANDIDATE_SEMANTICS=ACCEPTED_SOURCE_ONLY (NP-01..04)
OFFLINE_DESIGN/9_OF_9/COLLECTOR=ACCEPTED_NOT_REOPENED
CI_RELEASE=NOT_EXECUTED
PHASE2_NEW_RUN_APPROVED=NO
NETPOL_APPROVED_FOR_APPLY=NO
OWNER_HELPERS=NOT_EXECUTED
PRODUCTION_MIGRATION_DEPLOYMENT=NOT_EXECUTED
P8C=NOT_FINAL_ACCEPTED
P8D–P8G/P9=NOT_AUTHORIZED
