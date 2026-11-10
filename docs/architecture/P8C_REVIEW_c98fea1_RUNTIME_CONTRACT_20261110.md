# P8C — независимый review c98fea1: адресные fixes приняты, исполнимый контракт ещё PARTIAL

Дата: 2026-11-10. Основной Hermes; Hermes2 не участвует.
Продолжение прежнего P8C-SOURCE-CLOSURE-SINGLE-PASS и review
`3ed8d029231793c3fa488cde7e90892b369faa23` (e60d1db), без нового объёма и execution-допуска.

**SOURCE_PACKAGE=REWORK_REQUIRED.** Все 194 прежних метода проходят, включая 17 supplied.
Но проверка полного контракта обнаружила остаток в accounting, health scheduler,
реальной привязке release-gate и достоверности route E2E. Это source-работа,
воспроизводимая offline; она не зависит от доступа к кластеру/GHCR/CI.

## Проверенная база и evidence

Connector подтвердил fast-forward:
`3ed8d029231793c3fa488cde7e90892b369faa23` →
`61e4a44e34cd680bafefc29851f382e2eb2102dd` (source) →
`c98fea1af48128a2f1db7b600f7e9475c5b3914e` (evidence/main).
Изменены tools/readiness/release templates, рабочие fixtures, runbook и новые evidence.
Application/PG17/NetPol/collector/inventory не изменены.

Независимо на exact Connector blobs:
- **194/194 active test methods PASS**, qualification CLI exit0.
- **12 дополнительных controls: 2 PASS / 10 failed assertions / 0 errors**, exit1.
- Python 3.12.14; авторский Python 3.11.15. API/HTTP/часы/fake tools synthetic.
- 51 локальный исходный/reference файл сверен с Git blob SHA дерева Connector.
- Python syntax и bash -n PASS. Shell launcher целиком не запускался: бинарный pin-cache
  автора здесь отсутствует. Все его 194 метода и qualification CLI выполнены отдельно.
  Авторский cached pins10/10 не обозначается независимым повтором upstream verification.
- Offline network guard запрещал DNS/connect в дереве тестовых процессов; новых сетевых
  попыток тестов не зафиксировано. SSH/cluster/CI/private registry/real build/push/sign не было.

Evidence: `evidence/P8/20261110-c98fea1-architect-review/`:
`reexecution.json` + `reexecution-raw.txt`, `residual_contract_test.py` +
`residual-contract.txt` + `additional-execution.json`, `audit_routes.py` +
`route-audit.json`, `source-manifest.json`, `syntax-execution.json`, `review-scan.json`.
Воспроизведение из корня repo: `P8C_REVIEW_ROOT=$PWD python3 <evidence-path>/residual_contract_test.py -v`.
Контроли не являются новым списком требований вместо исходного контракта.

## Что закрыто — не переоткрывать

Атомарное ADD под flock для request charges действительно исправляет потерю двух списаний
и повторную выдачу последнего request slot. Исправлены durable запись явно переданных
seconds, отказ на over-cap суффикс, min(overall remaining, METRIC_CAP) для HTTP,
cluster-scoped NamespaceList, новые поля action_receipt, безопасная доставка release input
через env→file, обязательность полей gate, action cache commit_sha binding.

Все 17 предыдущих воспроизведений теперь PASS. C isolation, frozen evidence и принятые
app/PG17/policy6/107 tests/inventory9/9/S1/14-flow/design сохраняются. Новый review не отменяет
эти результаты. Требуется закончить оставшийся контракт целиком, не откатывать fixes.

## R1. Accounting должен учитывать фактически исполненный I/O, а не только вызовы helpers

| Проверка production-пути | Наблюдение | Необходимое завершение прежнего A1 |
|---|---|---|
| В каждом fake metadata/HTTP вызове проходит 1s; полный S0 | PASS; elapsed321s, budget.seconds295s | учитывать elapsed I/O наряду с sleep; не терять 26s |
| WAL body remaining=1 до первого metadata GET | transport получает cap262144 | ограничивать запрос минимумом remaining sample/window/WAL/overall, не только overall |
| Overall remaining2, fake stdout=`{}X` | ReadError, но authority.bytes остаётся прежним | сохранять реально потреблённые bytes на отказе; не читать сверх выделенного бюджета |
| WAL seconds3959, добавление2 | исключение проглочено; authority остаётся3959 | расход/исчерпание не может молча исчезать |

Тесты: `RouteControls.test_actual_transport_elapsed_persists_in_overall_budget`,
`test_wal_remaining_byte_limits_first_metadata_read`, `TransportDurability.*`.
Положительный здоровый S0 control проходит.

