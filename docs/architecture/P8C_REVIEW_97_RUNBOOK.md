# P8C #101 — перепубликация workflow и перепиновка (repin) после review #99

Роль: Implementation Engineer (Hermes). Источник: issue #101, review архитектора
[P8C_REVIEW_99.md](P8C_REVIEW_99.md) (commit `6c487ba0f662f8adec5be8593cab7cb0e152dda9`),
переработка PR #98 по review #95 ([P8C_REVIEW_95.md](P8C_REVIEW_95.md), commit `420ecc3822092b195d1d02271f16adb1b650ebc4`).

Этот документ — **инструкция**, а не разрешение на запуск. Он описывает, что сделано в PR
и какие шаги владелец выполняет ПОСЛЕ повторного review архитектора. Настоящее ревью не
разрешает dispatch, выпуск, смену секретов или lock, и **первый B остаётся BLOCKED**.

## 1. Что сделано в PR (ветка `engineer/101-cosign-verify-attestation-gate`)

### 1/A1 — наблюдение workflow-blob (из #97, принято)

`GITHUB_WORKFLOW_SHA` в Forgejo 15.0.11 **не существует**. В `preflight` и `release`
третий checkout на точном dispatch-коммите (`${{ github.sha }}`, `path: workflow`); шаг
«Observe executed workflow blob» через `forgejo_lock_gate.py workflow-blob` требует тип
`blob`. Blob подставлен в triple-check preflight, predicate, evidence и final gate.

### 1/cosign — проверка аттестаций без `-a` (review #99 item 1)

`cosign verify-attestation` v3.1.3 **не принимает** `-a/--annotations` (возвращает
`unknown shorthand flag: 'a'`); флаг принимают только `sign` и `verify`. Исправлено:

- `verify` (подпись образа) **сохраняет** `-a ref=<PINNED_SOURCE_SHA>` — проверка ref.
- Обе `verify-attestation` (slsaprovenance И spdxjson) передают только поддерживаемые
  флаги и проверяют подписанные subject/digest, тип и привязку к source:
  * subject/digest — позиционный `"${IMAGE}@${IMAGE_DIGEST}"`;
  * тип — `--type slsaprovenance` / `--type spdxjson`;
  * привязка к source — `--policy tools/portal/tools/cosign-slsa-policy.cue` (SLSA:
    `predicateType` + `sourceSHA` в `predicate.materials[0]`) и
    `--policy tools/portal/tools/cosign-spdx-policy.cue` (SPDX: `predicateType` +
    subject), ПЛЮС проверка SIGNED-вывода в gate:
    `check_verified_statement` (SLSA) и новая `check_verified_spdx_statement` (SPDX).
- CUE-политики проверены offline тем же движком, что использует cosign
  (`cuejson.Validate`): positive PASS, negative (неверный source material / неверный
  predicateType для каждого типа) REJECT (см. `evidence/`).
- Новый автономный тест `test_cosign_cli_flags.py` гоняет **фактический** cosign v3.1.3
  (скачивается и сверяется по SHA-256 `4629c757…`): `-a` отклоняется для обоих типов,
  поддерживаемые флаги принимаются, `verify`/`sign` принимают `-a`.

### 2/B — release перепроверяет gate и отклоняет placeholder identity (review #99 item 2)

- В `release` **до** build/push/sign добавлен шаг «Re-verify owner gate in release»:
  тот же `owner-gate` + та же тройная сверка (policy pin == owner document == observed
  blob) по снимку **данного** job (в preflight проверялся другой снимок). Смена gate
  между jobs (workflow_sha/source_sha) отклоняется до внешних записей.
- Шаг OIDC расширен: даже при `oidc_trust_confirmed=true` плейсхолдер
  `<FORGEJO_OIDC_IDENTITY_UNCONFIRMED>` **отклоняется** до push/sign (identity не
  угадывается). В gate: `identity_is_confirmed()` + reject в Stage 4 (плейсхолдер в
  binding ИЛИ в evidence — BLOCKED). Workflow-шаги `verify` передают
  `--identity "${{ env.WORKFLOW_IDENTITY }}"` и `--issuer "${{ env.OIDC_ISSUER }}"`.
- Автономные тесты: плейсхолдер-identity отклоняется при `oidc_trust_confirmed=true`;
  gate изменён между jobs (workflow_sha/source_sha) отклонён; positive — только с
  подтверждённой identity.

### 3/tools-pin — проверка точного tools pin (review #99 item 3)

- Новая команда `forgejo_lock_gate.py tools-pin-check --tools-dir tools` +
  `verify_tools_pin()`: сверяет, что **реально выбранный** tools checkout (по
  `PINNED_TOOLS_SHA`) реализует все gate-режимы, которые вызывает workflow
  (owner-gate/inventory/lock-image-check/digest/registry-fetch/predicate/workflow-blob/
  verify). Протухший tools pin (напр. `32a38ea` без `workflow-blob`) отклоняется
  fail-closed ДО побочных эффектов. Шаг добавлен в `test`, `preflight` и `release`.
