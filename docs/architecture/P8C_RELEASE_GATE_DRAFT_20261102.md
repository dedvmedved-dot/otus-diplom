# P8C Release Gate — DRAFT (NOT_AUTHORIZED_FOR_EXECUTION)

Дата: 2026-11-03. Исполнитель подготовки: PRIMARY HERMES. Status: DRAFT.

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

## 2. Полная таблица pins (точный upstream источник + checksum)

| Компонент | Exact asset / identity | Ref/checksum | Статус |
|---|---|---|---|
| Go archive | https://go.dev/dl/go1.27.3.linux-amd64.tar.gz | sha256 65efbc80fdc1fa2cd2631cad5b481777a68e8725f34e89f50fc6ac714e379b40 | UNVERIFIED (independent) |
| buildkit | https://github.com/moby/buildkit/releases/download/v0.34.0/buildkit-v0.34.0.linux-amd64.tar.gz | sha256 14813b1fb2a40082114e6d386c6fc5e7dd5298176ce7ee1a18bc33e73e109ac3 | UNVERIFIED |
| rootlesskit | https://github.com/rootless-containers/rootlesskit/releases/download/v2.3.1/rootlesskit-x86_64.tar.gz | sha256 caafdce18e0959f078b4b478d4f352ebf3d556e373265fc7831f1a6d70219ee0 | UNVERIFIED |
| syft | https://github.com/anchore/syft/releases/download/v1.55.0/syft_1.55.0_linux_amd64.tar.gz | sha256 bb65249542db5fedeeb4d3f9b018b75e7264dbfbbb10486f044581a92f90490d | UNVERIFIED |
| trivy | https://github.com/aquasecurity/trivy/releases/download/v0.76.0/trivy_0.76.0_Linux-64bit.tar.gz | sha256 e24b1c51293c1b15e4ba8d45bbc7891ba053f90278ec2698f3562c993e145fe7 | UNVERIFIED |
| cosign | https://github.com/sigstore/cosign/releases/download/v3.1.3/cosign-linux-amd64 | sha256 4629c757b7618056f8ddd7e2625ae9fdd94c0372a65049520bc7d9df9efc7f71 | UNVERIFIED |
| postgres (test svc) | docker.io/library/postgres:17.10-bookworm | @sha256:9b18b78397054fce88a9552e9d5a3ad5bb7fd258c5b3cc1c5028e46373d6ea8f | переиспользован |
| actions/checkout | github.com/actions/checkout | 11bd71901bbe5b1630ceea73d27597364c9af683 (tag v4.2.2 — НЕ утверждать tag→SHA verified) | UNVERIFIED |
| actions/upload-artifact | github.com/actions/upload-artifact | 65462800fd760344b1a7b4382951275a0abb4808 (v4.3.3) | UNVERIFIED |
| docker/login-action | github.com/docker/login-action | 9780b0c442fbb1117ed29e0efdff1e18412f7567 (v3.3.0) | UNVERIFIED |

Authoritative pin — SHA (commit/digest), не tag-annotation. UNVERIFIED = независимого proof в этом
задании нет; не перескачивать, не обновлять «до последних».

## 3. Identity / OIDC / artifacts (literal)

```text
repository: dedvmedved-dot/otus-diplom
workflow file: .github/workflows/p8c-portal-release.yml  (NOT published yet)
ref: refs/heads/main
OIDC issuer: https://token.actions.githubusercontent.com
certificate-identity: https://github.com/dedvmedved-dot/otus-diplom/.github/workflows/p8c-portal-release.yml@refs/heads/main
source binding: cosign verify -a ref=${{ github.sha }}
image: ghcr.io/dedvmedved-dot/otus-diplom-portal@<digest>  (digest = release-check.py digest из build-metadata.json)
artifacts: portal-source-tests, portal-sbom-signature-provenance
```

## 4. Bootstrap — private-before

Package existence НЕ доказан. **BOOTSTRAP_METHOD=UNRESOLVED**: точный вариант будущего отдельного
bootstrap-пакета требует решения Owner/Architect по (a) механизму первого private upload/repository
association для `ghcr.io/dedvmedved-dot/otus-diplom-portal`, (b) identity/artifact/visibility binding,
(c) способу private-before подтверждения до основного run. Не ослаблять private-before, не «первый
публичный push». Никакого фактического seed/push/settings mutation сейчас.

## 5. Run budget (численный, draft)

```text
test job timeout: 20m (hard)
release job timeout: 30m (hard)
max runs per workflow: 1 (single manual dispatch; no retry loop)
retry: NO automatic retry; любой FAIL → ручной разбор
wall-clock expiry: допуск истекает при изменении source/byte или по завершении одного approved run
source-change invalidation: любой byte change в template/helpers → pin недействителен, повторная сверка
enforcement: эти числа ещё НЕ реализованы в unchanged template (обозначить как будущий job-level timeout)
```

## 6. Статус
```text
RELEASE_TEMPLATE_CHANGED=NO (byte-identical)
RELEASE_GATE_DRAFT=REVIEW_READY (DRAFT)
CI_RELEASE=NOT_EXECUTED
```
