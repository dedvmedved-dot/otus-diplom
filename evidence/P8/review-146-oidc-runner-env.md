# Review #146 — условия выдачи OIDC id-token env по исходникам Forgejo 15.0.11 и runner

Задание #146. Основание: #144 (комментарий 12142), run 71, SHA
`c2194b161fe7e5e5218bd737c335faa63c41db0d`. Ограничение: только статический
анализ. Без запуска, без правок workflow/сервера, без запроса токенов, без
dispatch/rerun/merge. Выпуск B — NOT_READY.

## 1. Метод: закреплённые исходники

Склонированы точные версии (shallow clone по тегу):

| Компонент | Версия (тег) | Роль |
|---|---|---|
| Forgejo (сервер) | `v15.0.11` | генерация задачи и OIDC-контекста |
| forgejo/runner (бинарь) | `v6.1.0` | исполнение задачи; версия из лога run 71 (`version:v6.1.0`) |
| forgejo/runner/v12 (jobparser) | `v12.10.2` | парсер workflow; закреплён в `forgejo go.mod:14` (`code.forgejo.org/forgejo/runner/v12 v12.10.2`) |
| forgejo/act | `v1.23.1` | библиотека исполнения шагов; `runner go.mod:105` (`replace github.com/nektos/act => code.forgejo.org/forgejo/act v1.23.1`) |

## 2. Трассировка: где читается `enable-openid-connect`

Ключ `enable-openid-connect` читается парсером workflow (jobparser) и на уровне
**workflow**, и на уровне **job**. Правило предшествования: **уровень job
перекрывает уровень workflow**; если ни один не задан — по умолчанию `false`.

| Шаг | Файл:строка (runner/v12 v12.10.2) | Что делает |
|---|---|---|
| Поле workflow | `act/model/workflow.go:32` | `EnableOpenIDConnect *bool yaml:"enable-openid-connect"` (уровень workflow) |
| Поле job | `act/model/workflow.go:233` | `EnableOpenIDConnect *bool yaml:"enable-openid-connect"` (уровень job) |
| Захват уровня workflow | `act/jobparser/jobparser.go:127` (и `:532`, `:610` для reusable) | `workflowLevelEnableOpenIDConnect: origin.EnableOpenIDConnect` |
| Итог для job | `act/jobparser/jobparser.go:286` | `swf.EnableOpenIDConnect = evaluateEnableOpenIDConnect(bothJobs, bothJobs.workflowLevelEnableOpenIDConnect)` |
| Предшествование | `act/jobparser/jobparser.go:317-330` | job-уровень выигрывает; затем workflow-уровень; иначе `false` |
| Подтверждено тестом | `act/jobparser/testdata/enable_openid_connect.in.yaml` → `.out.yaml` | workflow-`true` наследуется job без переопределения; job-`false` перебивает |

Вывод по пункту «workflow или job»: **оба**. В run 71 ключ стоит на уровне
workflow (`enable-openid-connect: true` перед `jobs:`) — это корректно
наследуется единственным job `diagnostic` (без job-переопределения).

## 3. Условия выдачи на сервере (Forgejo 15.0.11)

| Шаг | Файл:строка | Что делает |
|---|---|---|
| Чтение флага job | `services/actions/task.go:162` | `enableOpenIDConnect, err := t.Job.EnableOpenIDConnect()` |
| Декодирование payload | `models/actions/run_job.go:362-368` | возвращает `jobWorkflow.EnableOpenIDConnect` (результат jobparser) |
| Переопределение fork-PR | `services/actions/task.go:167-171` | `if run.IsForkPullRequest && run.TriggerEvent != pull_request_target { enableOpenIDConnect = false }` |
| Инъекция в контекст задачи | `services/actions/task.go:181-187` | при `true` кладёт `forgejo_actions_id_token_request_token` и `forgejo_actions_id_token_request_url` в `gitCtx` |
| OIDC-claims в runtime-токен | `services/actions/auth.go:92-99` | `if enableOpenIDConnect { ... OIDCExtra/OIDCSub ... }` |

Важно: **никакие настройки сервера или репозитория не влияют на выдачу**,
кроме самого ключа YAML и исключения fork-PR. GitHub-ключ `permissions:` /
`permissions.id-token` Forgejo-парсером **не читается** (в Go-модели
`act/model/workflow.go` поля `permissions` нет; `id-token` встречается только в
необязательной JSON-схеме редактора `act/schema/workflow_schema.json:1318`,
которая на парсинг не влияет).

## 4. Условие, при котором runner передаёт env шагу (корневая причина)

Сервер кладёт id-token-данные в контекст задачи под именами
`forgejo_actions_id_token_request_url` / `forgejo_actions_id_token_request_token`.
Превращает их в шаговые переменные `ACTIONS_ID_TOKEN_REQUEST_URL` /
`ACTIONS_ID_TOKEN_REQUEST_TOKEN` — **только сам runner**. Здесь и есть разрыв
версий:

| Версия runner | Файл:строка | Наличие инъекции id-token env |
|---|---|---|
| `v6.1.0` (установлен) | `internal/app/run/runner.go` целиком | **НЕТ**: только `ACTIONS_RUNTIME_TOKEN` из `gitea_runtime_token` (`:179-184`); `ACTIONS_ID_TOKEN_REQUEST_*` не встречается нигде в дереве (0 вхождений `ACTIONS_ID_TOKEN_REQUEST` / `forgejo_actions` / `id_token`) |
| `v12.10.2` (совместим с сервером) | `internal/app/run/runner.go:313-314` | `runEnvs["ACTIONS_ID_TOKEN_REQUEST_TOKEN"] = taskContext["forgejo_actions_id_token_request_token"]...` и `..._URL` |

