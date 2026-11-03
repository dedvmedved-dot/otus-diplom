# P8C-R1 — review c86f39f: частичная приёмка и закрытие остатка R2

Дата: 2026-11-03 (Europe/Moscow).
REVIEWED_MAIN_SHA=c86f39fe6f5eb6edf17b010fdf3a32e16f669469
PARENT=ba2af0a28ac0209d4db01c72963388b3262044d0
Предыдущее задание: docs/architecture/P8C_REVIEW_b594b12_AND_GATES_R2_TASK_20261102.md.

## Решение Architect

Полное T1/T2/T3/T4=RESOLVED не подтверждено. Это остатки ранее заданных требований, не расширение scope.
Исправленные части принимаются и повторной доработки не требуют:

| Часть | Принято / зафиксировано | Остаток |
|---|---|---|
| Candidate NP-01…04 | ACCEPTED_SOURCE_ONLY; diff YAML только комментарий | Никаких semantic edits |
| T1 | DNS-направление, mutation sensitivity, все 5 missing/wrong labels, migrator4 tuples, stage union | Полнота negative API/DNS и structural guard |
| T2 | Правильный instance exporter, пять WAL series, reset/idle ограничения | Конечные числа, actor/access/transport/binding и error verdict |
| T3 | Automatic GITHUB_TOKEN, hashes template+helpers, список pins, private-before сохраняется | Конкретные source URLs/статусы, bootstrap choice, численный budget |
| T4 | Реальные health routes, все 11 API, readiness != TLS, S0 fields, exposure/cleanup | Object inventory и исполнимые proof/authz/persistence строки, bounds |
| Evidence | 9/9 blob+SHA256 совпали; published Go transcript exit0 | 63 subtests +2 functions, scan/provenance ниже |

Connector подтвердил HEAD/parent и девять изменённых файлов. Release template/helpers byte-identical.
Python-аудит по извлечённым через Connector bytes: exit0; 9/9 hashes MATCH.
Go отсутствует в среде Architect: Go suite самостоятельно НЕ запускался. Авторский transcript содержит
63 RUN/PASS subtests и 2 функции, а не 65 subtests; это уточнение счёта, не опровержение exit0.
Evidence review: evidence/P8/20261103T024805Z-p8c-c86f39f-review/.
Collector/S1/9-of-9/offline design/P8B/PG17 не переоткрываются.

## TASK: P8C-R1-CANDIDATE-AND-GATES-R2-RESIDUAL

Исполнитель — основной Hermes. Hermes2 не участвует.
Завершить R1–R4 и E ниже одним пакетом, без промежуточных запросов «продолжай».
Не переписывать весь проект и не наращивать общий collector.
Разрешены только flows_test.go, три текущих gate-draft, компактные status-ссылки и новые evidence.
Candidate YAML, runtime app, manifests deployment/gateway/RBAC, collector, Owner helpers, release code остаются неизменными.
Если найден отдельный release-code defect — описать reproducer; этим остатком code change вне flows_test.go не разрешается.

### R1 — конечная полнота уже заданных policy tests

Исходник: portal/networkpolicy/flows_test.go, blob 2eb7bae74bd1190eee954db2624c134ab1d46781.

1. API negative table сейчас использует только db, UDP — только db→ClusterIP443.
   Сделать цикл src={db,portal}; forbidden tuple={ClusterIP6443, .101/.102/.103:443,
   .100/.104/.50:6443}; UDP на всех четырёх разрешённых TCP tuples. Migrator4 уже закрыт.
2. DNS wrong-label/wrong-ns сейчас только UDP. Добавить TCP для каждого из четырёх workload peers.
   Изолировать mutation к DNS egress peers (сейчас снимается podSelector со всех namespace peers).
3. TestCandidatePolicyStructure сейчас содержит буквально «policyTypes spot checks»:
   отсутствует проверка exact type-set всех шести policies; нет проверки Ports/Protocol,
   нет проверки пустого peer {} или пустых selectors в правилах.
   Добавить конечную shape/semantic guard по уже принятому YAML:
   - exact apiVersion/kind/name/namespace и type-set без дубликатов;
   - exact допустимые IP/port/protocol tuples, а не только суффикс /32;
   - никаких пустых from/to peers, selector расширений, пустого ports, port=nil или неожиданных port/protocol;
   - baseline podSelector={} допустим на target, не считать его разрешением пустого peer;
   - модель не поддерживает endPort/named ports: отвергать явно до моделирования, не молча игнорировать;
     не требуется реализация новых возможностей evaluator.
   Минимальные negative guard fixtures: extra UDP/SCTP9999 rule, empty peer {},
   удалённый Egress policyType, незаданный /32:6443, endPort.
   Guard применяется к исходному реальному YAML, отдельно mutated copies должны отвергаться.