- Автономный тест: complete gate ACCEPT, gate без `workflow-blob` REJECT, отсутствие
  файла REJECT.

### 4/tooling — устранена двойная `v` и проверены ассеты/checksum (review #99 item 3)

`ROOTLESSKIT_VERSION`/`SYFT_VERSION`/`TRIVY_VERSION` теперь **bare** (`2.3.1`/`1.55.0`/
`0.76.0`); URL строятся `v${…}` (как cosign). `buildkit` оставлен с `v` (имя ассета
включает `v`: `buildkit-v0.34.0…`). Имена ассетов и SHA-256 перепроверены по сети
(совпали с `pins.lock.json`): rootlesskit `caaf…`, syft `bb65…`, trivy `e24b…`, cosign
`4629…`, buildkit `1481…`.

## 2. Автономные тесты

Офлайн, синтетика, без CI/registry/secrets. Запуск: `bash portal/tools/run_offline_suite.sh`.

- `test_forgejo_lock_gate.py` (89), `test_forgejo_offline_integration.py` (37),
  `test_owner_gate_barrier.py` (37 — барьер/OIDC/blob/плейсхолдер-identity/SPDX/
  gate-между-jobs/tools-pin/структура), `test_cosign_cli_flags.py` (5 — фактический
  cosign CLI). Итого 168 тестов + синтаксис шаблона VERIFIED (4 job, 93 выражения).
- CUE-политики проверены offline тем же `cuejson.Validate` (см. `evidence/`).

## 3. Публикация и repin (владелец, ПОСЛЕ повторного review) — ИСПРАВЛЕННЫЙ ПОРЯДОК

Порядок разделяет **подготовку** и **публикацию**, чтобы обе правки YAML (tools pin и
identity/SAN) не меняли blob уже опубликованного workflow:

1. **Подготовка (этот PR)**: финальные tools (gate + тесты + CUE-политики + template),
   финальный плейсхолдер identity, финальный workflow YAML. Ничего не публикуется.
2. **Review точной версии**: архитектор принимает PR — принимает ТОЧНЫЙ SHA tools
   (commit с `workflow-blob` + `tools-pin-check` + CUE-политиками) и ТОЧНЫЙ текст
   workflow. Перепубликация и repin — только после этого review.
3. **Отдельное решение владельца** о публикации (не это ревью).
4. **Публикация**: workflow фиксируется в `.forgejo/workflows/p8c-portal-forgejo-release.yml`
   в дереве `main`; фиксируются **merge commit** и **новый blob**
   `git rev-parse <merge_commit>:.forgejo/workflows/p8c-portal-forgejo-release.yml`
   (объект — `blob`). Никаких правок YAML после этого шага.
5. **Repin POLICY_WORKFLOW_SHA** → новый blob (секрет репозитория). OWNER_GATE несёт
   `workflow_sha` = тот же новый blob.
6. **Repin PINNED_TOOLS_SHA** → точный SHA из п. 2 (commit с workflow-blob +
   tools-pin-check + CUE-политиками). Этот commit НЕ меняет blob workflow (tools —
   отдельный pin), поэтому порядок безопасен.
7. **Подтвердить барьер**: выделенный runner/label `otus-diplom-admission` без других
   подходящих runners; процедура закрытия/открытия выдачи из раздела 1.
8. **Подтвердить OIDC**: доверие CA к issuer (`https://git.aiopslab.online/api/actions`)
   и audience, точный SAN, привязка `sub` к одобренному workflow, trust roots; заменить
   `<FORGEJO_OIDC_IDENTITY_UNCONFIRMED>` подтверждённым значением (в YAML env и в
   `forgejo_lock_gate.py`).
9. Только после п. 5–8 — **отдельное** решение о первом B. Это ревью не разрешает
   dispatch, выпуск, смену секретов или lock.

## 4. Замечания для ревьюера

- Двойная `v` для rootlesskit/syft/trivy устранена, имена ассетов и checksum проверены
  по сети и совпали с `pins.lock.json` (было «требует решения» в review #95).
- SHA-256 cosign `v3.1.3` = `4629c757b7618056f8ddd7e2625ae9fdd94c0372a65049520bc7d9df9efc7f71`
  перепроверен по сети (совпал с pin; подтверждено в review #99).
- `PINNED_TOOLS_SHA` в исполняемом YAML всё ещё `32a38ea…` (протухший, без
  `workflow-blob`) — **намеренно не менялся** (запрет «не менять действующие pins»);
  `tools-pin-check` и шаг в workflow теперь отклоняют такой pin fail-closed, а repin —
  п. 6 выше.
