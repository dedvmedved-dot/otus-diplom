# P8C #93 — привязка OWNER_GATE к выданному run_id до preflight (первый B)

Роль: Implementation Engineer (Hermes). Источник задания: issue #93.
База протокола: `docs/architecture/P8C_ADMISSION_91.md` (commit `c1a872b58d596e01cb5833b5ca2920fb6a21d962`).

## Вердикт (кратко)

1. **run_id-привязка OWNER_GATE до preflight — ВОЗМОЖНА детерминированно** (без угадывания ID,
   без гонки с job, без rerun). Механизм подтверждён версионными исходниками Forgejo 15.0.11:
   dispatch c `return_run_info=true` синхронно возвращает серверный `id` (это и есть
   `github.run_id`), а секреты фиксируются в момент **выдачи task ранеру** (`PickTask`), а не в
   момент dispatch. Поскольку `preflight` ждёт `needs: test`, окно владельца детерминировано.
   Точная последовательность — раздел 5.

2. **Допуск B в текущем виде — BLOCKED** двумя независимыми дефектами, ни один не связан с
   run_id-привязкой:
   - **GITHUB_WORKFLOW_SHA отсутствует** в рантайм-контексте Forgejo 15.0.11 (не blob, не commit —
     переменной нет, runner оставляет её unset). Triple-check preflight
     (`--observed-workflow-sha "$GITHUB_WORKFLOW_SHA"`) под `set -euo pipefail` упадёт на расширении
     неопределённой переменной («unbound variable»), а если бы передалась пустая строка — gate
     отверг бы её fail-closed `owner gate: observed workflow SHA (runtime context) missing`.
   - **OIDC к release job НЕ применим** в текущем виде: не выставлен `enable-openid-connect: true`
     (в Forgejo именно он включает id-token, а не `permissions.id-token: write`), и формат
     `sub`/identity не совпадает с `WORKFLOW_IDENTITY` в workflow.
   Оба дефекта требуют правки опубликованного workflow (решение архитектора). Предложения — раздел 7.

Ограничения соблюдены: B/C не запускались, секреты не читались (списки secrets/runners — HTTP 403,
это зафиксировано как факт), политика/lock не менялись, workflow не редактировался.

## Версии и источник доказательств

| Объект | Версия / пин | Источник |
|---|---|---|
| Forgejo server | `15.0.11+gitea-1.22.0` | `GET /api/v1/version` (живой инстанс), tag `v15.0.11` = commit `753f7edc775a97e66cd13d410404d5edc99b6b04` |
| forgejo-runner | фактическая версия НЕ читается (список runners: HTTP 403, owner-only) | анализ по последнему релизу `v13.2.2` = commit `0e61343d1cb98d2a381d0d18f34aea408e66e4d2` |
| Workflow (объект анализа) | `.forgejo/workflows/p8c-portal-forgejo-release.yml` blob `1805c93d3515c9262c45b99302fa1ef20581daaa` (main `e06a065`) | repo |

Все утверждения ниже — из версионных исходников (file + line). Вывод про отсутствие
`GITHUB_WORKFLOW_SHA` — свойство **сервера** (в его github-контексте нет поля `workflow_sha`),
поэтому он не зависит от фактической версии runner (runner лишь пробрасывает контекст сервера).

## 1. Семантика GITHUB_WORKFLOW_SHA → ОТСУТСТВУЕТ

Сервер 15.0.11 строит github-контекст в `services/actions/context.go`
(`generateGiteaContextForRun`, строки 45–73). В структуре `model.GithubContext` есть
`Workflow` и `WorkflowRef`, но **нет поля `WorkflowSha`**:

- `context.go:70` `Workflow: run.WorkflowID` (имя/путь файла workflow),
- `context.go:71` `WorkflowRef: workflowRef` = `<owner>/<repo>/<dir>/<file>@<ref>`.

Серверный `githubContextToMap` (строки 127–140) сериализует только эти поля → ключа
`workflow_sha` в контексте нет.

Ранер (forgejo-runner v13.2.2) независимо подтверждает то же:

- `act/model/github_context.go` — структура `GithubContext` содержит `WorkflowRef` и **не содержит**
  `WorkflowSha`;
- `internal/app/run/runner.go:276–294` — `preset` собирается из `taskContext[...]`, поля
  `workflow_sha` нет;
- `internal/app/run/runner_test.go:1373–1374` (интеграционный тест «GitHub Actions environment
  variables») явно фиксирует поведение:

```
echo GITHUB_WORKFLOW_SHA="$GITHUB_WORKFLOW_SHA"
[[ -z ${GITHUB_WORKFLOW_SHA+x} ]] || exit 1  # Currently unsupported.
```

`${GITHUB_WORKFLOW_SHA+x}` пусто ⇒ переменная **не установлена** («Currently unsupported»).

Вывод: `GITHUB_WORKFLOW_SHA` **отсутствует** (не blob, не commit). Утверждение владельца в #91
«runtime `GITHUB_WORKFLOW_SHA` == blob `1805c93d…`» не выполняется — в рантайме этой переменной нет.

## 2. Семантика github.sha (GITHUB_SHA) → COMMIT SHA (не blob)

`services/actions/context.go:28` `sha := run.CommitSHA`; `context.go:69` `Sha: sha`.
`run.CommitSHA` (`models/actions/run.go:58`) — commit, вызвавший run; для `workflow_dispatch` на
`refs/heads/main` это HEAD main на момент dispatch.

Ранер-тест `runner_test.go:1359–1360`: `GITHUB_SHA == 5d64b71392b1e00a3ad893db02d381d58262c2d6`
(40 hex = commit SHA, не blob).

## 3. github.run_id / run_number / run_attempt

`services/actions/context.go:120–121` (при `job != nil`):

```
gitContext["run_id"]      = fmt.Sprint(job.RunID)    // ActionRun.ID (глобальный DB id)
gitContext["run_attempt"] = fmt.Sprint(job.Attempt)  // попытка job, начинается с 1
```

- `github.run_id` = `ActionRun.ID` (первичный ключ, `models/actions/run.go:45`), строка.
- `github.run_number` = `run.Index` (`context.go:66` `RunNumber: fmt.Sprint(run.Index)`) — счётчик
  run'ов репозитория (`models/actions/run.go:52` «a unique number for each run of a repository»),
  именно он в URL UI (`/actions/runs/<Index>`).
- `github.run_attempt` = `job.Attempt` (`models/actions/run_job.go:33`), первый run = `1`.

Ранер-тест подтверждает различие: `GITHUB_RUN_ID=150`, `GITHUB_RUN_NUMBER=129`,
`GITHUB_RUN_ATTEMPT=3` (`runner_test.go:1351–1356`), и `forgejo.run_id=150`, `forgejo.run_number=129`
(`runner_test.go:1265–1268`).

Важно для владельца: **`github.run_id` — это `id` (DB id) из API, а НЕ номер из URL/UI.**
Номер из URL — это `run_number` (`index_in_repo`/`run.Index`). Брать его как `run_id` нельзя.

## 4. Момент фиксации OWNER_GATE (секретов)

Секреты **не** фиксируются в момент dispatch. Они читаются в момент выдачи task ранеру:

- `routers/api/actions/runner/runner.go:188` (`FetchTask`) → `services/actions/task.go:56`
  `secrets, err := getSecretsOfTask(ctx, t)`; `task.go:80` `Secrets: secrets`.
- `services/actions/secret.go:55` `secret_model.FetchActionSecrets(ctx, ...)` читает **текущие**
  значения секретов из БД на каждый `PickTask`.

Порядок job: `preflight.needs = [test]`, `release.needs = [preflight]`. Job с незакрытыми `needs`
остаётся `Waiting` и не превращается в task, пока нужды не выполнены
(`services/actions/job_emitter.go:173–228`, «The `needs` of this job are done»). Следовательно
task preflight создаётся и берётся ранером **после** завершения `test`.