4. S1/S2a/S2b: добавить DNS TCP и три endpoint6443 к уже проверяемым ClusterIP/peer/operator/S3.
   Fixtures пометить SYNTHETIC; model limitation — source union, не runtime CNI/DNAT.

Один адресный fresh run: go test -count=1 -v ./networkpolicy.
Не повторять общий Go/PG17/collector/UI suite.

### R2 — дописать runtime proposal, не переносить placeholders в будущий gate

Текущий draft blob 557c3fd7e51481318b4a84f2beb8dd2432547328 оставляет
«≤N GET, window W, interval I» и «точный CA/SNI закрепляется в future execute-gate».
Набор WAL metrics принят; выбирать новый источник не нужно.

Заполнить конкретными значениями N/W/I, per-request timeout, hard deadline, max body и total bytes,
общее число samples для baseline и каждого post-step. 5s/1MiB уже предложены — согласовать с total budget.
N/W/I — проектные численные решения в этом source-only задании, не требуют разрешения на исполнение.
Указать actor (основной Hermes через ранее принятый key-only operator path), конкретный сетевой путь
к существующему exporter, exact discovery fields/requests для UID/primary/endpoint binding и
как повторно обнаруживается role/UID/restart change. Не считать ClusterIP стабильным backend.
Считать metrics Service из deployment.yaml PLANNED, а не существующим.
HTTP из исторического P8B и TLS endpoint — разные режимы: выбрать source-backed вариант; если TLS
в текущей конфигурации не доказан, не изобретать CA/SNI. Точно описать требуемую future compatibility
проверку и disposition при несовпадении, без opportunistic HTTP fallback/verify=false.

Задать численные freshness/clock limits. Отдельно определить рост failed_count/last_failed_time,
parse error/NaN, HTTP/network timeout, counter reset, роли/UID/restart, idle и отсутствующие series.
Свежесть last_archived_time должна быть относительно конкретного baseline/этапа, а не просто GET-time.
Нельзя потерять ошибку архивирования за одновременным ростом archived_count.
При естественном idle — INCONCLUSIVE/STOP, не force WAL и не бесконечное ожидание.
Сохранить ограничения доказательства archive_command и различие DNS/S3.
Если access mechanism не выбран по источникам, записать ACCESS_METHOD=UNRESOLVED с точным вопросом,
но всё независимое (bounds/verdict/series/fields) закончить; не называть весь gate executable.
Execution wrapper остаётся отдельным prerequisite и сейчас не пишется.

### R3 — release draft: завершить три незаполненные позиции

Текущий draft blob afd8ba4f8fb923b60e41b044f4465bf5bbd0f0dd:
«источник=template» не заменяет точный upstream источник;
«создаёт ... с точными identity/artifact» не задаёт identity/artifact;
«timeout ... не задан здесь» не является численным budget.

1. Вписать для каждого existing pin точный expanded URL asset/repository commit/image identity,
   полный checksum/ref; принять ранее проверенное только с конкретной ссылкой evidence.
   UNVERIFIED допустим, если независимого proof нет. Не требуется новый registry/network run,
   установка инструментов или перескачивание принятых pins. У теговых annotations actions не утверждать
   verified tag→SHA без proof; authoritative pin — SHA.
2. Bootstrap: выбрать конкретный вариант будущего отдельного bootstrap-пакета с fixed package
   ghcr.io/dedvmedved-dot/otus-diplom-portal, actor, source/artifact identity, механизмом первого private
   upload/repository association, способом private-before подтверждения. Если механизм требует решения
   Owner/Architect — BOOTSTRAP_METHOD=UNRESOLVED и точный выбор, без утверждения «конкретный вариант готов».
   Никакого фактического seed/push/settings mutation сейчас.
3. Предложить численные test/release job timeouts, максимум run/attempt, wall-clock expiry,
   no-retry и source-change invalidation; отметить, где enforcement в unchanged template ещё не реализован.
   Exact workflow filename/ref/OIDC issuer/repository identity и artifacts заполнить литералами/вычисляемыми
   sourceSHA параметрами, не общей фразой «identity literal».
   Внешняя prerequisite не препятствует завершению source-document.

### R4 — deployment draft: заполнить таблицы вместо текста требований

Текущий draft blob e015751de3feccf6f5c508917435c3848dc4074a всё ещё содержит
«разрешённые ... объекты и их names/namespaces» и «SA + verb/resource/scope matrix».
Это перечень требуемой работы, не её результат.

