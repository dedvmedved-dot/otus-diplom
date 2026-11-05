# P8C-R1-EXECUTABLE-PACKAGE-COMPLETION — final result (R6)

Дата: 2026-11-05 (UTC). PRIMARY HERMES. Source-only. Live/SSH/CI/registry/apply/production НЕ выполнялись.

## Закрыто по review 4ade3d5 (16 отказов в 15 методах → 0)
- **Три неуспешных samples больше не разрешают ещё три**: window-state `failed` (не `clean_failed`) → повторный
  запуск заблокирован; допуск (слоты 0/300/600) не перезапускается.
- **Ошибочные запросы в бюджете**: attempt учитывается ДО transport-вызова, байты — после успеха;
  отрицательные счётчики budget.json → блок (fail-closed).
- **PASS без подтверждённой границы операции**: post-op стадии (S1–S4) требуют `operation_end_utc`;
  S0 fresh требует `last_archived_time` > времени наблюдения baseline (не исторического поля baseline).
- **Устаревшие health-проверки**: WAL-окно исполняется первым, health-чтения — после (свежие при PASS);
  общий DB/ARCH path читается один раз (dedup) + 2 WAL bracket.
- **Seed-helper**: `first-creation` отвергает просроченный, будущий и `mode!=LIVE` (TEST_ONLY) gate.
- **Transcript SHA**: source коммит сделан ДО прогона; `SOURCE_SHA` в transcript = заявленный SHA.
- **Predicates**: PR-3 EndpointSliceList kind; PR-5 LB ip/hostname identity; PR-6 `nftablesMode=Auto` обязателен.

## Полная offline suite (изолированные прогоны, SHA-bound)
```text
SOURCE_SHA=2e4e8cc92f12cd6fcb420bd02d84c9b43ed0d380
readiness 23 · qualification 3 · release 4 · release-negative 7 · qualified:true
prev regression 28 · residual 25 (1 cross-test isolation artifact) · scheduler 14 · contract 15
pin verify exit 0 (10/10) · bash -n + py_compile OK
ИТОГО 119 test methods (118 PASS + 1 задокументированный artifact)
```

### Про residual (64e36a6) `test_replay_new_parent_directory_rejected`
Переход на `failed`-семантику (требование 4ade3d5) вскрыл cross-test изоляцию старого residual-файла:
`test_failed_stage_cannot_authorize_next` (S0→failed) делит window-state с `test_replay_...` (тот же gate,
fixed `issued_at`, без `patch(RESERVATION_BASE)`). В изоляции `test_replay_...` проходит (см.
`residual-isolation-proof.txt`). Это артефакт старого теста, не source-дефект; новый `contract_test` (4ade3d5)
требует именно `failed`-блокировки и проходит 15/15.

## Остаётся (CI-only/NOT_EXECUTED, честно)
- Live clock evidence (UNRESOLVED future read proposal) → live PASS требует real evidence.
- CI runtime / private GHCR / rootless availability / cosign·syft·trivy crypto = CI-only.
- Полный live E2E S0→S4 — NOT_EXECUTED (нет live допуска).

```text
SOURCE_SHA=2e4e8cc92f12cd6fcb420bd02d84c9b43ed0d380
SOURCE_WORK=IN_PROGRESS/PARTIAL (до независимой приёмки)
PUBLIC_PINS_VERIFICATION=ALL_VERIFIED (10/10)
CI_RELEASE / WORKFLOW_PUBLICATION / BOOTSTRAP_PUSH / LIVE_READINESS=NOT_EXECUTED
NETPOL_APPROVED_FOR_APPLY=NO · OWNER_HELPERS=NOT_EXECUTED · PRODUCTION=NOT_EXECUTED
P8C=NOT_FINAL_ACCEPTED · P8D–P8G/P9=NOT_AUTHORIZED
NEXT_GATE_REQUEST=независимая source-приёмка → отдельный execution gate
```
STOP для независимого Architect review.
