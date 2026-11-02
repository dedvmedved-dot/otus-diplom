# P8C Release Gate — DRAFT (NOT_AUTHORIZED_FOR_EXECUTION)

Дата: 2026-11-02. Исполнитель подготовки: PRIMARY HERMES. Status: DRAFT.
Source: portal/tools/p8c-portal-release.yml.template (+ install-verified-go.sh, release-check.py, test_release.py).

```text
RELEASE_GATE=NOT_AUTHORIZED_FOR_EXECUTION
CI_RELEASE / WORKFLOW_PUBLICATION / WORKFLOW_DISPATCH = NOT_AUTHORIZED
```

## 1. Сопоставление template → будущий процесс (requirement → step/helper → proof)

| Requirement | Step/helper (template) | Offline proof (source read) | CI-only proof (NOT_EXECUTED) |
|---|---|---|---|
| source SHA привязка | `git diff --exit-code` + `SOURCE_SHA=${{github.sha}}` | template строка | checkout ref=sha; run output |
| test job → verified Go | `install-verified-go.sh` (GO_VERSION 1.27.3 + GO_SHA256 65efbc80…) | pin в template; archive checksum в helper | runner go version + sha256 |
| go vet/test/race | `go vet`, `go test`, `go test -race` | — | run artifacts (vet.txt/unit.txt/race.txt) |
| DB integration (isolated postgres:17) | postgres:17.10-bookworm@sha256:9b18b783… | pin в template | integration.txt; FAIL if TEST_DATABASE_URL unset |
| binary → один OCI build | `go build -trimpath` (CGO_ENABLED=0, ldflags sourceRevision/buildTime) + rootless buildctl | buildctl/rootlesskit pins + sha256 | build-metadata.json |
| immutable digest | `release-check.py digest` из metadata-file | source-level read | IMAGE_DIGEST |
| SBOM + vuln scan | syft spdx + trivy fs/image (`--exit-code 1 --severity HIGH,CRITICAL`) | syft/trivy pins + sha256 | sbom.spdx.json / scan-*.json |
| signature + attestations | cosign sign/attest + verify-attestation (OIDC identity/issuer) | cosign pin + identity/issuer literal | signature.json / attestation-*.jsonl |
| repo/ref/workflow/OIDC/source/digest binding | cosign verify `-a ref=${{github.sha}}` + certificate-identity workflow path | literal in template | verification.json |
| private package до/после push | `release-check.py private` (before + after) | source-level read | private-before/after.json |
| permissions | test: contents:read; release: contents:read + packages:write + id-token:write | template literal | — |
| artifacts + FAIL on missing | upload-artifact `if-no-files-found: error`; каждый step `set -euo pipefail` | template literal | — |
| no promotion/deploy | template не содержит deploy/promote; только candidate:tag push | template literal | — |

## 2. Bootstrap-зависимость (private-before требует существующий private package)
`release-check.py private` ДО push требует уже существующий private package (visibility/binding), но
это первый релиз. Не обходится «первым публичным push». Ожидаемый порядок: Owner/Architect создаёт
private GHCR package-пустой/seed и выдаёт минимальный `packages:write` только release-job, затем
`private`-check проверяет именно этот pre-existing package. Это **BLOCKED_EXTERNAL** до Owner-действия.
Точный prerequisite зафиксирован в §4. Без него CI release не запускается.

## 3. Pins / UNVERIFIED
Все tool-версии и checksums в template повторно используются как provenance, НЕ обновляются «до
последних». Независимой offline-проверки каждого checksum в этом задании нет → отмечены UNVERIFIED;
источник для будущей проверки — точный URL+version+sha256 в template (syft/trivy/cosign/rootlesskit/
buildkit/go). Supply-chain PASS не объявляется. Принятые ранее pins переиспользуются.

## 4. Внешние условия (Owner/Architect prerequisite) и run budget
```text
RELEASE_GATE_RUN_BUDGET=DRAFT (run budget не выделен; dispatch требует отдельного допуска)
EXTERNAL_PREREQUISITES:
  1. Owner создаёт private GHCR package + пакетный seed (иначе private-before fails).
  2. Owner публикует template в .github/workflows через GitHub UI ПОСЛЕ приёмки (не dispatch сейчас).
  3. Независимая сверка tool checksums (UNVERIFIED → VERIFIED) до первого run.
  4. Owner предоставляет единственный secrets.GITHUB_TOKEN usage scope (без PAK credentials).
DISPATCH=PUBLICATION+dispatch только отдельным допуском; НЕ этим заданием.
```

## 5. Статус
```text
RELEASE_TEMPLATE_CHANGED=NO (изменения release-кода не потребовались)
RELEASE_GATE_DRAFT=REVIEW_READY (DRAFT, offline preparation only)
CI_RELEASE=NOT_EXECUTED
```
