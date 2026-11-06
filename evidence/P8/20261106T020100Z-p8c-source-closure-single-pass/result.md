# P8C — Source Closure Single Pass — final result

TASK_ID: P8C-SOURCE-CLOSURE-SINGLE-PASS-20261106. PRIMARY HERMES. Source-only.
Live/SSH/CI/registry/apply/production НЕ выполнялись.

## Что сделано (A / B / C + финальный пакет)

### A. Readiness: один исполнимый процесс S0→S4
- `run_wal_window` исполняет ≤3 слота (0/300/600s) с жёстким deadline 660s и body-cap 6 MiB;
  `run_wal_sample` — 5 запросов, 30s deadline + 2 MiB body-cap, deadline проверяется ДО и ПОСЛЕ
  каждого transport-вызова.
- Раздельные бюджеты: sample 5 req/2 MiB/30s, window 15 req/6 MiB/660s, WAL 90 req/36 MiB/3960s,
  overall 233 req/179 MiB/5265s. WAL-cumulative (`_WAL_TRANSPORT`) и overall (`_TRANSPORT`)
  учитывают фактические attempts/bytes/elapsed, включая ошибки (attempt — до I/O, bytes — после
  успеха); проверка remaining budget — до следующего I/O (`_wal_budget_exhausted` перед каждым
  sample, `budget_exhausted` + отрицательный/corrupt budget — до чтений).
- Window-state `inflight`/`failed`/`completed` → failed/completed/UNKNOWN_OUTCOME не выдают новый
  бюджет; смена state-dir не обходит authority (ключ — package_sha256 в стабильном месте).
- baseline только из валидного наблюдения; S0 fresh — относительно времени первого baseline
  sample (`baseline_observed_at`); S1–S4 требуют `operation_end_utc`; FAIL/reset не стирает baseline.
- WAL-first + shared DB/ARCH GET (dedup), health-чтения свежие на момент PASS.
- typed per-read envelope/kind/apiVersion + точные predicates PR-3/5/6, HC-* (kind, identity, nftablesMode).

### B. Release/seed: исполнимые маршруты
- seed precheck: REUSE | CREATE_ALLOWED | STOP; REUSE/STOP → ноль build/push (шаги под `if !=
  CREATE_ALLOWED`); CREATE_ALLOWED — только по корректному future gate `release-check.py
  first-creation` (отвергает expired/future/`mode!=LIVE`).
- Доставка gate явная: Owner передаёт `first_creation_gate` через `workflow_dispatch.inputs`,
  шаг «Deliver …» пишет его в RUNNER_TEMP — файл не появляется «сам собой».
- setup → bounded ready → build → registry/private/association proof → cleanup (kill daemon после
  build, REUSE/STOP без daemon); Seed.Containerfile not-deployable, seed≠application digest.
- release `verified`: один build/digest связан с SBOM/scan/signature/attestations; неверный/отсутствующий
  proof → nonzero; успешный synthetic baseline проходит весь маршрут.

### C. Устранение зависимости тестов
- Исторический `residual_test.py` (64e36a6) НЕ редактировался. Активная рабочая копия
  `portal/tools/readiness/test_architect_residual.py` даёт каждому тесту StateAndExecution частный
  authority (`TemporaryDirectory` + `patch(RESERVATION_BASE)`), явно разделяя state только внутри
  сценария replay. Assertions replay/failed-блокировки сохранены без xfail/skip; production-защиты
  не ослаблены. Одиночный/полный/произвольный порядок проходят (per-test изоляция).

## Полный offline-прогон (единый launcher, final SHA)
```text
SOURCE_SHA=d2e8598a8720cb2dc5935ac33d218498cf846c45
launcher: bash portal/tools/run_offline_suite.sh → exit 0 (SUITE RESULT: PASS)
readiness 23 · residual-working 25 · qualification 3 · release 4 · release-negative 7
regression 28 · scheduler 14 · contract 15 · pin verify 10/10 · bash -n + py_compile OK
ИТОГО 119 test methods PASS
UTC 2026-11-06T02:01:04Z → 02:01:50Z
```
Полный вывод (argv, cwd, UTC, версии, exit, stdout/stderr) — `raw-transcript.txt`.

## Correction note (прошлый отчёт R6, без переписывания evidence)
В R6 я зафиксировал `test_replay_new_parent_directory_rejected` как «cross-test isolation artifact».
Причина подтверждена: общий fixed gate + отсутствие `patch(RESERVATION_BASE)` в историческом
residual-файле. Исправлено активной рабочей копией (C) — не ослаблением защит и не xfail/skip.

## Итоговые статусы
```text
SOURCE_PACKAGE_READY_FOR_REVIEW=YES
SOURCE_ACCEPTANCE=AWAITING_ARCHITECT
SOURCE_SHA=d2e8598a8720cb2dc5935ac33d218498cf846c45
CI_RELEASE / LIVE_READINESS / PRODUCTION=NOT_EXECUTED
PUBLIC_PINS_VERIFICATION=ALL_VERIFIED (10/10)
P8C=NOT_FINAL_ACCEPTED · P8D–P8G/P9=NOT_AUTHORIZED
```

## NOT_EXECUTED (исключительно внешние prerequisites)
- live clock evidence (реальная привязка времени — UNRESOLVED future-read proposal).
- CI runtime: runner availability (uidmap/slirp4netns), rootless buildctl, private GHCR visibility,
  cosign/syft/trivy криптографическое выполнение.
- полный live E2E S0→S4 (требует live допуска).

STOP для независимого Architect review.
