# P8C #107 — доработка #102 по review #106: границы SPDX-проверок + пара CUE до push

Роль: Implementation Engineer (Hermes). Источник: issue #107, review архитектора
[P8C_REVIEW_106.md](P8C_REVIEW_106.md) (commit `533cd2f7c63a5d192940a0476e419d5dadb27786`),
доработка PR #102 (SHA `087a68100922338e72e76ce0b42d5b00fcc22cd5`), который ранее
перерабатывался по review #103 (commit `585355f67ee6d975e9f50e970583020d1b978573`).

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
    `--policy tools/portal/tools/cosign-spdx-policy.cue` (SPDX), ПЛЮС проверка
    SIGNED-вывода в gate: `check_verified_statement` (SLSA) и
    `check_verified_spdx_statement` (SPDX).
- **review #103 item 2 — SPDX проверяется по содержимому, а не по оболочке.** Привязки
  разделены явно: **SBOM→digest** (SPDX: подписанный subject = image@digest + документ
  той самой image) и **digest→source** (SLSA: тот же digest связан с pinned source SHA
  через `predicate.materials[]`). Сама строка `predicateType` не доказывает ни того, ни
  другого. Требование «НЕПУСТОЙ SPDX-документ ожидаемой формы» (`spdxVersion` SPDX-2.x,
  `SPDXID == "SPDXRef-DOCUMENT"`, непустые `name` / `documentNamespace`, НЕПУСТОЙ
  `packages`) закрывают ДВА слоя с разными зонами ответственности (review #106 item 2):
  * **CUE-политика** (`cosign verify-attestation --policy`) отклоняет противоречия на
    ПРИСУТСТВУЮЩИХ полях — чужой `predicateType`, неверный `spdxVersion`/`SPDXID`,
    пустой `packages` (это проверка формы, НЕ полный валидатор SPDX);
  * **GATE** (`check_verified_spdx_statement`) дополнительно отклоняет ОТСУТСТВИЕ/ПУСТОТУ
    `predicate`/`name`/`documentNamespace`/`packages` над SIGNED-выводом — т.к.
    `cuejson.Validate` использует `cue.Final()` и НЕ требует отсутствующих полей.
  Итоговый отказ gate НЕ ослаблен: отсутствующий/пустой/чужой документ всегда отклоняется
  gate. Положительный фикстур — форма Syft/cosign; матрица исходов каждого слоя — в
  `evidence/` (`cue-policy-validation.txt`).
- CUE-политики проверены offline тем же движком, что использует cosign
  (`cuejson.Validate`, cuelang.org/go v0.9.2): positive PASS, negative на присутствующих
  полях (неверный source material / неверный predicateType для каждого типа) REJECT;
  отсутствие/пустота predicate не отклоняется CUE-слоем и показана в матрице отдельно от
  исхода gate (см. `evidence/`).
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

### 3/tools-pin — проверка точного tools pin (review #99 item 3 + review #103 item 3 + review #106 item 3)

- Команда `forgejo_lock_gate.py tools-pin-check --tools-dir tools` +
  `verify_tools_pin()`: сверяет, что **реально выбранный** tools checkout (по
  `PINNED_TOOLS_SHA`) реализует все gate-режимы, которые вызывает workflow
  (owner-gate/inventory/lock-image-check/digest/registry-fetch/predicate/workflow-blob/
  verify) И несёт/загружает обе CUE-политики, которые workflow открывает через
  `cosign verify-attestation --policy` (`cosign-slsa-policy.cue` +
  `cosign-spdx-policy.cue`). Протухший tools pin (напр. `32a38ea` без `workflow-blob`)
  или pin без одной из политик отклоняется fail-closed ДО побочных эффектов (до
  build/push/sign, когда политики ещё не открыты). Шаг добавлен в `test`, `preflight`
  и `release`.
- **review #106 item 3 — каждая политика проверяется на СВОЮ роль до push.** Наличие +
  подстрока `predicateType:` не различают политики: контроль архитектора показал, что
  точная копия SLSA-политики на пути SPDX даёт `tools_pin: true`. Теперь каждая
  политика сверяется по точным байтам с заранее проверенным эталонным SHA-256
  (`CUE_POLICY_REFERENCE_SHA256` в gate): перепутанные файлы или повреждённый CUE
  изменяют дайджест и отклоняются fail-closed ДО первой внешней записи. Легитимное
  изменение политики (напр. repin `sourceSHA`) обязано обновить эталонные SHA-256 в том
  же reviewed-коммите (§3 публикация).
- Автономные тесты: complete gate ACCEPT; gate без `workflow-blob` REJECT; gate со
  всеми командами, но БЕЗ одной из CUE-политик REJECT; пустая политика REJECT;
  отсутствие файла REJECT; **перепутанные политики REJECT; повреждённый CUE REJECT**
  (review #106).

### 4/tooling — устранена двойная `v` и проверены ассеты/checksum (review #99 item 3)

`ROOTLESSKIT_VERSION`/`SYFT_VERSION`/`TRIVY_VERSION` теперь **bare** (`2.3.1`/`1.55.0`/
`0.76.0`); URL строятся `v${…}` (как cosign). `buildkit` оставлен с `v` (имя ассета
включает `v`: `buildkit-v0.34.0…`). Имена ассетов и SHA-256 перепроверены по сети
(совпали с `pins.lock.json`): rootlesskit `caaf…`, syft `bb65…`, trivy `e24b…`, cosign
`4629…`, buildkit `1481…`.

## 2. Автономные тесты

Офлайн, синтетика, без CI/registry/secrets. Запуск: `bash portal/tools/run_offline_suite.sh`.

- `test_forgejo_lock_gate.py` (89), `test_forgejo_offline_integration.py` (37),
  `test_owner_gate_barrier.py` (48 — барьер/OIDC/blob/плейсхолдер-identity/SPDX
  (predicate-содержимое + отрицательные фикстуры)/gate-между-jobs/tools-pin
  (CUE-политики, включая перепутанные и повреждённые)/структура),
  `test_cosign_cli_flags.py` (5 — фактический cosign CLI). Итого 179 тестов +
  синтаксис шаблона VERIFIED (4 job, 93 выражения).
- CUE-политики проверены offline тем же `cuejson.Validate` (cuelang.org/go v0.9.2),
  что использует cosign: positive (SLSA/SPDX) PASS; negative на ПРИСУТСТВУЮЩИХ полях
  (неверный source material / неверный predicateType / чужой `spdxVersion`/`SPDXID` /
  пустой `packages`) REJECT. Отсутствие/пустота predicate/`name`/`documentNamespace`/
  `packages` CUE-слоем НЕ отклоняется (`cue.Final()` не требует отсутствующих полей) —
  их отклоняет GATE; матрица исходов каждого слоя — в `evidence/`.

## 3. Публикация и repin (владелец, ПОСЛЕ повторного review) — ИСПРАВЛЕННЫЙ ПОРЯДОК

**Все байты YAML, SAN (identity) и tools SHA финализируются ДО review и публикации.**
После публикации workflow никакая правка YAML недопустима — допустима только **сверка**
(сравнение) уже опубликованного blob с просмотренным и сверка tools pin.

1. **Подтвердить identity/SAN (владелец, ВНЕ этого PR)**: точное значение сертификатной
   identity (Forgejo id-token `sub` / SAN), привязка к одобренному workflow, CA-доверие
   к issuer (`https://git.aiopslab.online/api/actions`) и audience, trust roots. **Пока
   SAN неизвестен — подготовка остаётся НЕЗАВЕРШЁННОЙ**, значение НЕ угадывается
   (`<FORGEJO_OIDC_IDENTITY_UNCONFIRMED>` остаётся плейсхолдером, release BLOCKED).
2. **Отдельный commit tools с подтверждённой identity**: в `forgejo_lock_gate.py`
   подставить подтверждённый `WORKFLOW_IDENTITY` (плейсхолдер заменён точным значением
   из п. 1); CUE-политики уже несут фиксированный `sourceSHA`. Этот commit финализирует
   **tools SHA** (commit с `workflow-blob` + `tools-pin-check` + обеими CUE-политиками).
   После этого шага identity в gate больше не меняется (иначе поменялся бы tools commit).
3. **Подставить tools SHA и identity в кандидат YAML**: `PINNED_TOOLS_SHA` = точный tools
   SHA из п. 2, `WORKFLOW_IDENTITY` = точная identity из п. 1. Теперь **байты кандидата
   YAML финализированы** (tools pin и identity больше не меняются до публикации).
4. **Проверить точные байты и checkout** (до build/push): `git -C tools rev-parse HEAD ==
   PINNED_TOOLS_SHA`; обе CUE-политики присутствуют и загружаются из того же checkout
   (`tools-pin-check` до внешних записей); workflow-синтаксис VERIFIED.
5. **Review точной версии**: архитектор принимает PR — принимает ТОЧНЫЙ tools SHA,
   ТОЧНЫЙ текст workflow и подтверждённую identity (все байты финализированы в п. 1–3).
6. **Отдельное решение владельца** о публикации (не это ревью).
7. **Публикация БЕЗ правок**: workflow фиксируется в
   `.forgejo/workflows/p8c-portal-forgejo-release.yml` в дереве `main` БЕЗ каких-либо
   правок; фиксируются **merge commit** и **новый blob**
   `git rev-parse <merge_commit>:.forgejo/workflows/p8c-portal-forgejo-release.yml`
   (объект — `blob`). После этого шага правки YAML запрещены.
8. **Сверка blob с просмотренным**: сравнить опубликованный blob с blob, который видел
   архитектор на review (п. 5). Это — сверка (сравнение), НЕ редактирование. Допустима
   также сверка tools pin (реально выбранный checkout == `PINNED_TOOLS_SHA`).
9. **Выставить policy/OWNER_GATE** (только после п. 7–8): `POLICY_WORKFLOW_SHA` → новый
   blob (секрет репозитория); OWNER_GATE несёт `workflow_sha` = тот же новый blob. Это
   отдельные out-of-band секреты, а НЕ байты YAML.
10. Подтвердить барьер (выделенный runner/label `otus-diplom-admission` без других
    подходящих runners; процедура закрытия/открытия выдачи из раздела 1). Только после
    п. 9–10 — **отдельное** решение о первом B. Это ревью не разрешает dispatch, выпуск,
    смену секретов или lock.

Ключевое отличие от прошлой редакции: `PINNED_TOOLS_SHA` и `WORKFLOW_IDENTITY` больше
не правятся ПОСЛЕ публикации (п. 6/8 старой редакции) — они финализируются в п. 1–3 ДО
review и публикации. Шаг 8 «сверка blob» — это сравнение, а не запись в YAML, поэтому
он не противоречит запрету на правки после публикации.

## 4. Замечания для ревьюера

- Двойная `v` для rootlesskit/syft/trivy устранена, имена ассетов и checksum проверены
  по сети и совпали с `pins.lock.json` (было «требует решения» в review #95).
- SHA-256 cosign `v3.1.3` = `4629c757b7618056f8ddd7e2625ae9fdd94c0372a65049520bc7d9df9efc7f71`
  перепроверен по сети (совпал с pin; подтверждено в review #99).
- `PINNED_TOOLS_SHA` в исполняемом YAML всё ещё `32a38ea…` (протухший, без
  `workflow-blob`) и `WORKFLOW_IDENTITY` — плейсхолдер — **намеренно НЕ менялись**
  (запрет «не менять действующие pins/секреты» + «не угадывать SAN»); `tools-pin-check`
  теперь отклоняет такой pin fail-closed, а финализация точного tools SHA + identity —
  §3 п. 1–3 (ДО review/публикации).
- **review #103**: (1) порядок публикации исправлен — YAML/SAN/tools SHA финализируются
  до review/публикации, после публикации только сверка blob (§3); (2) SPDX проверяется
  по содержимому (непустой документ ожидаемой формы) с явным разделением SBOM→digest и
  digest→source, положительным Syft-фикстуром и отрицательными отсутствующий/пустой/чужой
  (границы слоёв уточнены в review #106, см. ниже); (3) `tools-pin-check` требует и
  загружает обе CUE-политики из того же checkout до внешних записей (отрицательный тест —
  gate со всеми командами, но без одной политики).
- **review #106** (эта доработка): (1) §3 порядок публикации — принят без изменений.
  (2) SPDX — уточнены границы проверок: CUE-политика отклоняет противоречия на
  присутствующих полях (форма), а отсутствие/пустоту predicate/`name`/`documentNamespace`/
  `packages` отклоняет GATE (`check_verified_spdx_statement`, т.к. `cuejson.Validate` с
  `cue.Final()` не требует отсутствующих полей); комментарий `cosign-spdx-policy.cue` и
  runbook согласованы с этим разделением, итоговый отказ gate НЕ ослаблен; в матрицу
  `evidence/` добавлены отсутствующий/пустой predicate с фактическим исходом каждого слоя
  (CUE и gate отдельно). (3) `verify_tools_pin()` теперь сверяет каждую политику по
  точным байтам с эталонным SHA-256 (`CUE_POLICY_REFERENCE_SHA256`) — перепутанные
  файлы и повреждённый CUE отклоняются до первой внешней записи; добавлены регрессии на
  перепутанные политики и повреждённый CUE (тест на отсутствующий файл сохранён).
  Рабочие pins/секреты/lock не менялись, workflow не публиковался, B/C не запускались.
