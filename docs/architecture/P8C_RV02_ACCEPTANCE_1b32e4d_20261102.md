# P8C RV-02 — приёмка offline-дизайна после review 1b32e4d

Дата: 2026-11-02 (Europe/Moscow). Architect review через GitHub Connector.
REVIEW_HEAD=1b32e4d87f9925339f2192c7893fc74f2ddae5eb
PARENT=d9a322ad8c4f77ef03aa12566e1c7a9f442bf9cf

## Решение
```text
OFFLINE_DESIGN=ACCEPTED_WITH_RUNTIME_LIMITS
A/B/C=DOCUMENT_CLOSED_AFTER_ARCHITECT_CORRECTIONS
DOCUMENT_REWORK_REQUIRED=NO
COLLECTOR_REWORK_REQUIRED=NO
COLLECTOR_RERUN_REQUIRED=NO
AUTHORIZED_READ_SET_COMPLETE=YES
FLOW_MATRIX_COMPLETE=NO
EFFECTIVE_POLICY_UNION=UNKNOWN
EXECUTION_GATE_READY=NO
PHASE2_NEW_RUN_APPROVED=NO
OWNER_PHASE2_HANDOFF_ALLOWED=NO
NETPOL_APPROVED_FOR_APPLY=NO
CI / WORKFLOW / OWNER_HELPERS / PRODUCTION=NOT_AUTHORIZED
P8C=NOT_FINAL_ACCEPTED
P8D–P8G/P9=NOT_AUTHORIZED
```

Каноническая принятая редакция:
docs/architecture/P8C_RV02_OFFLINE_ROLLOUT_DECISION_20261102.md
**в одном commit с этим решением**, а не неизменённая авторская редакция 1b32e4d.
Новый круг исправления A/B/C для Hermes не назначается. Hermes2 не участвует.

## Что подтвердил Connector
Main был 1b32e4d, один fast-forward commit относительно d9a322a. Изменены только
canonical plan и существующий source-extractions.md. Collector/application/YAML не тронуты.
Локальные утверждения HEAD=origin/dirty=0 не проверяются Connector и здесь не подтверждаются.

Подтверждены исправления Hermes: readyInstances, отказ от firstRecoverabilityPoint-as-WAL,
восстановленные 14 FLOW-ID, точные API tuples, Basic Auth отдельно от TLS/routing,
MetalLB VIP forwarding без обязательного NodePort hop, S3 stale/STOP.
Сверены 17 repo-local source blobs и 3 внешних pinned source blobs; 14 FLOW-ID уникальны.
MetalLB URL — документальная ссылка, не immutable Git blob и не новый runtime факт.

## Что исправлено Architect непосредственно в документе
Чтобы не возвращать весь пакет на очередной круг, выполнены конечные документальные правки:

1. PR-3: resource.group/v1 был ошибочным type/name argv, а label-list не single named object.
   Вместо этого закреплён буквальный discovery.k8s.io/v1 raw EndpointSlice endpoint,
   limit200, один GET, completeness/typed shape и все ready tuples; несколько slices допустимы.
   Источник парсинга kubectl v1.36.2:
   kubernetes/kubernetes staging/src/k8s.io/cli-runtime/pkg/resource/builder.go,
   blob 37e830852c9a29eaca8c545143ee95c108ac2ef7, splitResourceTypeName.
2. PR-5: core/v1 raw Service list с обоими owning selectors, limit2 и cardinality1,
   protocol/UID/ports/selectors/LB projection. PR-6: точные девять GVR paths с limit200,
   без auto-pagination; policy presence/typed semantic comparison и label set.
   PR-3/5/6 суммарно максимум11 GET на один proposed набор; ни один не исполнялся.
   Новый script не создан: безопасный execution wrapper и его допуск — будущий gate.
3. Проверки: удалён placeholder «reason-перечень перечисляется» и выдуманная альтернатива
   имени operator Deployment. Используется наблюдавшийся selector cloudnative-pg Pods.
   True/False/Unknown/absence имеют конечные исходы; reason не заменяет status.
   Введён общий deadline каждой проверки, а не I×N плюс неучтённые request durations.
   INCONCLUSIVE отличается от доказанного отказа, но не разрешает дальнейшую изоляцию.