Из существующих pinned manifests заполнить:
- exact kind/name/namespace/source blob/actor/new-or-preexisting/ownership-no-overwrite каждого
  RBAC, CA/Certificate, Secret reference, Service, Job, Deployment, Gateway, HTTPRoute и шести NetPol;
  generated Service/Pods — selectors/owner UID, имена заранее не угадывать.
  Отправные факты: SA portal/portal-reader и portal/portal-migrator;
  ClusterRole+Binding portal-platform-reader; Roles+Bindings portal-db-reader/portal-ingress-reader
  в portal и portal-velero-reader в velero; Job portal/portal-migrate-0001;
  Services portal/portal и portal/portal-db-metrics; Deployment portal/portal;
  Gateway portal/portal-gateway; HTTPRoute portal/portal.
  Эти факты сверить, не ограничиться переписыванием списка.
- RBAC subject=system:serviceaccount:portal:portal-reader, exact verb/group/resource/name/namespace
  allowed и denied матрица из rbac.yaml, включая named reads, secrets/exec/proxy и mutation verbs.
  Actor operator выполняет конечное число authorization reviews (не actual mutations);
  выбрать точный механизм/API body и лимит запросов, без выдачи Portal дополнительных прав.
- Migration: версия и полный checksum из embedded migration; конкретный read-only ledger/schema
  query или existing app signal с обозначенными пределами. Буквальный checksum0001 — не значение.
- DB TLS: какие exact live-safe observations вместе с pinned config/CA/SNI/no-fallback доказывают
  successful verified connection; какой existing endpoint/field даёт app Ping; чего он не доказывает.
  Не вводить superuser, Secret export, arbitrary exec или изменение приложения.
- UI/auth/11API: exact GET paths, ожидаемые статусы/поля, существующий TLS trust/hostname route,
  безопасный ввод Owner credential, per-call bounds и finite total.
- Events persistence: exact наблюдаемые поля/readback и existing app DB tables/signals, window/count/TTL/cap
  из принятого source; нет новых K8s events, writes или перепроверки всей PG17 suite.
- Численные timeout/budget/expiry для deployment proposal и конечное число проверок.
  Из accepted plan наследовать HC bounds с точной ссылкой, без «всё определить позже».
- Missing runtime mechanism допускается только как конкретный UNRESOLVED prerequisite, не как
  успешное evidence и не как абстрактная строка матрицы.

Принятые endpoints, S0, exposure boundary, scopes rollback и canonical DB contract сохраняются.
Gate остаётся NOT_AUTHORIZED даже после заполнения proposal. Не реализовать wrapper/live probe в этом задании.

### E — evidence и единственный итоговый STOP

- Сохранить исторические evidence. Новый source commit до новых tests/evidence commit; отсутствие такого
  разделения в c86f39f не исправлять переписыванием истории.
- Полные tested source SHA + path/blob/SHA256; свежий адресный transcript и requirement→code/doc→test/proof.
- Счёт c86f39f уточнить новым текстом: 2 functions +63 subtests; mutation/stage assertions внутри функции
  не выдавать за отдельные t.Run.
- Secret-scan: предоставить фактическую команду, scanner/version, точный список файлов (включая новые
  evidence), UTC/exit/count и ограничения. Сейчас в manifest есть только summary, команды/версии
  scanner в raw-transcript нет. Значения не печатать. No matches у grep обычно exit1; если wrapper
  возвращает exit0, показать различие, а не предполагать ошибку/успех.
- Проверить каждую строку R1–R4: нельзя объявлять RESOLVED, если вместо требуемых чисел/имён стоят
  placeholder или формулировка самого требования. REVIEW_READY не означает runtime success.
- Публикация main fast-forward с expected HEAD; no force; Connector readback. Independent work
  завершить без нового «продолжай»; остановка только полный пакет или конкретный внешний blocker
  после завершения всего независимого остатка.

SOURCE_WORK=IN_PROGRESS/PARTIAL
CANDIDATE_SEMANTICS=ACCEPTED_SOURCE_ONLY
METRIC_SOURCE_CHOICE=ACCEPTED_SOURCE_ONLY
COLLECTOR/9_OF_9/OFFLINE_DESIGN=ACCEPTED_NOT_REOPENED
CI_RELEASE=NOT_EXECUTED
PHASE2_NEW_RUN_APPROVED=NO
NETPOL_APPROVED_FOR_APPLY=NO
OWNER_HELPERS=NOT_EXECUTED
PRODUCTION_MIGRATION_DEPLOYMENT=NOT_EXECUTED
P8C=NOT_FINAL_ACCEPTED
P8D–P8G/P9=NOT_AUTHORIZED

Новых SSH/live/registry/CI/apply/backup/restore/PITR/failover действий нет.
