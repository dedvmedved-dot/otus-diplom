# P8C #105 — доработка #102 по review #103: SPDX predicate, CUE tools pin, порядок публикации

Роль: Implementation Engineer (Hermes). Задача: issue #105 (Forgejo), review
`docs/architecture/P8C_REVIEW_103.md` (commit `585355f67ee6d975e9f50e970583020d1b978573`).
Проверяемый SHA: `237c3e2ea603998483707f22f5856df6679040dd` (PR #102, ветка
`engineer/101-cosign-verify-attestation-gate`). Rework = новые коммиты в той же ветке.

## Критерии review #103 → результат

| #103 item | результат |
|---|---|
| §3 порядок фиксации: YAML/SAN/tools SHA финализируются ДО review/публикации | `docs/architecture/P8C_REVIEW_97_RUNBOOK.md` §3 переписан: identity/SAN (владелец) → отдельный commit tools с подтверждённой identity → подставить tools SHA + identity в кандидат YAML → проверка байт/checkout → review → решение владельца → публикация БЕЗ правок → сверка blob → policy/OWNER_GATE. После публикации — только сверка, не редактирование. Пока SAN неизвестен — подготовка незавершена (не угадывается). |
| SPDX: требовать подписанный непустой документ ожидаемой формы | `cosign-spdx-policy.cue` + `check_verified_spdx_statement()` теперь требуют `spdxVersion` (SPDX-2.x), `SPDXID==SPDXRef-DOCUMENT`, непустые `name`/`documentNamespace`, НЕПУСТОЙ `packages`. Положительный Syft/cosign фикстур; отрицательные отсутствующий/пустой/чужой документ. |
| явно отделить SBOM→digest от digest→source | SBOM→digest = SPDX (subject image@digest + документ); digest→source = SLSA (`predicate.materials[]`). `predicateType` сам по себе не доказывает ни того, ни другого (комментарии в `check_verified_spdx_statement` + Stage 4). |
| точный tools pin: проверять обе CUE-политики из того же checkout до внешних записей | `verify_tools_pin()` теперь требует ОБЕ политики (`cosign-slsa-policy.cue`, `cosign-spdx-policy.cue`) присутствующими, читаемыми, непустыми, с `predicateType:` из того же checkout. Отрицательные тесты: gate со всеми командами, но БЕЗ одной политики (REJECT); пустая политика (REJECT). |
| не публиковать workflow, не менять pins/секреты/lock, не запускать B/C | `.forgejo/workflows/` изменён только в ветке (не в main). `PINNED_TOOLS_SHA=32a38ea…`, `WORKFLOW_IDENTITY` (плейсхолдер), `POLICY_WORKFLOW_SHA`/`OWNER_GATE`/`REGISTRY_*` (секреты), `images.lock`/`versions.lock`/`pins.lock.json` НЕ тронуты. B/C не запускались; registry/sign/attest не выполнялись (офлайн-синтетика). |
| представить новый SHA для review | см. финальный отчёт (SHA зафиксирован после commit). |

## Изменённые файлы

- `docs/architecture/P8C_REVIEW_97_RUNBOOK.md` — §3 порядок публикации/repin исправлен,
  §1 (SPDX по содержимому, CUE tools pin), §2 (177 тестов), §4 (review #103).
- `portal/tools/cosign-spdx-policy.cue` — требуемый непустой SPDX-документ ожидаемой
  формы (predicateType + spdxVersion/SPDXID/name/documentNamespace/packages).
- `portal/tools/forgejo_lock_gate.py` — `SPDX_VERSION_RE`; `check_verified_spdx_statement`
  читает `predicate` (непустой документ, разделение SBOM→digest / digest→source);
  `REQUIRED_CUE_POLICIES` + `verify_tools_pin` проверяет обе CUE-политики из checkout;
  комментарий Stage 4 (разделение привязок).
- `portal/tools/test_owner_gate_barrier.py` — реалистичный Syft SPDX фикстур +
  6 отрицательных SPDX-тестов (отсутствующий/пустой/чужой/пустой packages/без
  namespace); 3 теста tools-pin (без одной политики ×2, пустая политика).
- `portal/tools/test_forgejo_offline_integration.py` — реалистичный Syft SPDX фикстур.

## Офлайн-доказательства

- `offline-suite.txt` — полный прогон `run_offline_suite.sh`: **SUITE RESULT: PASS**
  (системный Python, изолированные authority-окна).
- `workflow-syntax.txt` — синтаксис шаблона: **SYNTAX = VERIFIED** (4 job, 93 выражения).
- `cue-policy-validation.txt` + `cue-validation/` — CUE-политики проверены тем же
  движком, что использует cosign (`cuejson.Validate`, cuelang.org/go v0.9.2):
  SLSA positive/negative PASS; SPDX positive (Syft) PASS, foreign (неверный
  predicateType/spdxVersion/SPDXID/пустой packages) REJECT. Разделение слоёв: отсутствие/
  пустота predicate/name/namespace/пакетов отклоняет GATE (`check_verified_spdx_statement`,
  `TestSpdxAttestation`), т.к. `cuejson.Validate` вызывает `cue.Final()` (не требует
  присутствия полей, а cosign-политика — только противоречия на присутствующих).
- Тесты: `test_forgejo_lock_gate.py` (89) + `test_forgejo_offline_integration.py` (37) +
  `test_owner_gate_barrier.py` (46) + `test_cosign_cli_flags.py` (5) = **177** тестов PASS.

## NEW SHA (to be recorded post-commit)

`EXTERNAL_POST_COMMIT_VALUE — VERIFY BY CONNECTOR`
