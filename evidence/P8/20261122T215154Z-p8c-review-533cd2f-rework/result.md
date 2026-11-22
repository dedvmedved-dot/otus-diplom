# P8C #107 — доработка #102 по review #106: пара CUE до push + границы SPDX-проверок

Роль: Implementation Engineer (Hermes). Задача: issue #107 (Forgejo), review
`docs/architecture/P8C_REVIEW_106.md` (commit `533cd2f7c63a5d192940a0476e419d5dadb27786`).
Проверяемый SHA (до rework): `087a68100922338e72e76ce0b42d5b00fcc22cd5` (PR #102, ветка
`engineer/101-cosign-verify-attestation-gate`). Rework = новые коммиты в той же ветке.

## Критерии review #106 → результат

| #106 item | результат |
|---|---|
| §3 порядок публикации | Принят без изменений (байты финализируются до review, после публикации — только сверка blob). Правок нет. |
| SPDX: gate принят в заявленном объёме, описание CUE исправить | `cosign-spdx-policy.cue` и runbook §1/§2/§4 согласованы: CUE-слой (`cuejson.Validate`, `cue.Final()`) отклоняет противоречия на ПРИСУТСТВУЮЩИХ полях (чужой `predicateType`, неверный `spdxVersion`/`SPDXID`, пустой `packages`); отсутствие/пустоту predicate/`name`/`documentNamespace`/`packages` отклоняет GATE (`check_verified_spdx_statement`) — итоговый отказ gate НЕ ослаблен. |
| Восемь исполняемых примеров CUE не включают отсутствие/пустоту predicate | `cue-validation/main.go` расширен: добавлены отсутствующий predicate, пустой predicate `{}`, отсутствующие `name`/`documentNamespace`/`packages` как ИСПОЛНЯЕМЫЕ CUE-кейсы (все `want=true` — CUE-слой их принимает). Итог: 13 CUE-кейсов, все совпали с ожиданием. Нижний печатный блок про gate заменён на ссылку на матрицу исходов каждого слоя. |
| Показать результаты CUE и gate отдельно для отсутствующего/пустого predicate | `cue-policy-validation.txt` — матрица «case → CUE-слой → GATE-слой» с фактическими исходами: для отсутствующего/пустого predicate CUE=ACCEPT, GATE=REJECT (разделение слоёв по дизайну). Сырые прогоны: `cue-layer.txt` (13 кейсов) и `gate-layer.txt` (10 кейсов). |
| Tools pin: `verify_tools_pin()` не отличает политики друг от друга | `verify_tools_pin()` теперь сверяет КАЖДУЮ политику по точным байтам с заранее проверенным эталонным SHA-256 (`CUE_POLICY_REFERENCE_SHA256`). Контроль архитектора воспроизведён: SPDX-путь с точной копией SLSA-политики → `tools_pin: false` (REJECT, exit 1); корректная пара → `tools_pin: true` (exit 0). |
| Регрессия на перепутанные файлы и повреждённый CUE, сохранить тест на отсутствующий файл | Добавлены `test_gate_with_swapped_cue_policies_rejected` и `test_gate_with_corrupted_cue_policy_rejected`; тесты на отсутствующий файл и пустую политику сохранены. |
| Не менять рабочие pins/секреты/lock, не публиковать workflow, не запускать B/C | `PINNED_TOOLS_SHA=32a38ea…` (протухший), `WORKFLOW_IDENTITY` (плейсхолдер), `POLICY_WORKFLOW_SHA`/`OWNER_GATE`/`REGISTRY_*` (секреты), `images.lock`/`versions.lock`/`pins.lock.json` НЕ тронуты. Workflow не публиковался (изменён только в ветке, не в main). B/C, registry, sign/attest не запускались (офлайн-синтетика). |

## Изменённые файлы

- `portal/tools/forgejo_lock_gate.py` — `CUE_POLICY_REFERENCE_SHA256` (эталонные SHA-256
  двух политик) + проверка каждой политики по точным байтам в `verify_tools_pin()`;
  комментарий/сообщение обновлены под review #106 item 3.
- `portal/tools/cosign-spdx-policy.cue` — комментарий исправлен: CUE-слой отклоняет
  противоречия на присутствующих полях; отсутствие/пустота — ответственность gate.
- `portal/tools/test_owner_gate_barrier.py` — +2 регрессии tools-pin (перепутанные
  политики, повреждённый CUE). Итого 48 тестов.
- `docs/architecture/P8C_REVIEW_97_RUNBOOK.md` — §1/§2/§3/§4 согласованы с разделением
  слоёв SPDX и новой проверкой пары CUE (SHA-256) до push; заголовок/источник — #107.

## Офлайн-доказательства

- `offline-suite.txt` — полный прогон `run_offline_suite.sh`: **SUITE RESULT: PASS**
  (системный Python, изолированные authority-окна), `SOURCE_SHA=1e3fdc5…`.
- `workflow-syntax.txt` — синтаксис шаблона: **SYNTAX = VERIFIED** (4 job, 93 выражения).
- `cue-policy-validation.txt` — матрица исходов каждого слоя SPDX (CUE vs GATE);
  `cue-layer.txt` — 13 CUE-кейсов (cuelang.org/go v0.9.2, движок cosign), все совпали;
  `gate-layer.txt` — 10 SPDX-кейсов через `check_verified_spdx_statement`, все совпали.
- `cue-validation/` — обновлённый Go-валидатор (main.go + политики + go.mod/go.sum).
- `spdx_gate_matrix.py` — воспроизводимый прогон GATE-слоя тех же кейсов.
- Тесты: `test_forgejo_lock_gate.py` (89) + `test_forgejo_offline_integration.py` (37) +
  `test_owner_gate_barrier.py` (48) + `test_cosign_cli_flags.py` (5) = **179** тестов PASS.

## NEW SHA (для повторного review архитектора)

`1e3fdc537d6c6802486cf621d28dc49283a34fa4`

Примечание: независимая сверка SHA source/package — за GitHub Connector (не
заявлена здесь как выполненная).
