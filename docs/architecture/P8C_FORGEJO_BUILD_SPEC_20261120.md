# P8C — Forgejo Actions build spec для закреплённого source SHA (ПОДГОТОВКА, НЕ ИСПОЛНЕНИЕ)

Дата: 2026-11-20 UTC. Исполнитель подготовки: Hermes engineer (`hermes-5.187.1.37-engineer`).
Тип документа: спецификация сборки (AUTHOR_PROPOSAL), НЕ допуск на исполнение.
Основание: решение владельца issue #29 (comment 1680); наряд архитектора issue #49;
доработка по решению #52 (review `a5f0e759…`) — issue #54.

Статусные строки:

```text
FORGEJO_BUILD_SPEC = REVIEW_READY (AUTHOR_PROPOSAL; не ARCHITECT_ACCEPTED)
APPLICATION_DIGEST / SLSA_PROVENANCE = NOT_VERIFIED   (не существуют до фактической сборки)
WORKFLOW_PUBLICATION / WORKFLOW_DISPATCH / BUILD / PUSH / SIGN / ATTEST = NOT_AUTHORIZED
LOCK_UPDATE = NOT_PERFORMED   (digest в locks остаётся NOT_VERIFIED)
RUNTIME_6 / P8D = NO-GO / NOT_OPENED; #32 = HOLD
```

Границы соблюдены: CI не запускался, образы не публиковались, секреты не запрашивались,
стенд не затрагивался. P0-параметры владелец передаёт вне git.

---

## 1. Фактические пути по дереву `d22aa8f1170deaf09580518916ea02c7c4d8bfba`

`git rev-parse HEAD` = `d22aa8f1170deaf09580518916ea02c7c4d8bfba`;
`git rev-parse HEAD^{tree}` = `72fbe02838850c1ed9576ef73c263481fe607322`.

### 1.1 Контекст сборки

| Роль | Путь | blob (HEAD) | sha256 (байты) | size |
|---|---|---|---|---|
| контекст сборки приложения | `portal/` | tree `ac032aab…` | — | — |
| Makefile (build/test/image) | `portal/Makefile` | `252ff945…` | `47dee8b2…` | 769 |

### 1.2 Dockerfile (образ приложения)

| Роль | Путь | blob | sha256 | size | Примечание |
|---|---|---|---|---|---|
| образ приложения | `portal/Containerfile` | `e158e2f7…` | `54d86c2b…` | 338 | **Имя `Containerfile`, НЕ `Dockerfile`** — сборка обязана передавать `--opt filename=Containerfile`. `FROM scratch`, бинарник собирается вне контейнера, `USER 65532:65532`. |
| seed (bootstrap, НЕ приложение) | `portal/tools/Seed.Containerfile` | (в дереве) | — | — | отдельный scope, не deployable. |

### 1.3 Lock-файлы приложения

| Уровень | Путь | blob | sha256 | size | Состояние digest |
|---|---|---|---|---|---|
| Go-модули | `portal/go.mod` | `55e30c3b…` | `0ebed832…` | 2233 | — |
| Go-суммы | `portal/go.sum` | `1447b671…` | `195a860f…` | 11624 | — |
| npm (только тестовые deps) | `portal/package.json` | `13cdf96e…` | `288fad7a…` | 249 | — |
| npm lock | `portal/package-lock.json` | `3eb710ab…` | `2953d177…` | 29194 | — |
| приложение + toolchain | `portal/versions.lock` | `5a5853bc…` | `0aa32429…` | 2194 | `image.digest: "NOT_VERIFIED"` |
| tool/action pins | `portal/tools/pins.lock.json` | `4fb6f353…` | `b4f60eda…` | 2021 | `source_sha: "TO_BE_RECORDED_AT_VERIFY"` |
| платформенные образы | `images.lock` | `9f723bc7…` | `9d998506…` | 8158 | **нет записи `portal`** |
| платформенные версии | `versions.lock` | `05beed6b…` | `ee736140…` | 1803 | — |

### 1.4 Разделение source и tools (доработка #54, блокирующее расхождение 2)

