# P8C Release Gate — DRAFT (NOT_AUTHORIZED_FOR_EXECUTION)

Дата: 2026-11-02. Исполнитель подготовки: PRIMARY HERMES. Status: DRAFT.
Source: portal/tools/p8c-portal-release.yml.template (+ install-verified-go.sh, release-check.py, test_release.py).

```text
RELEASE_GATE=NOT_AUTHORIZED_FOR_EXECUTION
CI_RELEASE / WORKFLOW_PUBLICATION / WORKFLOW_DISPATCH = NOT_AUTHORIZED
```

## 1. Manifest (path → blob → SHA-256)

| Path | blob | sha256 |
|---|---|---|
| portal/tools/p8c-portal-release.yml.template | 0e713e47f7f7a9e940b3113a7481e393aa961f9e | 7f28c5c9d8b919cdb22f1e94548820357018dbea20b7010e266b6f5089b9c98f |
| portal/tools/install-verified-go.sh | 2b6e0c9a0127ac0a641feef791f017d287719543 | 3a34d349b33f032513a21fecd795eeb26129c511c21f3e02f8774b74e7f8d356 |
| portal/tools/release-check.py | 88598da050c07c6475ebcafb793876567c730e87 | 48ba1486de53729f9c24ad0a97d40ecd1f9870c67e61315e56b038f631451ef6 |
| portal/tools/test_release.py | cf31c99d9e9d152c8b267007744e19444f7debe9 | 5ae16c313c3778879333a56db3f71639889d2646ded7b6df5909e0a69d6a4654 |

## 2. Полная таблица pins (tool / action / image)

| Компонент | Version/ref | Digest/checksum | Источник | Статус |
|---|---|---|---|---|
| Go archive | 1.27.3 | sha256 65efbc80fdc1fa2cd2631cad5b481777a68e8725f34e89f50fc6ac714e379b40 | install-verified-go.sh | переиспользован; UNVERIFIED здесь |
| buildkit | v0.34.0 | sha256 14813b1fb2a40082114e6d386c6fc5e7dd5298176ce7ee1a18bc33e73e109ac3 | template | UNVERIFIED |
| rootlesskit | 2.3.1 | sha256 caafdce18e0959f078b4b478d4f352ebf3d556e373265fc7831f1a6d70219ee0 | template | UNVERIFIED |
| syft | 1.55.0 | sha256 bb65249542db5fedeeb4d3f9b018b75e7264dbfbbb10486f044581a92f90490d | template | UNVERIFIED |
| trivy | 0.76.0 | sha256 e24b1c51293c1b15e4ba8d45bbc7891ba053f90278ec2698f3562c993e145fe7 | template | UNVERIFIED |
| cosign | 3.1.3 | sha256 4629c757b7618056f8ddd7e2625ae9fdd94c0372a65049520bc7d9df9efc7f71 | template | UNVERIFIED |
| postgres (test service) | postgres:17.10-bookworm | @sha256:9b18b78397054fce88a9552e9d5a3ad5bb7fd258c5b3cc1c5028e46373d6ea8f | template | переиспользован |
| actions/checkout | 11bd71901bbe5b1630ceea73d27597364c9af683 | v4.2.2 | template | UNVERIFIED |
| actions/upload-artifact | 65462800fd760344b1a7b4382951275a0abb4808 | v4.3.3 | template | UNVERIFIED |
| docker/login-action | 9780b0c442fbb1117ed29e0efdff1e18412f7567 | v3.3.0 | template | UNVERIFIED |

UNVERIFIED = независимая offline-проверка checksum в этом задании не выполнялась; точный источник для
будущей проверки — URL+version+sha256 (см. template). Не обновлять версии, не перескачивать.

## 3. Сопоставление template → будущий процесс (requirement → step/helper → proof)

| Requirement | Step/helper | Offline proof (source read) | CI-only proof (NOT_EXECUTED) |
|---|---|---|---|
| source SHA привязка | `git diff --exit-code` + `SOURCE_SHA=${{github.sha}}` | template | checkout ref=sha + output |
| verified Go | install-verified-go.sh | pin + helper sha256 | go version + archive sha256 |
| go vet/test/race | go vet/test/-race | — | vet.txt/unit.txt/race.txt |
| DB integration | postgres:17.10 service, FAIL if TEST_DATABASE_URL unset | pin | integration.txt |
| binary → OCI | go build -trimpath + rootless buildctl | pins | build-metadata.json |
| immutable digest | release-check.py digest | source | IMAGE_DIGEST |
| SBOM + vuln scan | syft/trivy (--exit-code 1 HIGH,CRITICAL) | pins | sbom/scan-*.json |
| signature + attestations | cosign sign/attest/verify-attestation | pin + identity literal | signature/attestation-*.jsonl |
| identity/source/digest binding | cosign verify `-a ref` + certificate-identity workflow@refs/heads/main | literal | verification.json |
| private package до/после push | release-check.py private (before+after) | source | private-before/after.json |
| permissions | test contents:read; release contents:read + packages:write + id-token:write | template | — |
| FAIL on missing | upload-artifact if-no-files-found:error; set -euo pipefail | template | — |
| no promote/deploy | candidate:tag push only, нет deploy steps | template | — |

## 4. Bootstrap (private-before) и permissions — исправлено

- **GITHUB_TOKEN**: job token автоматически выдаёт GitHub Actions (`secrets.GITHUB_TOKEN`),
  используемый внутри workflow; Owner НЕ передаёт значение токена. Owner обеспечивает разрешённые
  workflow/package settings и publication (reference: https://docs.github.com/en/actions/concepts/security/github_token,
  проверено 2026-11-02). Owner publication и manual dispatch разделены; оба сейчас запрещены.
- **Bootstrap private-before**: package existence сейчас НЕ доказан. Конкретный bootstrap-вариант:
  отдельный будущий допуск, который (a) создаёт private GHCR package/seed с точными identity/artifact/
  visibility/repository binding, (b) проверяет его read-only ДО основного run, (c) после этого
  `release-check.py private` (before) подтверждает pre-existing package. Не ослаблять private-before,
  не «первый публичный push». До этого — BLOCKED_EXTERNAL.

## 5. Run budget (draft, не grant)

```text
RUN_BUDGET=DRAFT (run не выделен)
timeout: per-job hard deadline (не задан здесь, определяется execute-gate)
retry: без retry по умолчанию; источник/byte change инвалидирует будущий pin
expiry: допуск истекает при изменении source/byte или по завершении одного approved run
```

## 6. Статус
```text
RELEASE_TEMPLATE_CHANGED=NO (byte-identical; дефектов release-кода не воспроизведено)
RELEASE_GATE_DRAFT=REVIEW_READY (DRAFT)
CI_RELEASE=NOT_EXECUTED
```
