# P8C — Forgejo Actions build spec для закреплённого source SHA (ПОДГОТОВКА, НЕ ИСПОЛНЕНИЕ)

Дата: 2026-11-20 UTC. Исполнитель подготовки: Hermes engineer (`hermes-5.187.1.37-engineer`).
Тип документа: спецификация сборки (AUTHOR_PROPOSAL), НЕ допуск на исполнение.
Основание: решение владельца issue #29 (comment 1680); наряд архитектора issue #49.

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
| образ приложения | `portal/Containerfile` | `e158e2f7…` | `54d86c2b…` | 338 | **Имя `Containerfile`, НЕ `Dockerfile`** — сборка обязана передавать `--opt filename=Containerfile` (см. §3). `FROM scratch`, бинарник собирается вне контейнера, `USER 65532:65532`. |
| seed (bootstrap, НЕ приложение) | `portal/tools/Seed.Containerfile` | (в дереве) | — | — | отдельный scope, не deployable. |

Пробел (фиксируется, не блокирует подготовку): файл с именем `Dockerfile` в дереве
отсутствует — сборка ориентирована на BuildKit `Containerfile`. Это не дефект, а
факт; инструкция §3 закрепляет точное имя файла.

### 1.3 Lock-файлы приложения

| Уровень | Путь | blob | sha256 | size | Состояние digest |
|---|---|---|---|---|---|
| Go-модули | `portal/go.mod` | `55e30c3b…` | `0ebed832…` | 2233 | — |
| Go-суммы | `portal/go.sum` | `1447b671…` | `195a860f…` | 11624 | — |
| npm (только тестовые deps) | `portal/package.json` | `13cdf96e…` | `288fad7a…` | 249 | — |
| npm lock | `portal/package-lock.json` | `3eb710ab…` | `2953d177…` | 29194 | — |
| приложение + toolchain | `portal/versions.lock` | `5a5853bc…` | `0aa32429…` | 2194 | `image.digest: "NOT_VERIFIED"` |
| tool/action pins | `portal/tools/pins.lock.json` | `4fb6f353…` | `b4f60eda…` | 2021 | `source_sha: "TO_BE_RECORDED_AT_VERIFY"` |
| платформенные образы | `images.lock` | `9f723bc7…` | `9d998506…` | 8158 | **нет записи `portal`** (см. §1.4) |
| платформенные версии | `versions.lock` | `05beed6b…` | `ee736140…` | 1803 | — |

### 1.4 Пробелы (честно фиксируются)