Дерево `d22aa8f…` содержит только ИСХОДНЫЙ код приложения и toolchain-записи,
но НЕ содержит Forgejo-инструментарий, который эта ветка вводит заново
(`forgejo_lock_gate.py`, `test_forgejo_lock_gate.py`,
`check_forgejo_workflow_syntax.py`, `p8c-portal-forgejo-release.yml.template`).
Поэтому workflow держит **два независимых неизменяемых pin**:

| Pin | Значение | Назначение |
|---|---|---|
| `PINNED_SOURCE_SHA` | `d22aa8f1170deaf09580518916ea02c7c4d8bfba` | исходники приложения + `Containerfile` + `install-verified-go.sh` |
| `PINNED_TOOLS_SHA` | `<FORGEJO_TOOLS_SHA>` (P0, фиксируется при публикации) | Forgejo-инструментарий этой ветки |

Обе checkout-директории (`src/`, `tools/`) независимы; `git rev-parse HEAD` в
каждой сверяется со своим литералом, и инвентаризация файлов
(`forgejo_lock_gate.inventory`) проверяет, что каждый используемый файл лежит в
СВОЁМ дереве, а tools-файлы не подменяют source новым HEAD.

### 1.5 Пробелы (честно фиксируются)

1. **`images.lock` не содержит записи об образе приложения `portal`.** Единственное
   «домашнее» место application digest — `portal/versions.lock` (`image.digest`).
   Решение владельца (#29#1680) говорит «фиксируются в `images.lock`/`versions.lock`»
   — требуется решение, куда именно. **GAP — требует решения архитектора/владельца.**
2. **Расхождение registry-ссылок.** `portal/versions.lock` и `deployment.yaml`
   ссылаются на `ghcr.io/dedvmedved-dot/otus-diplom-portal`, тогда как доверенный
   канал — Forgejo/self-hosted. Итоговый registry-путь — P0, **NOT_VERIFIED**.
3. **Action pins не переносятся.** `pins.lock.json` фиксирует GitHub SHA; Forgejo
   fork SHA — **NOT_VERIFIED** до первого запуска.
4. **`TO_BE_RECORDED_AT_VERIFY`** в `pins.lock.json.source_sha` — подстановка
   закреплённого source SHA отложена до фазы исполнения.

---

## 2. Сопоставление с Forgejo Actions (self-hosted)

| Concern | GitHub Actions (существующие шаблоны) | Forgejo Actions (self-hosted runner) |
|---|---|---|
| каталог автозапуска | `.github/workflows/` | `.forgejo/workflows/` (шаблон §3 держится ВНЕ него = неактивен) |
| runner | `runs-on: ubuntu-24.04` | `runs-on: <SELF_HOSTED_RUNNER_LABEL>` |
| checkout | `actions/checkout@11bd719…` | `actions/checkout@<FORGEJO_CHECKOUT_SHA>` |
| upload-artifact | `actions/upload-artifact@65462800…` | Forgejo-эквивалент (SHA TBD) |
| login в registry | `docker/login-action@9780b0c…` | `docker login` по secret (или Forgejo fork) |
| дефолтный токен | `secrets.GITHUB_TOKEN` | **НЕ выдаётся** — secret владельца |
| OIDC issuer | `https://token.actions.githubusercontent.com` | `https://git.aiopslab.online` (read-only discovery) |
| certificate-identity | `.github/workflows/…@refs/heads/main` | `.forgejo/workflows/p8c-portal-forgejo-release.yml@refs/heads/main` |
| registry | `ghcr.io` (PRIVATE) | Forgejo package registry **или** доверенный внутренний registry (P0) |
| `services.postgres` | поддерживается | поддерживается |
| `workflow_dispatch` inputs | поддерживается | поддерживается |
| `GITHUB_OUTPUT`/`GITHUB_ENV`/`GITHUB_PATH`/`RUNNER_TEMP` | есть | есть (act-runner) |

---

## 3. Неактивный workflow + цепочка допуска (инструкция)

Файл: **`portal/tools/p8c-portal-forgejo-release.yml.template`** (эта ветка).
НЕ лежит в `.forgejo/workflows/` — неактивен по конструкции. Публикация и
dispatch — отдельное решение архитектора.

Цепочка допуска (порядок жёсткий, каждый шаг fail-closed; соответствует
блокирующим расхождениям #52):

1. **Owner gate (допуск владельца) — ПЕРВЫЙ шаг release-job, до доступа к
   credentials и до любых build/push/sign.** Вход `release_gate` **обязателен**
   (`required: true`); отсутствующий/просроченный/чужой допуск останавливает run.
   Проверяются: `owner`, `source_sha == PINNED_SOURCE_SHA`,
   `workflow_sha == PINNED_TOOLS_SHA`, `repository`, `package`, `ref`,
   `mode=LIVE`, `issued_at_utc` (не будущее, не просрочено), `expiry_hours`,
   `attempt=1` и `run_attempt=1`.
2. **Разделение source/tools.** Две независимые checkout-директории (`src/`,
   `tools/`) по двум независимым pin; `git rev-parse HEAD` сверяется с литералом;
   инвентаризация (`forgejo_lock_gate.inventory`) подтверждает наличие всех
   используемых файлов по соответствующим деревьям и отсутствие подмены source.
3. **Trusted registry.** Манифест получается и проверяется байтово ТОЛЬКО с
   доверенного registry (`REGISTRY`, P0). `forgejo_lock_gate.registry-fetch`
   отказывает неизвестному назначению ДО любого сетевого запроса (credentials не
   передаются постороннему host); проверяются `sha256(manifest_bytes) == digest` и
   `Docker-Content-Digest == digest`; `image_ref` обязан лежать под доверенным
   registry. Тег `candidate` — только транспортный ярлык.
4. **Подписанное утверждение того же run.** Keyless cosign по Forgejo OIDC;
   `cosign attest --type slsaprovenance` (предикат без subject — subject заполняет
   cosign), затем `cosign verify-attestation` пишет `attestation-provenance.jsonl`.
   **Gate читает именно этот проверенный statement**, а не локальный predicate:
   `subject` (image/digest) — из проверенного in-toto statement; `builder.id`,
   `invocation.configSource` (workflow SHA + entryPoint), `materials` (source SHA),
   `metadata.buildInvocationId` (run id) — из predicate; дополнительно сверяются
   issuer/identity (`--certificate-identity`/`--certificate-oidc-issuer`). Discovery
   само по себе доверие не даёт.
5. **Только после 1–4 — запись lock.** `forgejo_lock_gate.verify` принимает
   evidence-bundle и решает; запись `registry`+`digest` **одной парой** в
   `portal/versions.lock:image` происходит только при `inputs.apply_lock == true`
   (явная авторизация владельца) И при прошедшем gate. Проверка объединена в один
   job (`release`); отдельного `update-lock` job больше нет — доказательства
   передаются не между jobs, а внутри одного job.

Правила, закреплённые в шаблоне:
- digest никогда не подменяется тегом и никогда не изобретается;
- checkout/sourceRevision/provenance привязаны к литералу `d22aa8f…`, не к `github.sha`;
- все P0-параметры (`<SELF_HOSTED_RUNNER_LABEL>`, `<REGISTRY_HOST_OWNER_SUPPLIED>`,
  `<OWNER_IDENTITY_P0>`, `<FORGEJO_TOOLS_SHA>`, `<FORGEJO_CHECKOUT_SHA>`, secret'ы
  registry) — плейсхолдеры, владелец передаёт вне git.

---

## 4. Gate (fail-closed, единая валидация)

Модуль: **`portal/tools/forgejo_lock_gate.py`** (эта ветка). Единственная
реализация валидации, общая для (неактивного) workflow и offline-тестов. Чистые
функции, каждая возвращает `(allowed, reason)`; сетевого I/O внутри нет —
registry-транспорт инжектируется (mock в тестах).

- `verify_owner_gate` — допуск владельца (п.1).
- `verify_file_inventory` — разделение source/tools (п.2).
- `fetch_registry_manifest` (host-gate) + `verify_registry_manifest` (bytes) (п.3).
- `parse_verified_attestation` + `check_verified_statement` (п.4).
- `build_predicate` — SLSA-предикат без subject (subject заполняет cosign).
- `decide_lock_update(evidence, bindings, now)` — оркестрация всей цепочки.
- `apply_lock_pair` — запись `registry`+`digest` одной парой, атомарно, с отказом
  при несовпадении registry в lock.

CLI: `owner-gate`, `inventory`, `registry-fetch`, `digest`, `predicate`, `verify
[--apply]`. `verify` принимает binding-переопределения P0 (`--owner`,
`--trusted-registry`, `--workflow-sha`, …) — production всегда гейтится на
`time.time()`.

---

## 5. Локальная проверка (результат)

### 5.1 Синтаксис workflow-шаблона

```text
SYNTAX = VERIFIED (YAML well-formed; 2 jobs; 41 expressions balanced)
```

### 5.2 Юнит-тесты gate (37/37)

`test_forgejo_lock_gate.py` покрывает каждый слой: owner gate (missing/foreign/
expired/future/wrong-mode/attempt), file inventory (missing/smuggled/same-pin),
registry (foreign-host-refused-before-transport/bytes/dcd mismatch), verified
statement (subject/builder/materials/workflow-sha/run-id/type/buildType),
`apply_lock_pair` (pair + pair-mismatch rejection).

### 5.3 Offline интеграционный harness (23/23)

`test_forgejo_offline_integration.py` прогоняет ПОЛНУЮ цепочку
`decide_lock_update` с полностью валидным baseline и мутацией ровно одного поля
на негативный случай (гарантированное достижение именованной проверки):

- **положительный случай**: валидный evidence ⇒ ALLOWED; CLI `--apply` пишет пару
  `registry`/`digest` в scratch-lock, реальный lock не трогается.
- **отказ 1 (owner gate)**: отсутствующий / просроченный / чужой допуск.
- **отказ 2 (source/tools)**: tools-файл подменён в source-дерево; source подменён
  новым HEAD.
- **отказ 3 (registry)**: чужой host отклонён ДО сетевого запроса (mock transport
  не вызван); несовпадение bytes.
- **отказ 4 (verified statement)**: нет verified attestation; несвязанный subject;
  подмена predicate (другой source в materials); другой run; другой registry;
  несовпадение certificate identity/issuer.

Также структурно проверено, что owner gate — первый шаг release-job (до
login/build) и что вход `release_gate` обязателен.

Полные выводы: `evidence/P8/…/01-syntax-check.txt`, `02-unit-tests.txt`,
`03-integration-harness.txt`.

### 5.4 OIDC issuer (read-only discovery)

`GET https://git.aiopslab.online/.well-known/openid-configuration` →
`issuer: https://git.aiopslab.online` (HTTP 200). Единственный сетевой факт
(публичный, read-only, не стенд).

---

## 6. Оставшиеся предпосылки первого запуска (NOT_VERIFIED до их выдачи)

1. **P0-параметры владельца (вне git):** метка self-hosted runner, registry host +
   имя пакета, registry credentials, Forgejo secret для CI-токена, `OWNER_IDENTITY`.
2. **`PINNED_TOOLS_SHA`** — фиксируется литералом коммита, который несёт
   Forgejo-инструментарий, при публикации (не существует до слияния).
3. **SHA Forgejo action-форков** (`actions/checkout` и при необходимости
   `docker/login-action`) — закрепить и занести в `pins.lock.json`.
4. **Подтверждение `GITHUB_WORKFLOW_SHA`/`github.*`** на self-hosted runner Forgejo
   при первом запуске.
5. **Решение о домашнем месте digest:** новая запись в `images.lock` и/или
   `portal/versions.lock.image.digest` (см. §1.5.1).
6. **Решение о публикации workflow** и о gate-документе/бюджете dispatch.
7. **Независимая ревизия CA/UID владельцем OTUS** и **подтверждение pull** для
   workload — предшествуют открытию окна.

---

## 7. Итог

```text
PREPARATION = COMPLETE (REVIEW_READY, offline)
EXECUTION / LOCK_UPDATE = NOT_AUTHORIZED (digest остаётся NOT_VERIFIED)
```

Спецификация доработана по решению #52 и готова к повторному ревью архитектора.
Сборка, публикация workflow/образа, запрос секретов, обращение к стенду и
обновление lock **не выполнялись**. Итоговый SHA коммита ветки и PR указываются в
задаче архитектора (вне git-коммита — во избежание самореференции SHA).