Причины в source:
- `_count_seconds` вызывается для ожиданий, но elapsed metadata/HTTP в overall не добавляется.
- `_count_wal_seconds` глотает `ReadError` от `_charge`; runtime увеличивается, authority нет.
- `_charge(bytes)` проверяет cap уже ПОСЛЕ чтения. При превышении бросает исключение без
  сохранения фактического расхода. Transport читает ещё один байт после достижения cap.
- `_remaining_body` использует process-local base+delta и только overall; window/sample/WAL
  остатки не ограничивают каждый I/O. Atomic ADD после I/O не заменяет резервирование до I/O.

Завершить единый механизм reservation/consumption/failure для всех принятых уровней.
Сохранить request concurrency fixes. Для bytes/time обеспечить либо корректное резервирование
остатка, либо сериализацию исполнителя в том же authority; crash не должен выдавать расход заново.
Отказ не должен превращаться в «расхода не было». Не маскировать ошибку обрезанием counters.

Hard deadlines из предыдущего review также остаются source-остатком: `run_read` передаёт
15s, WAL передаёт5s без минимума remaining enclosing deadline; `default_http_get` проверяет
deadline после blocking read, но не ограничивает этим остатком сам read. В kubectl остались
0.08s grace и minimum0.1s wait. Исполнить абсолютные пределы внутри I/O, а не только отвергать
поздний результат. Часы/transport в offline тестах должны расходовать время, иначе эта ветвь
не проверяется. Все принятые caps сохраняются; нового live чтения не требуется.

## R2. Health W/I/N: таблица должна управлять исполнением и общим бюджетом

Сейчас для DB/ARCH/OP/DNS/Portal hardcoded `retries=2`. Это first GET + 2 retries +
final sweep = максимум4 наблюдения, а не принятый N6. Для Gateway `retries=12` даёт
first +12+final = **14 GET**, хотя N≤12.

Независимые controls:
- HC-OP здоров на пятом наблюдении внутри W60/I10/N6. Реально только
  `[300,310,320,320]`, INCONCLUSIVE. Пятый GET не выполнен.
- HC-GW постоянно indeterminate. Реально14 GET: 1800,1810,…,1920,1920.

Завершить настоящий scheduler по принятой таблице, не увеличивать число retries под тест:
DB/ARCH(shared), OP, Portal — W60/I10/N6; DNS — W30/I5/N6;
Gateway — W120/I10/N≤12. Учесть first GET и freshness re-read внутри N, а не сверх него.
Окна имеют абсолютный конец; последовательные sleep для разных checks не должны незаметно
расширять окно. Timestamp принадлежит фактическому GET, включая shared DB/ARCH cache.
Сохранить failure precedence и итоговую freshness (обычные checks≤30s, Gateway≤60s).

## R3. Release-gate: обязательное поле ещё не означает binding

Настоящий `release-check.py release-gate` при полном корректном документе:

| Изменение относительно положительного control | Фактический результат |
|---|---|
| gate.attempt=1, фактический argv run_attempt=2 | exit0, gate=bound, attempt2 |
| gate.workflow_sha другой, GITHUB_WORKFLOW_SHA исходный | exit0 |
| issued_at на120s в будущем | exit0 (допускается +300s) |

Положительный bound gate — exit0. Это не failures из-за неполных fixtures.

Причины: `attempt` argv читается, но не сравнивается; workflow_sha проверяется только regex;
future grace300s не предусмотрен принятым gate-контрактом. Требуются actual attempt=1,
совпадение документа с actual workflow SHA, уже наступивший issued_at и реальная expiry.
Проверить тот же полный контракт first-creation: отсутствие ожидаемого runtime binding не
должно означать разрешение (сейчас workflow сравнивается только если env присутствует),
future gate также не должен активироваться раньше времени. Источник binding должен быть
явным в template и fake environment; не подставлять произвольную строку в проверяемый документ.

Доставка release_gate через env→file принята. Не требуется менять её или публиковать workflow.
Нужны позитивный bound route и отрицательные controls с одним изменённым полем каждый,
через реальные validators, без замены результата gate на PASS.

## R4. Route E2E — исправить исполнение и проверки результата, не расширять mocks

`audit_routes.py` оборачивает `_run_step`, вызывает его настоящую реализацию и фиксирует
returncodes. Тесты остаются PASS при следующих сбоях:

| Тест | Реальный шаг | Exit / ошибка |
|---|---|---|
| seed CREATE_ALLOWED | Verify seed registry | 1 / SEED_DIGEST unbound |
| seed CREATE_ALLOWED | Record seed digest | 2 / mocked-private |
| release full route | Private prerequisite | 1 / нет go-version.txt и go-binary.sha256 |
| release full route | Sign keyless | 1 / не подставлен github.workflow |

В extraction snapshot дополнительно exit129 на git provenance, потому что snapshot не git
checkout. Это ограничение reviewer-среды, **не дефект production**; остальные приведённые
сбои возникают из устройства самого test harness и не зависят от наличия `.git`.