1. **`images.lock` не содержит записи об образе приложения `portal`.** В нём только
   инфраструктурные образы (kube-vip, calico, piraeus, metallb, envoy, metrics-server).
   Единственное «домашнее» место для application digest сейчас — `portal/versions.lock`
   (`image.digest`). Решение владельца (#29#1680) говорит «фиксируются в
   `images.lock`/`versions.lock`» — требуется решение, куда именно писать verified
   digest (новая запись в `images.lock` и/или `portal/versions.lock`). **GAP — требует
   решения архитектора/владельца.**
2. **Расхождение registry-ссылок.** `portal/versions.lock` и `portal/manifests/deployment.yaml`
   (blob `2cb27165…`) ссылаются на `ghcr.io/dedvmedved-dot/otus-diplom-portal` (GHCR),
   тогда как доверенный канал по #29#1680 — Forgejo/self-hosted. Итоговый registry-путь
   (`<REGISTRY_HOST>` + имя пакета) — P0-параметр владельца, **NOT_VERIFIED**, не изобретается.
3. **Action pins не переносятся.** `pins.lock.json` фиксирует GitHub SHA
   (`actions/checkout@11bd719…`, `docker/login-action@9780b0c…`,
   `actions/upload-artifact@65462800…`); на Forgejo это другие репозитории с другими SHA.
   Точные SHA Forgejo-fork — **NOT_VERIFIED** до первого запуска (см. §2, §6).
4. **`TO_BE_RECORDED_AT_VERIFY`** в `pins.lock.json.source_sha` — фактическая подстановка
   закреплённого source SHA туда ещё не выполнена (отложено до фазы исполнения).

---

## 2. Сопоставление существующих шаблонов с Forgejo Actions (self-hosted)

Существующие шаблоны `portal/tools/p8c-portal-release.yml.template` и
`p8c-portal-seed.yml.template` написаны под **GitHub Actions** (`dedvmedved-dot/otus-diplom`,
GHCR, `token.actions.githubusercontent.com`). Сопоставление с целевой площадкой:

| Concern | GitHub Actions (существующие шаблоны) | Forgejo Actions (self-hosted runner) |
|---|---|---|
| каталог автозапуска | `.github/workflows/` | `.forgejo/workflows/` (шаблон §3 держится ВНЕ него = неактивен) |
| runner | `runs-on: ubuntu-24.04` (hosted) | `runs-on: <SELF_HOSTED_RUNNER_LABEL>` — метка, которую регистрирует владелец |
| checkout | `actions/checkout@11bd719…` | `actions/checkout@<FORGEJO_CHECKOUT_SHA>` — другой fork/SHA |
| upload-artifact | `actions/upload-artifact@65462800…` | Forgejo-эквивалент (SHA TBD) |
| login в registry | `docker/login-action@9780b0c…` | Forgejo `docker/login-action` fork, либо `docker login` по secret |
| дефолтный токен | `secrets.GITHUB_TOKEN` (выдаётся автоматически) | **НЕ выдаётся автоматически** — secret владельца (напр. `FORGEJO_TOKEN`) |
| OIDC issuer | `https://token.actions.githubusercontent.com` | `https://git.aiopslab.online` (подтверждено read-only discovery §5.3) |
| certificate-identity | `https://github.com/dedvmedved-dot/otus-diplom/.github/workflows/…@refs/heads/main` | `https://git.aiopslab.online/aiopslab/otus-diplom/.forgejo/workflows/p8c-portal-forgejo-release.yml@refs/heads/main` |
| registry | `ghcr.io` (PRIVATE) | Forgejo package registry **или** доверенный внутренний registry (P0, #29#1680) |
| `services.postgres` | поддерживается | поддерживается (self-hosted runner должен исполнять docker) |
| `workflow_dispatch` inputs | поддерживается | поддерживается |
| `GITHUB_OUTPUT`/`GITHUB_ENV`/`GITHUB_PATH`/`RUNNER_TEMP` | есть | есть (act-runner) |
| `github.sha`/`github.ref`/`github.run_attempt` | есть | есть (эмулируются); `GITHUB_WORKFLOW_SHA` — проверить при первом запуске |

Суть расхождений: **(1)** action refs и registry-путь меняются, **(2)** OIDC issuer/identity
меняются (меняет проверяемый builder.id и cosign identity), **(3)** `secrets.GITHUB_TOKEN`
не выдаётся — нужен явный secret, **(4)** runner — самохостимый, его метку задаёт владелец.

---

## 3. Неактивный workflow + цепочка проверки (инструкция)

Файл: **`portal/tools/p8c-portal-forgejo-release.yml.template`** (в этой ветке).
Он НЕ лежит в `.forgejo/workflows/`, поэтому Forgejo его не запускает — неактивен по
конструкции. Публикация в `.forgejo/workflows/` и dispatch — отдельное решение архитектора.

Цепочка, которую сборка обязана пройти (порядок жёсткий, каждый шаг fail-closed):

1. **Точный source SHA.** `actions/checkout` с `ref` = литерал
   `d22aa8f1170deaf09580518916ea02c7c4d8bfba` (НЕ runtime `github.sha`/HEAD main); шаг
   `Verify checkout` сверяет `git rev-parse HEAD` с литералом и требует чистое дерево.
   Несовпадение → STOP (до сборки).
2. **Digest из registry, НЕ из тега.** Сборка OCI (`buildctl`, BuildKit, `Containerfile`)
   даёт digest из `build-metadata.json`; затем шаг `Verify registry digest bytes`
   повторно получает манифест из registry по digest и сверяет с `Docker-Content-Digest`
   и с sha256 байтов манифеста (`release-check.py registry`). Тег `candidate` — только
   транспортный ярлык; identity = `@sha256:<64hex>`. Подмена digest тегом запрещена.
3. **Связь с доверенным run + SLSA provenance.** Keyless cosign по Forgejo OIDC
   (`--certificate-oidc-issuer https://git.aiopslab.online`,
   `--certificate-identity …/.forgejo/workflows/p8c-portal-forgejo-release.yml@refs/heads/main`),
   `-a ref=<pinned SHA>`; attest `slsaprovenance` + `verify-attestation`; provenance
   (`release-check.py predicate`) связывает `builder.id` (workflow identity) и
   `invocation.configSource.digest.sha1 == <pinned SHA>`, subject — digest образа.
4. **Только после проверки — обновление lock.** Job `update-lock` вызывает
   `forgejo_lock_gate.py` (единая валидация, см. §4) с (pinned SHA, HEAD, digest из
   registry, image_ref, provenance.json). Обновление `portal/versions.lock`
   (`image.digest`) происходит **только** при полном связывании; иначе файл не меняется
   и run падает. До фактической сборки значение остаётся `NOT_VERIFIED`.

Правила, закреплённые в шаблоне:
- digest **никогда** не подменяется тегом и **никогда** не изобретается;
- checkout/sourceRevision/provenance привязаны к литералу `d22aa8f…`, не к `github.sha`;
- все P0-параметры (`<SELF_HOSTED_RUNNER_LABEL>`, `<REGISTRY_HOST_OWNER_SUPPLIED>`,
  `<FORGEJO_CHECKOUT_SHA>`, secret'ы registry) — плейсхолдеры, владелец передаёт вне git.

---

## 4. Lock-update gate (fail-closed, единая валидация)

Модуль: **`portal/tools/forgejo_lock_gate.py`** (эта ветка). Чистая функция
`decide_lock_update(source_sha, digest, provenance, image_ref, pinned_source_sha)`
возвращает `allowed` только если **все** условия выполнены:

1. `pinned_source_sha` и `source_sha` — 40-hex, и `source_sha == pinned_source_sha`;
2. `digest` — строго `sha256:<64hex>` (тег/seed/любая иная строка отклоняется);
3. SLSA provenance связывает `builder.id == <Forgejo workflow identity>`,
   `invocation.configSource.digest.sha1 == source_sha`, `subject` привязывает digest образа.

CLI `--apply <lock>` записывает digest в `portal/versions.lock` **только** при
`allowed=True`, атомарно (`tmp` + `os.replace`); при любом отказе файл остаётся
байтово идентичным. Тот же модуль импортирует отрицательный тест (§5.2) — одна
реализация валидации, без дублирования.

---

## 5. Локальная проверка (результат)

### 5.1 Синтаксис workflow-шаблона

`portal/tools/p8c-portal-forgejo-release.yml.template` проверен офлайн:
YAML-разбор (PyYAML `safe_load`) + структурные инварианты (name/on/jobs, у каждого
job есть `runs-on`+`steps`, сбалансированность `${{ }}`). Результат:

```text
SYNTAX = VERIFIED (YAML well-formed; 3 jobs; expressions balanced)
RUN = NOT_VERIFIED (workflow не публиковался и не запускался — границы #49)
```

Полный вывод: `evidence/P8/…/01-syntax-check.txt`.

### 5.2 Отрицательная проверка (SHA mismatch / отсутствие provenance)

`portal/tools/test_forgejo_lock_gate.py` (unittest) прогоняет реальный
`forgejo_lock_gate` с синтетическими входами (без сборки/registry/учётных данных):

```text
test_valid_bindings_allowed                          PASS
test_source_sha_mismatch_not_allowed                 PASS   (lock update НЕ разрешён)
test_missing_provenance_not_allowed                  PASS   (lock update НЕ разрешён)
test_provenance_binds_wrong_source_not_allowed       PASS
test_provenance_binds_wrong_digest_not_allowed       PASS
test_tag_instead_of_digest_not_allowed               PASS   (digest НЕ подменяется тегом)
test_provenance_wrong_builder_not_allowed            PASS
test_apply_writes_only_when_allowed                  PASS
test_apply_source_mismatch_leaves_lock_untouched     PASS   (файл байтово идентичен)
test_apply_missing_provenance_leaves_lock_untouched  PASS   (файл байтово идентичен)
test_apply_tag_instead_of_digest_leaves_lock_untouched PASS
TESTS_TOTAL=11  TESTS_FAILED=0  HARNESS_EXIT=0
```

Вывод: **несовпадение SHA или отсутствие provenance не разрешает обновление lock** —
подтверждено исполняемым тестом (не описанием). Полный вывод:
`evidence/P8/…/02-negative-check.txt`.

### 5.3 OIDC issuer (read-only discovery)

`GET https://git.aiopslab.online/.well-known/openid-configuration` → `issuer:
https://git.aiopslab.online` (HTTP 200). Это единственный сетевой факт, снятый при
подготовке (публичный, read-only, не стенд). Полный вывод:
`evidence/P8/…/03-oidc-discovery.txt`.

---

## 6. Оставшиеся предпосылки первого запуска (NOT_VERIFIED до их выдачи)

1. **P0-параметры владельца (вне git):** метка self-hosted runner, registry host + имя
   пакета, registry credentials (read/push, для workload — read-only pull-токен, #29#1680),
   Forgejo secret для CI-токена (вместо авто-`GITHUB_TOKEN`).
2. **SHA Forgejo action-форков** (`actions/checkout` и при необходимости
   `docker/login-action`/`upload-artifact`) — закрепить и занести в `pins.lock.json`.
3. **Подтверждение `GITHUB_WORKFLOW_SHA`/`github.*`** на self-hosted runner Forgejo при
   первом запуске (для строгой привязки workflow_sha в gate-документе).
4. **Решение о домашнем месте digest:** новая запись в `images.lock` и/или
   `portal/versions.lock.image.digest` (см. §1.4.1).
5. **Решение о публикации workflow** (перенос шаблона в `.forgejo/workflows/`) и о
   gate-документе/бюджете одноразового dispatch (проект учёта из
   `P8C_CI_RELEASE_GATE_SPEC_20261118.md` §3.3 остаётся недоказанным).
6. **Независимая ревизия CA/UID владельцем OTUS** и **подтверждение pull** для workload —
   предшествуют открытию окна (не сборке спецификации).

После готовности входов: фактическая сборка → независимая ревизия CA/UID →
подтверждение pull для workload → отдельное решение архитектора об окне.

---

## 7. Итог

```text
PREPARATION = COMPLETE (REVIEW_READY, offline)
EXECUTION / LOCK_UPDATE = NOT_AUTHORIZED (digest остаётся NOT_VERIFIED)
```

Спецификация готова к ревью архитектора. Сборка, публикация workflow/образа, запрос
секретов, обращение к стенду и обновление lock **не выполнялись**. PR и итоговый SHA
коммита этой ветки указываются в задаче архитектора (вне git-коммита — во избежание
самореференции SHA в собственном коммите).