4. WAL/S3: отсутствие выбранного источника в разрешённом read-set не выдаётся за
   отсутствие метрик в CNPG/Barman вообще. Это явный runtime dependency и STOP до S1.
   Не назначены новые backup/probe/exec/log или повтор принятых тестов.
5. Exposure: Programmed/LB IP не считается точным моментом подключения или E2E proof.
   Риск начинается с создания Gateway. Rollback не считает delete acknowledgement
   прекращением forwarding; требует cleanup принадлежащих Gateway Service/Pods
   до снятия dataplane policy. Удаление остаётся только будущим deployment-gate.
6. Исправлены ошибочная сокращённая owning-name=portal, selector aliases, полный
   Envoy source ref и surveyed monitoring/DNS утверждения. Live enforcement не объявлен
   доказанным ни наличием selectors, ни историческими IP.

## Evidence preservation
Авторский commit переписал уже опубликованный
evidence/P8/20261102-p8c-rv02-rollout-r1-residual/source-extractions.md:
ec873db6970d661da9dccf66fe9db24a88afeadd → c84555ed6bee4046556da174ae681e0097a37722.
Это не новая evidence запись, поэтому утверждение «историческое evidence не изменено»
к данному файлу неприменимо.

В этом commit исходный путь восстановлен byte-for-byte к ec873db… (из d9a322a).
Авторская новая версия сохранена byte-for-byte по новому пути:
evidence/P8/20261102-p8c-rv02-1b32e4d-review/author-source-extractions-1b32e4d.md.
Оба состояния остаются в Git; история не переписана, force не применяется.
Новая проверка — evidence/P8/20261102-p8c-rv02-1b32e4d-review/verification.json.

## Requirement → решение → проверка
| Requirement | Принятая canonical секция | Проверка / граница |
|---|---|---|
| A1 schema | §2 HC-DB | pinned CNPG field readyInstances, 3/3/3; никакого runtime PASS |
| A2 WAL | §2 HC-ARCH-STATE / HC-WAL-PROGRESS | состояние отдельно от прогресса; firstRecoverabilityPoint исключён; INCONCLUSIVE блокирует S1 |
| A3 checks / rollback | §1–2 | конечные deadline/исходы, union, policies before workloads, асинхронная exposure/cleanup; mutations не разрешены |
| B 14-flow | §0/§3–4 | 14 уникальных строк, source dictionary/ref/blobs, отдельные API tuples |
| C1 boundary | §1 | TLS/routing/auth отдельно; source-derived10443, no mandatory NodePort hop |
| C2 reads | §5 PR-3/5 | буквальные raw paths, scope, limit, completeness, safe fields; не live |
| C3 baseline/S3 | §5 PR-4/6 | stale STOP; конечный policy-set comparison не effective union; неподтверждённые поля остаются UNKNOWN |
| Git/evidence | этот раздел + verification.json | добавочный commit, обе версии extraction сохранены; никаких source/YAML изменений |

Это документальная проверка; unit/integration/platform tests не запускались и не нужны
для этих правок. Принятый 9/9 inventory c872eed и source eed114e не переоткрываются.

## Что дальше
Этап доработки offline-документа завершён. Следующая инженерная работа — отдельный
candidate YAML package по уже описанным delta и затем подготовка release/deploy gates.
Текущий commit **не разрешает** изменения policy YAML, CI/workflow publication/dispatch,
реальные helpers, новый live inventory, NetworkPolicy apply/rollback или production deployment.

До runtime-gate отдельно нужны: допустимое свежее подтверждение S3/WAL, текущий
baseline/selected peers, принятый YAML и проверенный release digest; generated Service/Gateway
проверяются в соответствующем deployment этапе. Эти зависимости не закрыты текстом.
Portal UI/API пока не предъявлены работающими; URL и FINAL ACCEPTED не присваиваются.
