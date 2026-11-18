# P8C CI Release Gate — спецификация (ПОДГОТОВКА, НЕ ИСПОЛНЕНИЕ)

Дата: 2026-11-18, Europe/Moscow. Исполнитель подготовки: PRIMARY HERMES (engineer,
assignee `hermes-5.187.1.37-engineer`). Тип документа: спецификация gate (AUTHOR_PROPOSAL),
НЕ допуск на исполнение.

Статусные строки:

```text
CI_RELEASE_GATE_SPEC = REVIEW_READY (AUTHOR_PROPOSAL, не ARCHITECT_ACCEPTED)
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
template (sha256 из §1.2); gate-документ связывается с этим runtime SHA.

---

## 2. Разрешённые операции в рамках gate

Scope gate ограничен CI-маршрутом release/seed: сборка → проверки → private-реестр →
SBOM/scan/sign/attest → артефакты. Разрешено строго следующее (A→B→C, без расширения):

### 2.1 Job `test` (permissions: только `contents: read`)

1. `actions/checkout` по pinned SHA, `persist-credentials: false`, `ref=${{ github.sha }}`.
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

### 2.3 Job `seed` (отдельный one-shot bootstrap; seed ≠ release, НЕ deployable)

1. Типизированный precheck `private` → REUSE | CREATE_ALLOWED | STOP (typed job output).
2. REUSE и STOP выполняют НОЛЬ build/push.
3. CREATE_ALLOWED только по корректному first-creation gate (см. §5) + `GITHUB_RUN_ATTEMPT=1`.
4. Минимальный not-deployable seed (`Seed.Containerfile`) → `seed-<sha>` тег; digest отличен от
   application digest (иначе STOP).

### 2.4 Явно ЗАПРЕЩЕНО (не входит в scope gate)

- Deployment / promote / любая публикация, кроме `candidate`-тега в PRIVATE GHCR.
- NetworkPolicy apply, live-readiness, любые reads/writes в кластер ПАК.
- Public package / публичный реестр; любые PAK-секреты или kubeconfig.
- Automatic retry / повторный run / force-push / изменение pinned source после issued gate.

---

## 3. Одноразовый бюджет (scope + лимиты запуска)

Запуск — однократный, ручной, без авто-повторов. Числа ниже — лимиты gate; enforcement
реализован в закреплённом workflow/source, исполнение — после отдельного допуска.

| Параметр | Значение |
|---|---|
| job `test` timeout | 20m (hard) |
| job `release` timeout | 30m (hard) |
| job `seed` precheck timeout | 5m (hard) |
| job `seed` timeout | 15m (hard) |
| max runs | 1 (manual `workflow_dispatch`) |
| run attempt | `run_attempt = 1` и gate `attempt = 1` (integer) — иначе reject |
| auto-retry | НЕТ |
| gate expiry | 24 часа (`expiry_hours` int, `0 < expiry_hours <= 24`) от `issued_at_utc` (не будущее, уже наступившее) |
| инвалидация | байтовое изменение любого pinned source/workflow файла → pin недействителен |

Условие допуска: gate-документ issued Архитектором/Owner-ом (никогда не материализуется
«сам собой»; доставляется как `workflow_dispatch.inputs.release_gate` → файл через env).

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

### 4.4 Artifact `portal-seed-evidence` (job seed)

`seed-evidence.json`, `seed-registry.json`, `private.json`, `private-after.json`,
`seed-metadata.json`, `seed-digest.txt`, `first-creation-gate.json`, `MANIFEST.txt`.
Проверка: `seed_digest` зафиксирован, `not_deployable=true`, `seed_digest != application_digest`,
registry/private binding (аналогично §4.3).

---

## 5. Gate-документ (admission control)

До protected операций обязателен типизированный gate-документ (release-gate), все поля
связаны с фактическим run; отсутствие/несовпадение → nonzero, НЕ пропуск:

```text
release-gate {
  source_sha    == <runtime github.sha>                     (40 hex)
  repository    == dedvmedved-dot/otus-diplom
  package       == ghcr.io/dedvmedved-dot/otus-diplom-portal
  workflow_sha  == <GITHUB_WORKFLOW_SHA> (40 hex, actual)   (недостаток runtime binding = НЕ авторизация)
  mode          == LIVE                                     (TEST_ONLY rejected)
  issued_at_utc == уже наступившее, не будущее, не истёкшее
  expiry_hours  : int, 0 < expiry_hours <= 24
  attempt       == 1 (integer)  И  run_attempt == 1         (missing/null/bool/2 rejected)
}
```

Seed first-creation gate — тот же набор обязательных полей + binding к `GITHUB_SHA` /
repository / package / workflow_sha; только `mode=LIVE`, `GITHUB_RUN_ATTEMPT=1`.

---

## 6. Итоговый статус

```text
PREPARATION = COMPLETE (REVIEW_READY, offline)
EXECUTION    = NOT_AUTHORIZED
```

Подготовка спецификации завершена; допуск на исполнение gate НЕ выдан. Жду решения
Архитектора (STAGE P8C: PASSED + PROCEED) перед публикацией workflow и любым CI-run.