Версия установленного runner подтверждена логом run 71: строка
`otus-diplom(version:v6.1.0) received task 224 ...` в точности соответствует
формату `internal/app/run/runner.go:134` (`"%s(version:%s) received task ...",
r.name, ver.Version(), ...`).

Библиотека `forgejo/act v1.23.1` (используется v6.1.0) также не инъектирует
id-token env: `pkg/runner/run_context.go:1185-1245` (`withGithubEnv`) кладёт только
стандартные `GITHUB_*`/`FORGEJO_TOKEN`/`ACTIONS_RUNTIME_*`; в Go-коде `act` нет ни
одного вхождения `id-token`/`oidc`/`openid` (только тест-фикстуры JS).

Версия, с которой инъекция появилась: `v12.5.0` (в `v12.4.0` и всех `v6.x`
включительно — отсутствует).

## 5. Таблица условий: установлено / UNKNOWN

| Условие | Статус | Источник |
|---|---|---|
| `enable-openid-connect` читается на уровне workflow И job; job перебивает | УСТАНОВЛЕНО | jobparser.go:286,317-330; workflow.go:32,233; тест-данные |
| workflow-`true` из run 71 наследуется job `diagnostic` | УСТАНОВЛЕНО | testdata enable_openid_connect (job2 без переопределения) |
| Сервер 15.0.11 при `true` кладёт `forgejo_actions_id_token_request_*` в контекст | УСТАНОВЛЕНО | task.go:162,181-187; run_job.go:362-368 |
| fork-PR форсит `false` (к `workflow_dispatch` не применимо) | УСТАНОВЛЕНО | task.go:167-171 |
| `permissions:` / `id-token: write` на выдачу не влияет | УСТАНОВЛЕНО | отсутствие поля в Go-модели workflow.go |
| Runner v6.1.0 инъектирует `ACTIONS_ID_TOKEN_REQUEST_*` в шаг | **ОПРОВЕРГНУТО** | runner.go v6.1.0 — кода нет (0 вхождений) |
| Runner v12.10.2 (v12.5.0+) инъектирует `ACTIONS_ID_TOKEN_REQUEST_*` | УСТАНОВЛЕНО | runner.go:313-314 (v12.10.2) |
| Наличие env при запуске на обновлённом runner | **UNKNOWN** (нужен допуск владельца на новый разовый запуск) | вне статического анализа |

## 6. Вывод (корневая причина)

Run 71 получил `ENV_MISSING ACTIONS_ID_TOKEN_REQUEST_URL` **не из-за workflow**.
Workflow корректен: `enable-openid-connect: true` на уровне workflow корректно
парсится сервером 15.0.11 (jobparser v12.10.2) и сервер корректно кладёт
id-token-данные в контекст задачи. Причина — **устаревший runner v6.1.0**, который
не реализует инъекцию `ACTIONS_ID_TOKEN_REQUEST_URL`/`_TOKEN` в шаг. Сервер и
jobparser совместимы с runner серии v12 (`v12.10.2`), который эту инъекцию
содержит.

## 7. Правка / STOP

**STOP** — правка workflow невозможна и не нужна (workflow уже корректен; менять
workflow/сервер заданием запрещено). Требуется действие оператора:

> Обновить бинарь runner с `v6.1.0` до серии `v12` (≥ `v12.5.0`, рекомендуется
> `v12.10.2` — версия jobparser, закреплённая в Forgejo 15.0.11). После
> обновления — новый разовый запуск по отдельному допуску владельца для
> наблюдения `ACTIONS_ID_TOKEN_REQUEST_URL`/`_TOKEN` и claims `iss`/`aud`/`sub`.

Минимальная подтверждённая правка для ревью: **отсутствует** (не существует
изменения workflow, которое включило бы env на runner v6.1.0). Выпуск B —
NOT_READY до обновления runner и повторного допуска.

## 8. Границы (что НЕ делалось)

- Не изменялся workflow, сервер, ветки `engineer/126-oidc-pilot` /
  `engineer/139-oidc-enable-openid`, PR #140.
- Не запрашивались токены/секреты; не выполнялись dispatch/rerun/merge.
- Не печатались URL, значения env, JWT, payload, заголовки.
- Анализ только по исходникам и документации закреплённых версий.

## 9. Ссылки на версионные строки

- Forgejo 15.0.11: `services/actions/task.go:162,167-171,181-187`;
  `models/actions/run_job.go:362-368`; `services/actions/auth.go:92-99`;
  `go.mod:14` (пин runner/v12).
- runner v6.1.0: `internal/app/run/runner.go:134,154-170,179-184`; `go.mod:105`
  (пин act v1.23.1).
- forgejo/act v1.23.1: `pkg/runner/run_context.go:1185-1245`.
- runner/v12 v12.10.2: `internal/app/run/runner.go:313-314`;
  `act/model/workflow.go:32,233`; `act/jobparser/jobparser.go:127,286,317-330,532,610`;
  `act/jobparser/testdata/enable_openid_connect.{in,out}.yaml`.