Итог: значение OWNER_GATE, увиденное preflight, — это значение на момент выдачи task preflight,
т.е. **после** окна `test` (десятки минут: `go test`, `-race`, интеграционные тесты, npm ci).
`test` OWNER_GATE не использует.

## 5. Детерминированная последовательность владельца (один run)

Без угадывания ID, без гонки, без rerun. Идентификаторы — только из ответов API.

1. (Разово, уже сделано) Проверить, что pins согласованы: `source_sha = 4c09d6b4…`,
   `tools_sha = 32a38ea1…`, `workflow_sha = POLICY_WORKFLOW_SHA` (= blob `1805c93d…`), runner
   online + label `otus-diplom`, доступ к пакету.

2. Dispatch **через API с `return_run_info=true`** (UI его не отдаёт):
   ```
   POST /api/v1/repos/aiopslab/otus-diplom/actions/workflows/p8c-portal-forgejo-release.yml/dispatches
   Authorization: token <owner>
   {"ref":"refs/heads/main",
    "inputs":{"apply_lock":"false","reviewed_digest":""},
    "return_run_info":true}
   ```
   Ответ `201` (см. `routers/api/v1/repo/action.go:859–869`, `modules/structs/workflow.go:22–25`):
   ```json
   {"id": <run_id>, "run_number": <n>, "jobs": ["test","preflight","release"]}
   ```
   `id` — это и есть `github.run_id` (серверный, не угаданный). `run_number` — для сверки с UI.

3. Построить OWNER_GATE с **`run_id` = строка из `id`** шага 2, `attempt=1`, `run_attempt=1`,
   `source_sha`/`tools_sha`/`workflow_sha` из шага 1, `repository`/`ref`/`package` по политике,
   `issued_at_utc` = сейчас, `expiry_hours` ∈ 1–24. Обновить секрет:
   ```
   PUT /api/v1/repos/aiopslab/otus-diplom/actions/secrets/OWNER_GATE
   {"data":"<json документа OWNER_GATE>"}
   ```

4. Дождаться завершения `test` (бездействие). `preflight` заберёт OWNER_GATE уже с корректным
   `run_id` на момент выдачи task (раздел 4). Rerun не требуется; `attempt` остаётся 1.

Гонки нет: `test` не читает OWNER_GATE; task `preflight` появляется только после `test`, а секрет
читается при выдаче этого task. Единственное требование к владельцу — выполнить шаг 3 до
завершения `test` (окно в десятки минут).

## 6. OIDC к release job → НЕ ПРИМЕНИМ (в текущем виде)

Forgejo выдаёт id-token только при `enable-openid-connect: true` (workflow- или job-уровень):

- `services/actions/task.go:162–187`: `enableOpenIDConnect, err := t.Job.EnableOpenIDConnect()`;
  только при `true` в контекст кладутся `forgejo_actions_id_token_request_token` и
  `forgejo_actions_id_token_request_url`.
- `services/actions/auth.go:92–101`: только при `true` к токену добавляется scope
  `generate_id_token:<runID>:<jobID>` и OIDC-claims.
- `permissions.id-token: write` **не** маппится на это: парсер (`code.forgejo.org/forgejo/runner/.../act/jobparser`,
  поле `EnableOpenIDConnect` с тегом `yaml:"enable-openid-connect"`) читает именно
  `enable-openid-connect`.

В workflow release job задан только `permissions: {id-token: write}`; `enable-openid-connect: true`
нет ни на уровне workflow, ни на уровне job → рантайм-токен без OIDC-scope, `ACTIONS_ID_TOKEN_*`
не выставляются (`internal/app/run/runner.go:312–313` читают именно `forgejo_actions_id_token_*`).
Keyless `cosign sign/verify` не получит id-token → release упадёт на этапе подписи/верификации.

