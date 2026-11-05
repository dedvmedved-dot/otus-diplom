# P8C-R1-EXECUTABLE-PACKAGE-COMPLETION — final result (R4)

Дата: 2026-11-05 (UTC). PRIMARY HERMES. Source-only. Live/SSH/CI/registry/apply/production НЕ выполнялись.

## Закрыто по checkpoint 9a05014 (обязательная source-работа)
- **WAL scheduler** (`wal.Scheduler`): 6 окон (S0 baseline + S1..S4), ≤3 слота на окно со смещениями
  0/300/600s; кумулятивные счётчики requests/bytes/seconds (window ≤15req/6MiB, глобально ≤90req/36MiB/3960s);
  virtual-clock (без wall sleep).
- **Сохранение расхода допуска после non-PASS/crash**: window-state (не reservation-файл) в стабильном
  authority-месте (package_sha256), JSON {attempts, completed}. Retry внутри окна допустим (≤3 слотов),
  после completed/slots-exhausted — блок (no replay). Budget сохраняется в state-dir (budget.json) и
  накапливается, не сбрасывается при non-PASS/crash.
- **Baseline сохранение**: WAL PASS-метрики сохраняются (wal-baseline.json, bound к source/package) и
  читаются как baseline следующей стадии; run_wal_sample возвращает metrics (не только disp/detail).
- **Deadline во время исполнения**: 30s проверяется после КАЖДОГО из 5 запросов (не только в конце).
- Различение: samples внутри окна (retry) vs новый запуск после завершения (blocked) реализовано
  через window-state + слот-счётчик.

## Полная offline suite
```text
SOURCE_SHA=317ebc7ab1839f7dac5a22690b24aabafcc98283
A readiness 23 · B qualification 3 · C release 4 · D release-negative 7 · E qualified:true
F prev regression 28 · G residual 25 · H pin verify exit 0 (10/10) · bash -n + py_compile OK
ИТОГО 90 test methods PASS · 2026-11-05T05:28:59Z–05:29:45Z
```

## Остаётся (CI-only/NOT_EXECUTED, честно)
- Live clock evidence (UNRESOLVED future read proposal) → live PASS требует real evidence.
- CI runtime / private GHCR / rootless availability / cosign·syft·trivy crypto = CI-only.
- Сквозной S0→S4 с virtual clock + receipts + baseline описан и частично покрыт тестами;
  полный live E2E — NOT_EXECUTED (нет live допуска).

```text
SOURCE_SHA=317ebc7ab1839f7dac5a22690b24aabafcc98283
SOURCE_WORK=IN_PROGRESS/PARTIAL (до независимой приёмки)
PUBLIC_PINS_VERIFICATION=ALL_VERIFIED (10/10)
CI_RELEASE / WORKFLOW_PUBLICATION / BOOTSTRAP_PUSH / LIVE_READINESS=NOT_EXECUTED
NETPOL_APPROVED_FOR_APPLY=NO · OWNER_HELPERS=NOT_EXECUTED · PRODUCTION=NOT_EXECUTED
P8C=NOT_FINAL_ACCEPTED · P8D–P8G/P9=NOT_AUTHORIZED
NEXT_GATE_REQUEST=независимая source-приёмка → отдельный execution gate
```
STOP для независимого Architect review.
