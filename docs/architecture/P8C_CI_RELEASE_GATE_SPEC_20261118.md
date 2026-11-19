# P8C CI Release Gate — спецификация (ПОДГОТОВКА, НЕ ИСПОЛНЕНИЕ)

Дата: 2026-11-19 (R1 — исправления по вердикту #2 issuecomment-409), Europe/Moscow.
Исполнитель подготовки: PRIMARY HERMES (engineer, assignee `hermes-5.187.1.37-engineer`).
Тип документа: спецификация gate (AUTHOR_PROPOSAL), НЕ допуск на исполнение.

Статусные строки:

```text
CI_RELEASE_GATE_SPEC = REVIEW_READY (AUTHOR_PROPOSAL, R1; не ARCHITECT_ACCEPTED)
CI_RELEASE / WORKFLOW_PUBLICATION / WORKFLOW_DISPATCH / BOOTSTRAP_PUSH = NOT_AUTHORIZED
LIVE_READINESS / NETWORKPOLICY_APPLY / DEPLOYMENT = FORBIDDEN
P8C = NOT_FINAL_ACCEPTED
```

Основание: source-этап завершён и принят. Публикуемый источник —
`d22aa8f1170deaf09580518916ea02c7c4d8bfba`. Настоящий документ фиксирует контракт
будущего CI release gate: что закреплено, что разрешено, какой бюджет, какие артефакты.
Никакой запуск, публикация workflow, build/push/sign/attest этим документом НЕ выполняется.

Примечание о площадках: очередь задач и репозиторий спецификаций — Forgejo
`aiopslab/otus-diplom` (git.aiopslab.online). Исполнение CI (GitHub Actions) и private-реестр
GHCR относятся к зеркалу `dedvmedved-dot/otus-diplom`. Закреплённые SHA едины для обоих
зеркал (main совпадает на pinned source).

Изменения R1 (по четырём пунктам вердикта #2/issuecomment-409):

1. §1.2.1–1.2.2 — явно разграничены blob-объект (SHA контента) и SHA будущего коммита
   публикации workflow; добавлены проверка побайтовой идентичности опубликованного
   workflow и согласование source checkout с runtime SHA (публикация коммитом меняет
   `github.sha`, поэтому checkout привязан к литералу `d22aa8f…`, не к `HEAD main`).
2. §2.3–2.4 — release и seed разделены как независимые scope; seed объявлен
   необязательным и с отдельным допуском; устранено противоречие тегов
   (`candidate` — release; `seed-<sha>` — только seed при CREATE_ALLOWED).
3. §3 — лимиты разделены на обеспеченные (в pinned шаблонах/коде) и предложенные
   (требуют доказательства одноразовости); определена единица бюджета и владелец
   учёта/погашения; зафиксирован STOP до доказательства одноразовости.
4. §4.4 — состав seed-evidence распределён по исходам (CREATE_ALLOWED/REUSE/STOP);
   убрана трактовка отсутствия известного application digest как доказательства различия.

---

## 1. Закреплённые source / workflow SHA

Authoritative pin = содержимое (blob/commit SHA), не тег. Любое байтовое изменение
закреплённого файла инвалидирует gate.

### 1.1 Source SHA

| Поле | Значение |
|---|---|
| source SHA (HEAD, принятый source-этап) | `d22aa8f1170deaf09580518916ea02c7c4d8bfba` |
| ветвь | `main` (Forgejo `origin/main` == `d22aa8f…`) |

### 1.2 Workflow + gate-помощники (path → blob → sha256 → size)

Манифест фактически исполняемых release/seed артефактов на pinned source (blob — объектный
SHA git, sha256 — SHA-256 содержимого файла):

| Path | blob | sha256 | size |
|---|---|---|---|
| portal/tools/p8c-portal-release.yml.template | a86521accc76f94dca9380e3b8805a319aa2668f | 8021503a01dd23e420cc1609a883bd21de7b974d32f38ef0828154c98342ecd6 | 14137 |
| portal/tools/p8c-portal-seed.yml.template | b631ed64ce543e0619e75cc2f95626a02ec87a75 | 7dc6acab5cce91b7e31ea62a39e6e8acfd8036bf354d242deb84442b141c3f71 | 9015 |
| portal/tools/release-check.py | ad49113c36eb7369fb3c6bfb25e1f6f0db2e150f | d21e75f138d3f66caf7be448d702740ea836911ee03da6a420d3fc4ea56b4a69 | 16389 |
| portal/tools/release_qualification.py | 3d5a4b408deb1845a29238906e162c19f1170b19 | f1522a80c24d1b5dc2cf7cb9bb0a66bafe3d21af5acb088f6a6a460045781802 | 5493 |
| portal/tools/verify-pins.py | 7704268df59ad94cac2c141c57bebb61a94a6b96 | a058c5449cf4a9a88006886c7fe39ef0e1d5ba74f796f3fba3f9bd8855faf3e3 | 8182 |
| portal/tools/pins.lock.json | 4fb6f3531247c016d1d4d414eb7729988967e254 | b4f60edaae78aef79d6cfb3a2b47211a37315a6b579c6d0b10fcd542e2f13989 | 2021 |
| portal/tools/install-verified-go.sh | 2b6e0c9a0127ac0a641feef791f017d287719543 | 3a34d349b33f032513a21fecd795eeb26129c511c21f3e02f8774b74e7f8d356 | 948 |

### 1.2.1 Что такое «blob» в §1.2 (уточнение R1)

Столбец `blob` — это git object SHA-1 (SHA-1 содержимого файла, 40 hex), **не** SHA коммита.
Значения `blob`/`sha256`/`size` фиксируют содержимое шаблонов и gate-помощников на принятом
source `d22aa8f…`. SHA коммита, который в будущем опубликует
`.github/workflows/p8c-portal-release.yml` (и seed-аналог), на момент подготовки НЕ существует
и будет определён только отдельным решением о публикации workflow. Следовательно, `blob`
шаблона **не равен** и **не предсказывает** SHA будущего коммита публикации workflow.

### 1.2.2 Согласование source checkout и runtime SHA (обязательное условие до dispatch)

Проблема: после публикации workflow новым коммитом в `main`, для `workflow_dispatch`
значение `github.sha` = HEAD `main` = коммит публикации, а **не** pinned source `d22aa8f…`.
Закреплённые шаблоны сейчас используют `ref: ${{ github.sha }}` (release template: строки
48/114; seed template: строки 35/77) и `SOURCE_SHA=${{ github.sha }}`.

Требование до исполнения:

- source checkout в jobs `test`/`release`/`seed` должен быть pinned на литерал
  `d22aa8f1170deaf09580518916ea02c7c4d8bfba` (фиксированный вход), а НЕ на `github.sha`/HEAD main;
- gate связывает `source_sha` с этим литералом, а не с runtime `github.sha`.

Проверка идентичности опубликованных байтов (реальная проверка): перед выдачей gate
сверяются байты опубликованного `.github/workflows/p8c-portal-release.yml` с pinned template
из §1.2, т.е. `sha256(опубликованный файл) == sha256(template)`. Выполняется доверенной
сверкой (`verify-pins.py` или эквивалентной) ДО dispatch.

Ответственный: Архитектор/Owner — единственный, кто выдаёт gate, и только после
подтверждения (а) побайтового совпадения опубликованного workflow с pinned template и
(б) закрепления checkout на литерал `d22aa8f…`.

STOP: если опубликованные байты workflow ≠ sha256 pinned template, ИЛИ checkout/SOURCE_SHA
≠ `d22aa8f…`, ИЛИ любой pinned файл изменился — STOP (gate не выдаётся, dispatch не выполняется).
Если для закрепления checkout на литерал потребуется изменить шаблон — новый blob/sha256
подлежит перезакреплению (§3, инвалидация) и повторному утверждению Архитектором до dispatch.

### 1.3 Внешние pins (pins.lock.json, sha256; tag→SHA не утверждается)

| Компонент | Версия | sha256 |
|---|---|---|
| Go | 1.27.3 | 65efbc80fdc1fa2cd2631cad5b481777a68e8725f34e89f50fc6ac714e379b40 |
| buildkit | v0.34.0 | 14813b1fb2a40082114e6d386c6fc5e7dd5298176ce7ee1a18bc33e73e109ac3 |
| rootlesskit | v2.3.1 | caafdce18e0959f078b4b478d4f352ebf3d556e373265fc7831f1a6d70219ee0 |
| syft | v1.55.0 | bb65249542db5fedeeb4d3f9b018b75e7264dbfbbb10486f044581a92f90490d |
| trivy | v0.76.0 | e24b1c51293c1b15e4ba8d45bbc7891ba053f90278ec2698f3562c993e145fe7 |
| cosign | v3.1.3 | 4629c757b7618056f8ddd7e2625ae9fdd94c0372a65049520bc7d9df9efc7f71 |
| postgres (test service) | 17.10-bookworm | sha256:9b18b78397054fce88a9552e9d5a3ad5bb7fd258c5b3cc1c5028e46373d6ea8f |

Actions (immutable commit SHA; tag-аннотация только справочно):

| Action | SHA | tag (справочно) |
|---|---|---|
| actions/checkout | 11bd71901bbe5b1630ceea73d27597364c9af683 | v4.2.2 |
| actions/upload-artifact | 65462800fd760344b1a7b4382951275a0abb4808 | v4.3.3 |
| docker/login-action | 9780b0c442fbb1117ed29e0efdff1e18412f7567 | v3.3.0 |

### 1.4 Идентичность (OIDC / keyless)

```text
repository:        dedvmedved-dot/otus-diplom
image:             ghcr.io/dedvmedved-dot/otus-diplom-portal@<digest>  (PRIVATE)
workflow file:     .github/workflows/p8c-portal-release.yml (пока НЕ опубликован; публикуется
                   из pinned template после отдельного допуска)
certificate-identity: https://github.com/dedvmedved-dot/otus-diplom/.github/workflows/p8c-portal-release.yml@refs/heads/main
certificate-oidc-issuer: https://token.actions.githubusercontent.com
source binding:    cosign verify -a ref=<source_sha>; provenance.configSource.digest.sha1 == <source_sha>
```

Workflow SHA на момент исполнения — это `GITHUB_WORKFLOW_SHA` опубликованной копии
`.github/workflows/p8c-portal-release.yml`, которая обязана побайтово совпадать с pinned
template (sha256 из §1.2); gate-документ связывается с этим runtime SHA. Runtime SHA
workflow ≠ SHA коммита публикации (см. §1.2.1).

---

## 2. Разрешённые операции в рамках gate

Scope gate ограничен CI-маршрутом release/seed: сборка → проверки → private-реестр →
SBOM/scan/sign/attest → артефакты. **Release и seed — независимые scope с независимыми
допусками** (release-gate и seed first-creation gate выдаются отдельно). Seed —
**необязательный** scope: релиз может выполняться без seed, а seed — только при отдельно
выданном first-creation gate.

### 2.1 Job `test` (permissions: только `contents: read`)

1. `actions/checkout` по pinned SHA, `persist-credentials: false`, `ref=<литерал d22aa8f…>`.
2. Установка проверенного Go-архива (`install-verified-go.sh`, pinned sha256).
3. `go vet ./...`, `go test -count=1 ./...`, `go test -race -count=1 ./...`.
4. DB integration: `go test -tags integration ./internal/store/` против `postgres:17.10-bookworm`
   (loopback), `TEST_DATABASE_URL` обязателен — при отсутствии FAIL.
5. Helper mock-тесты: `test_helpers.py`, `test_release.py`.
6. JS/browser fixture smoke: `npm ci --ignore-scripts`, `renderer-smoke`, `fixture-smoke`,
   `test-dataflow.sh`.
7. `actions/upload-artifact` evidence (при ошибке файлов — error).

### 2.2 Job `release` (permissions: `contents: read` + `packages: write` + `id-token: write`)

1. Проверка чистого дерева + provenance: `git diff --exit-code`, запись `SOURCE_SHA`/`BUILD_TIME`.
2. Доставка типизированного release gate (данные через env, никогда shell-интерполяция).
3. Admission gate: `release-check.py release-gate` (binding source/repository/package/workflow/
   expiry/attempt — см. §5).
4. Установка проверенного Go.
5. Private-package prerequisite ДО push: `release-check.py private` → `private-before.json`.
6. Сборка бинарника: `CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -trimpath`
   (`-X main.sourceRevision=<sha>`, `buildTime=1970-01-01T00:00:00Z` — воспроизводимо).
7. Установка rootlesskit + BuildKit (pinned sha256); `unshare -Ur` guard.
8. `docker/login-action` к GHCR (github.actor + GITHUB_TOKEN).
9. Сборка OCI через rootless `buildctl` (bounded readiness 30×(timeout5+sleep1)) + immutable
   digest из `build-metadata.json`; push только `candidate`-тега.
10. Проверка registry bytes + private visibility ПОСЛЕ push: `release-check.py registry`,
    `release-check.py private` → `registry.json` / `private-after.json`.
11. SBOM (syft, spdx-json) + vuln scan (trivy `--exit-code 1 --severity HIGH,CRITICAL`) по
    бинарнику и по образу.
12. Keyless sign + verify (`cosign sign/verify` с `-a ref=<sha>`), attest SBOM+provenance +
    `cosign verify-attestation`; итог `release-check.py verified` (payload-binding).
13. `actions/upload-artifact` (SBOM/signature/provenance).
14. Cleanup buildkit-демона `if: always()`.

### 2.3 Job `seed` (независимый НЕОБЯЗАТЕЛЬНЫЙ one-shot bootstrap; seed ≠ release, НЕ deployable)

Seed — отдельный scope с собственным допуском (first-creation gate, §5). Необязателен:
отсутствие seed-допуска означает «seed не выполняется» (bootstrap НЕ разрешён) и НЕ блокирует
release-scope.

1. Типизированный precheck `private` → REUSE | CREATE_ALLOWED | STOP (typed job output).
2. REUSE и STOP выполняют НОЛЬ build/push.
3. CREATE_ALLOWED только по корректному first-creation gate (см. §5) + `GITHUB_RUN_ATTEMPT=1`.
4. Минимальный not-deployable seed (`Seed.Containerfile`) → `seed-<sha>` тег; digest отличен от
   application digest (если application digest известен — см. §4.4).

Ответственный за scope-разделение: gate-проверки `release-check.py` (release-gate vs
first-creation) + ревью Архитектора/Owner-а. STOP: если seed-допуск отсутствует, а bootstrap
пытается выполниться, либо seed-scope затрагивает release-scope (или наоборот) — STOP.

### 2.4 Scope-границы и явные запреты

Публикация разрешена ТОЛЬКО в PRIVATE GHCR и только двумя тегами, каждый в своём независимом scope:

- release scope → тег `candidate` (immutable digest из `build-metadata.json`);
- seed scope → тег `seed-<sha>` (только при CREATE_ALLOWED по first-creation gate).

Любой иной тег/публикация запрещены. Явно ЗАПРЕЩЕНО:

- Deployment / promote / публикация любым тегом, кроме двух выше, и вне PRIVATE GHCR.
- NetworkPolicy apply, live-readiness, любые reads/writes в кластер ПАК.
- Public package / публичный реестр; любые PAK-секреты или kubeconfig.
- Automatic retry / повторный run / force-push / изменение pinned source после issued gate.
- Bootstrap seed при отсутствии отдельного seed-допуска (first-creation gate).

---

## 3. Одноразовый бюджет (scope + лимиты запуска)

Запуск — однократный, ручной, без авто-повторов. Лимиты разделены на **ОБЕСПЕЧЕННЫЕ**
(реально закреплены в pinned workflow/source) и **ПРЕДЛОЖЕННЫЕ** (заявлены в спецификации,
но механизм enforcement ещё не доказан и требует отдельного решения/доработки до dispatch).

### 3.1 Обеспеченные лимиты (закреплены в pinned шаблонах/коде)

| Параметр | Значение | Где закреплено |
|---|---|---|
| job `test` timeout | 20m (hard) | release template L33 |
| job `release` timeout | 30m (hard) | release template L102 |
| job `seed` precheck timeout | 5m (hard) | seed template L28 |
| job `seed` timeout | 15m (hard) | seed template L69 |
| auto-retry | НЕТ (retry/concurrency-повтор в шаблонах отсутствует) | шаблоны |
| gate expiry | 24h, `0 < expiry_hours <= 24`, `issued_at_utc` не будущее и не истёкшее | release-check.py (release-gate и first-creation) |
| инвалидация | байтовое изменение любого pinned файла → pin недействителен | определение (§1) |

### 3.2 Предложенные лимиты (требуют доказательства одноразовости ДО dispatch)

| Параметр | Заявленное значение | Статус enforcement |
|---|---|---|
| единица бюджета | ровно 1 (один) авторизованный `workflow_dispatch` = один issued gate-документ | ПРЕДЛОЖЕНО — механизм не реализован |
| max runs | 1 | ПРЕДЛОЖЕНО |
| run_attempt / attempt | `run_attempt = 1` И `attempt = 1` (строгий тип: int, не bool, ==1) | ЧАСТИЧНО: seed (first-creation) строго; release — НЕТ строгой проверки типа (см. §5) |
| погашение при любом исходе | единица расходуется на dispatch, включая неудачу | ПРЕДЛОЖЕНО — не реализовано (нет внешнего учёта) |

### 3.3 Единица бюджета и владелец учёта/погашения

- **Единица бюджета**: ровно один авторизованный `workflow_dispatch` (один issued gate-документ
  = одна единица).
- **Расходование**: единица считается израсходованной в момент dispatch, НЕЗАВИСИМО от исхода —
  успех ИЛИ неудача (неудачный run НЕ возвращает единицу).
- **Владелец учёта/погашения**: Архитектор/Owner (единственный issuer gate). Владелец фиксирует
  выдачу единицы ДО dispatch и отмечает её погашенной при любом исходе.
- **Ответственный за фиксацию**: Архитектор/Owner.

STOP: до доказательства одноразовости — пока (а) не определён владелец учёта/погашения,
(б) не подтверждена строгая проверка attempt для release (выравнена с seed: int, не bool, ==1,
см. §5) и (в) не обеспечено погашение единицы при любом исходе — dispatch НЕ выдаётся (STOP).

---

## 4. Возвращаемые артефакты (и как проверяются)

### 4.1 Образ

`ghcr.io/dedvmedved-dot/otus-diplom-portal@<digest>` — private, `candidate` tag.
Проверка: `release-check.py digest` (digest из build-metadata) + `registry` (manifestVerified,
image/digest binding) + `private` (visibility=private, repository binding).

### 4.2 Artifact `portal-source-tests` (job test)

`go-version.txt`, `vet.txt`, `unit.txt`, `race.txt`, `integration.txt`, `helpers.txt`,
`release-checks.txt`, `node-version.txt`, `renderer.txt`, `fixtures.txt`, `dataflow.txt`.
Проверка: наличие (upload `if-no-files-found: error`) + zero-failure exit на каждом шаге.

### 4.3 Artifact `portal-sbom-signature-provenance` (job release)

`build-metadata.json`, `private-before.json`, `registry.json`, `private-after.json`,
`sbom.spdx.json`, `scan-binary.json`, `scan-image.json`, `sign.txt`, `signature.json`,
`provenance.json`, `attest-sbom.txt`, `attest-provenance.txt`, `attestation-sbom.jsonl`,
`attestation-provenance.jsonl`, `verification.json`, `go-version.txt`, `go-binary.sha256`.

Проверка — строгий payload-binding (`release-check.py verified`), не `size>0`:

- `build-metadata.json` — valid JSON, `containerimage.digest == <ожидаемый digest>`.
- `scan-binary.json` / `scan-image.json` — valid JSON, форма `Results[]`, нет HIGH/CRITICAL;
  `scan-image` ссылается на `IMAGE@<digest>`.
- `registry.json` — `image == IMAGE`, `digest == <digest>`, `manifestVerified == true`.
- `private-before.json` / `private-after.json` — `visibility == private`, `repository == REPO`.
- `sbom.spdx.json` — valid JSON со `spdxVersion`.
- `provenance.json` — `builder.id == <workflow identity>`,
  `invocation.configSource.digest.sha1 == <source_sha>`.
- `signature.json` / `attestation-*.jsonl` — cosign verify/verify-attestation с identity,
  OIDC issuer и `-a ref=<source_sha>`.

### 4.4 Artifact `portal-seed-evidence` (job seed) — состав зависит от исхода

Состав пакета НЕ единый: seed template (строки 173–177) собирает только СУЩЕСТВУЮЩИЕ файлы
(`if [ -f … ]`), поэтому набор артефактов определяется исходом seed:

| Исход seed | Фактически собираемые файлы | Проверка |
|---|---|---|
| CREATE_ALLOWED (bootstrap выполнен) | `seed-evidence.json`, `seed-registry.json`, `private.json`, `private-after.json`, `seed-metadata.json`, `seed-digest.txt`, `first-creation-gate.json` (+ `MANIFEST.txt`) | `seed_digest` зафиксирован; `not_deployable=true`; registry/private binding (аналогично §4.3); `seed_digest != application_digest` ТОЛЬКО если application digest известен |
| REUSE (существующий seed переиспользован, НОЛЬ build/push) | reuse-решение + ссылка на существующий digest + registry/private binding; НЕТ нового digest/metadata | новый digest отсутствует (не требуется); НЕ трактуется как доказательство различия |
| STOP (gate отклонён / нет допуска) | только причина STOP (вывод отклонения + nonzero exit); НОЛЬ build/push | фиксируется причина отклонения; артефактов сборки нет |

Уточнение `seed_digest != application_digest`: сравнение доказуемо ТОЛЬКО когда application
digest известен (release уже выполнен и вернул digest). Если application digest
неизвестен/отсутствует — это отдельное состояние «неприменимо/неизвестно», а НЕ доказательство
различия; отсутствие известного application digest НЕ трактуется как прохождение проверки.

Ответственный: `release-check.py` (first-creation/seed-проверки) + ревью Архитектора/Owner-а
итогового пакета. STOP: при CREATE_ALLOWED, если `seed_digest` зафиксировать не удалось, ИЛИ
(при известном application digest) `seed_digest == application_digest` — STOP.

---

## 5. Gate-документ (admission control)

До protected операций обязателен типизированный gate-документ (release-gate), все поля
связаны с фактическим run; отсутствие/несовпадение → nonzero, НЕ пропуск:

```text
release-gate {
  source_sha    == <pinned литерал d22aa8f…>                     (40 hex; НЕ runtime github.sha — см. §1.2.2)
  repository    == dedvmedved-dot/otus-diplom
  package       == ghcr.io/dedvmedved-dot/otus-diplom-portal
  workflow_sha  == <GITHUB_WORKFLOW_SHA> (40 hex, actual)   (недостаток runtime binding = НЕ авторизация)
  mode          == LIVE                                     (TEST_ONLY rejected)
  issued_at_utc == уже наступившее, не будущее, не истёкшее
  expiry_hours  : int, 0 < expiry_hours <= 24
  attempt       == 1  И  run_attempt == 1
}
```

Точное поведение enforcement (по фактическому коду `release-check.py`):

- **release-gate** (строки 148–151): проверка `g['attempt'] != 1 or str(run_attempt) != '1'` —
  отклоняет отсутствие/2/строку, НО НЕ отклоняет строго не-int типы (`True`/`1.0` проходят как
  `== 1`). Строгая проверка «int, не bool, ==1» для release НЕ обеспечена.
- **seed first-creation**: `isinstance(attempt, int) and not bool and attempt == 1` +
  `GITHUB_RUN_ATTEMPT == '1'` — строго; отсутствие/строка/bool/2 отклоняются.

Следовательно, строгий attempt-тип для release — ПРЕДЛОЖЕННЫЙ лимит (hardening
`release-check.py` release-gate), НЕ обеспеченный; до его внедрения и подтверждения — STOP
(см. §3.3).

Seed first-creation gate — отдельный, независимый от release-gate документ: тот же набор
обязательных полей + строгая привязка attempt (`int`, не bool, ==1) и `GITHUB_RUN_ATTEMPT=1`;
только `mode=LIVE`.

---

## 6. Итоговый статус

```text
PREPARATION = COMPLETE (REVIEW_READY, offline)
EXECUTION    = NOT_AUTHORIZED
```

Подготовка спецификации завершена (R1 — исправления по четырём пунктам вердикта #2).
Допуск на исполнение gate НЕ выдан. Жду решения Архитектора (STAGE P8C: PASSED + PROCEED)
перед публикацией workflow и любым CI-run. Source-этап не переоткрывается; публикация/dispatch
workflow, build/push/sign/attest, live-readiness, NetworkPolicy apply, deployment и P8D+ —
НЕ выполняются. P8C = NOT_FINAL_ACCEPTED.
