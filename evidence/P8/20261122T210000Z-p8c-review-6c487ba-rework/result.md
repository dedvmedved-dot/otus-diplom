# P8C #101 — review #99 rework: cosign verify-attestation, release gate, tools pin

Role: Implementation Engineer (Hermes). Task: issue #101 (Forgejo), review
`docs/architecture/P8C_REVIEW_99.md` (commit `6c487ba0f662f8adec5be8593cab7cb0e152dda9`).
Rework of PR #98 (branch `engineer/97-owner-gate-race-oidc`, SHA `29eb709`).

## Criteria → result

| #101 criterion | result |
|---|---|
| CLI v3.1.3 принимает обе команды | `verify-attestation` больше не передаёт `-a` (отклоняется v3.1.3); `verify`/`sign` сохраняют `-a ref=…`. Доказано фактическим CLI (`evidence/P8/20261122T210000Z-p8c-review-6c487ba-rework/cosign-cli-flags.txt`) |
| подписанные subject/type/source проверяются, независимые отрицательные фикстуры | subject/digest (позиционный digest), type (`--type`), source (`--policy` CUE + `check_verified_statement`/`check_verified_spdx_statement`). Отрицательные фикстуры для ОБОИХ типов: `TestSpdxAttestation` (5), плейсхолдер/gate/tools-pin в `test_owner_gate_barrier.py` |
| Release до записи отклоняет новый несовпадающий OWNER_GATE/blob и placeholder SAN даже при true | шаг «Re-verify owner gate in release» (до build/push) + `identity_is_confirmed` reject (плейсхолдер BLOCKED при `oidc_trust_confirmed=true`) + `[[ WORKFLOW_IDENTITY != placeholder ]]` до sign |
| Проверить tooling URL/checksum и предусмотреть проверку точного tools pin | checksum перепроверены по сети (`tooling-checksums.txt`); двойная `v` устранена (rootlesskit/syft/trivy bare); `tools-pin-check` + `verify_tools_pin()` (проверка реально выбранного tools) |
| исправить порядок публикации/repin и тестировать исполняемый YAML | runbook §3 переписан (подготовка → review → решение владельца → публикация → repin); синтаксис шаблона VERIFIED (4 job, 93 выражения), 168 тестов PASS |
| Представить новый SHA на review | см. финальный отчёт (SHA зафиксирован после commit) |

## Constraints honoured

- Workflow НЕ опубликован (только PR; `.forgejo/workflows/` изменён в ветке, не в main).
- Действующие pins/секреты/lock НЕ менялись: `PINNED_TOOLS_SHA=32a38ea…` (протухший)
  оставлен как есть — теперь отклоняется `tools-pin-check` до repin (runbook §3 п.6).
  `POLICY_WORKFLOW_SHA`/`OWNER_GATE`/`REGISTRY_*` (секреты) и `images.lock`/`versions.lock`/
  `pins.lock.json` не тронуты.
- B/C не запускались; registry/sign/attest не выполнялись (офлайн-синтетика).

## Offline evidence

- `tooling-checksums.txt` — SHA-256 всех инструментов совпал с pin (по сети).
- `cosign-cli-flags.txt` — фактический cosign v3.1.3: `-a` отклонён для verify-attestation,
  поддерживаемые флаги приняты, `verify`/`sign` принимают `-a`.
- `cue-policy-validation.txt` — CUE-политики проверены тем же движком (`cuejson.Validate`,
  cuelang.org/go v0.9.2), что использует cosign: 5/5 случаев совпали с ожиданием
  (positive PASS, negative REJECT для обоих типов).

## NEW SHA (to be recorded post-commit)

`EXTERNAL_POST_COMMIT_VALUE — VERIFY BY CONNECTOR`
