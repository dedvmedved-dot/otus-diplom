# P8C-R1-EXECUTABLE-PACKAGE-COMPLETION — final result (R5)

Дата: 2026-11-05 (UTC). PRIMARY HERMES. Source-only. Live/SSH/CI/registry/apply/production НЕ выполнялись.

## Закрыто по review efc6929 (scheduler/state/budget gaps)
- **Scheduler подключён к main**: `run_wal_window` исполняет ≤3 слота на окно (offsets 0/300/600s,
  virtual `time.sleep`), читает/сохраняет baseline между слотами, возвращает PASS/FAIL/INCONCLUSIVE.
- **Первый baseline сохраняется**: первый корректный sample (INCONCLUSIVE «baseline recorded») пишет
  `wal-baseline.json`; `wal_sample` grown+fresh → PASS без op_end (S0-окно), post-op — после op_end+skew.
- **Бюджет считает фактические запросы/байты** (transport-счётчик, не logical-read count); истощённый
  (≥90req/36MiB/3960s) и corrupt budget.json блокируют ДО любых чтений.
- **Повторный запуск**: window-state со статусом `inflight`/`clean_failed`/`completed`; crash/UNKNOWN_OUTCOME
  (inflight) и completed → блок, чистый non-PASS (clean_failed) → retry ≤3 слотов; новый state-dir не сбрасывает window-state.
- **Deadline во время исполнения**: проверяется ДО и ПОСЛЕ каждого transport-вызова; последний ответ,
  пересекающий 30s, даёт INCONCLUSIVE (не PASS).
- **Predicates**: PR-3/DNS port+addresses в одной slice; gateway generation обязателен (не None==None);
  PR-6 felix bpfEnabled drift → FAIL.

## Полная offline suite (source SHA-bound, изолированные прогоны)
```text
SOURCE_SHA=783502a7eff2662d6f7612ccc56c4a9251e16ace
readiness 23 · qualification 3 · release 4 · release-negative 7 · qualified:true
prev regression 28 · residual 25 · scheduler regression 14 · pin verify exit 0 (10/10)
bash -n + py_compile OK — ИТОГО 104 test methods PASS
2026-11-05T17:58:30Z–17:59:17Z
```

## Остаётся (CI-only/NOT_EXECUTED, честно)
- Live clock evidence (UNRESOLVED future read proposal) → live PASS требует real evidence.
- CI runtime / private GHCR / rootless availability / cosign·syft·trivy crypto = CI-only.
- Полный live E2E S0→S4 — NOT_EXECUTED (нет live допуска).

```text
SOURCE_SHA=783502a7eff2662d6f7612ccc56c4a9251e16ace
SOURCE_WORK=IN_PROGRESS/PARTIAL (до независимой приёмки)
PUBLIC_PINS_VERIFICATION=ALL_VERIFIED (10/10)
CI_RELEASE / WORKFLOW_PUBLICATION / BOOTSTRAP_PUSH / LIVE_READINESS=NOT_EXECUTED
NETPOL_APPROVED_FOR_APPLY=NO · OWNER_HELPERS=NOT_EXECUTED · PRODUCTION=NOT_EXECUTED
P8C=NOT_FINAL_ACCEPTED · P8D–P8G/P9=NOT_AUTHORIZED
NEXT_GATE_REQUEST=независимая source-приёмка → отдельный execution gate
```
STOP для независимого Architect review.