Важное разграничение: ошибки `SEED_DIGEST`/GitHub-expression здесь не доказывают, что Actions
в production не передаст переменные. Они доказывают, что текущий E2E не эмулирует передачу
GITHUB_ENV/GITHUB_OUTPUT и не проверяет успешное исполнение маршрута.

Кроме того:
- release-тест assert exit0 только для gate; большинство остальных returncodes игнорируются;
- steps с `curl -sSfL` пропускаются целиком. Вместе с установкой пропускаются SBOM generation
  и Trivy scans, которые находятся в тех же steps;
- `verified` — локальный semantic artifact validator, не network-only режим. Shim возвращает
  готовый `payloadBinding=PASS`, не проверяя отсутствующие/неправильные proof files;
- IMAGE_DIGEST заранее задан `a…`, fake build пишет `e…`; GITHUB_ENV не импортируется.
  Настоящий validator должен заметить такой mismatch; он сейчас подменён;
- negative readiness/build/proof routes заявлены в docstring, но отдельного исполнения и
  assertions cleanup/no subsequent protected operations нет.

Завершить один offline маршрут каждого вида. Fake разрешён на внешней границе: download,
registry/API transport, crypto/tool binaries. Validators и принятие решений должны исполняться
реально. Эмулировать outputs/env/if/failure/always cleanup, проверять exit каждого обязательного
шага, digest связи и полный proof package. У внешних tools выдавать реалистичные synthetic
файлы, а не `{}`/готовый PASS. Upload-action можно проверить по перечню и содержимому файлов,
не отправляя их. При negative case ожидаемый nonzero — результат теста, но дальнейшие
protected steps должны отсутствовать, cleanup — присутствовать.

REUSE/STOP и новый source input сохраняются. Не требуется реальный OCI build, CI или crypto.

## E. Cached image proof: осталось сравнение наблюдаемого digest

Action commit_sha mismatch исправлен. Image path сравнивает только cached `declared` с lock,
после чего доверяет status VERIFIED. Cache с declared=lock, но manifest_sha256 другого образа
всё ещё даёт exit0. Контроль `test_offline_image_evidence_requires_observed_digest_binding`.
Связать lock/ref/declared/observed digest и существующее integrity/provenance evidence.
Новый upstream download не нужен, принятые публичные pins не переоткрываются.

## Продолжение — один пакет основному Hermes

Это продолжение прежней source-работы, дополнительного «продолжай» не требуется.
Закрыть R1–R4/E целиком вместе с runbook/matrix/manifest. Не выдавать SOURCE_WORK=COMPLETE
по зелёным tests, если внутри full-route игнорируются nonzero или validators заменены PASS.
12 controls — примеры нарушений прежнего контракта; они не заменяют полный review.

До финального отчёта самому проверить trace каждого positive/negative production route:
actual calls, время/bytes/counters, неизменность authority, промежуточные outputs и конечный
вердикт. Затем source commit → один полный offline launcher на этом SHA → новый evidence
commit. Любой mandatory fail должен делать итоговый exit ненулевым. В evidence отдельно
отметить fake-tool proof и то, что потребует CI/live. Промежуточные commits допустимы как PARTIAL.

Не менять historical evidence. Не переоткрывать app/PG17/policies/inventory/S1/14-flow/C isolation.
Fast-forward без force/rebase/amend. Hermes2 не участвует.
Никаких live/SSH/cluster/Owner helpers, CI/private registry, workflow publication/dispatch/token,
реальных build/push/sign, NetworkPolicy apply, production, backup/restore/PITR/failover.
Следующий итоговый STOP — целый source-пакет либо конкретный внешний blocker после завершения
независимой source-работы. Перечисленные defects внешними blockers не являются.

```text
REVIEWED_SOURCE_SHA=61e4a44e34cd680bafefc29851f382e2eb2102dd
REVIEWED_EVIDENCE_HEAD=c98fea1af48128a2f1db7b600f7e9475c5b3914e
EXISTING_ACTIVE_TESTS=194/194 PASS
PREVIOUS_17_CONTROLS=17/17 PASS
QUALIFICATION_CLI=exit0; not equivalent to complete E2E acceptance
ADDITIONAL_EXISTING_CONTRACT=12 methods; 2 PASS; 10 failures; 0 errors; exit1
ROUTE_E2E_AUDIT=mandatory step failures ignored; semantic validator mocked
SOURCE_PACKAGE=REWORK_REQUIRED
SOURCE_WORK=IN_PROGRESS/PARTIAL
EXECUTION_GATE_ISSUED=NO
CI_RELEASE / LIVE_READINESS / PRODUCTION=NOT_EXECUTED
NETPOL_APPROVED_FOR_APPLY=NO
P8C=NOT_FINAL_ACCEPTED
P8D–P8G/P9=NOT_AUTHORIZED
```