Дополнительно: даже при включённом OIDC формат identity не совпадает. Forgejo `sub`
(`services/actions/auth.go:148–155`):
```
default: "repo:<owner>/<repo>:ref:<ref>"
```
Для workflow_dispatch это `repo:aiopslab/otus-diplom:ref:refs/heads/main`, тогда как в workflow
`WORKFLOW_IDENTITY = https://git.aiopslab.online/aiopslab/otus-diplom/.forgejo/workflows/p8c-portal-forgejo-release.yml@refs/heads/main`
(GitHub-стиль). `cosign verify --certificate-identity` с таким значением не сойдётся.
Issuer `https://git.aiopslab.online` (`OIDC_ISSUER`) соответствует `setting.AppURL`
(`routers/api/actions/oidc.go:115`), это корректно.

## 7. BLOCKED и предложения (решение архитектора)

### Fix A — привязка workflow-SHA вместо отсутствующего GITHUB_WORKFLOW_SHA
Секрет `POLICY_WORKFLOW_SHA` сохраняет смысл «reviewed blob workflow». Заменить рантайм-источник
на вычисляемый внутри job (blob SHA самого файла workflow из main), либо перейти на `workflow_ref`:

- A1 (минимально, сохраняет blob-SHA): в preflight дополнительно сделать checkout репозитория
  `aiopslab/otus-diplom` на `${{ github.sha }}` и вычислить
  `git rev-parse HEAD:.forgejo/workflows/p8c-portal-forgejo-release.yml` (blob SHA), передать как
  `--observed-workflow-sha`. Тогда triple-check: POLICY pin == owner document == **вычисленный blob**
  (вместо несуществующей `$GITHUB_WORKFLOW_SHA`).
- A2 (альтернатива): привязаться к `github.workflow_ref` (реально доступен:
  `aiopslab/otus-diplom/.forgejo/workflows/p8c-portal-forgejo-release.yml@refs/heads/main`), заведя
  `POLICY_WORKFLOW_REF`; `--observed-workflow-sha` заменить на `--observed-workflow-ref`.
- A3 (консервативно): привязаться к `github.sha` (commit SHA main) — он уникально определяет дерево,
  а значит и blob workflow; проверить `github.sha == POLICY_COMMIT_SHA` и blob по пути.

Одноразовая авторизация при этом полностью сохраняется: run_id (из `return_run_info`) + attempt=1 +
expiry, секрет читается только в момент выдачи task preflight.

### Fix B — OIDC release job
- Добавить `enable-openid-connect: true` (workflow- или release-job уровень).
- Заменить `WORKFLOW_IDENTITY` на Forgejo-формат `repo:aiopslab/otus-diplom:ref:refs/heads/main`
  (либо `cosign verify --certificate-identity-regexp`). Issuer оставить `https://git.aiopslab.online`.

Оба Fix требуют правки опубликованного и запенинненного workflow (POLICY_WORKFLOW_SHA — blob
текущего файла; после правки blob изменится). Это вне полномочий engineer — выполняется только
после приёмки архитектором и повторной публикации.

## 8. Источники (пины)

- Forgejo server `v15.0.11` = `753f7edc775a97e66cd13d410404d5edc99b6b04`
  (`https://codeberg.org/forgejo/forgejo`): `services/actions/context.go`,
  `services/actions/task.go`, `services/actions/secret.go`, `services/actions/auth.go`,
  `routers/api/v1/repo/action.go`, `modules/structs/workflow.go`, `models/actions/run.go`,
  `models/actions/run_job.go`, `services/actions/job_emitter.go`, `routers/api/actions/oidc.go`.
- forgejo-runner `v13.2.2` = `0e61343d1cb98d2a381d0d18f34aea408e66e4d2`
  (`https://code.forgejo.org/forgejo/runner`): `act/model/github_context.go`,
  `internal/app/run/runner.go`, `internal/app/run/runner_test.go`.

## 9. Границы и статус

- run_id-привязка: **CONFIRMED** (раздел 5).
- Допуск B целиком: **BLOCKED** (разделы 1, 6), предложения в разделе 7.
- Вердикт по п. «При невозможности — BLOCKED»: механизм run_id достижим, но workflow в текущей
  редакции не пройдёт preflight/release из-за дефектов A и B. Архитектору — принять Fix A/B и
  перепубликовать workflow перед первым B.
