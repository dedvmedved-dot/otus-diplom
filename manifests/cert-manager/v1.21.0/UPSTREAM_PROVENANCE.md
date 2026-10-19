# cert-manager 1.21.0 — Upstream Provenance

- repository: github.com/cert-manager/cert-manager
- tag: v1.21.0
- commit: b8f325e36f49626ba72d7efbe138c01a5e661d96
- release date: 2026-07-08

## Release assets (hash verified)
- cert-manager.yaml: sha256:6e499c3f1ab356abe79a7853911f80cb09c213885bfdf81092fdff142ba63c4a
- cert-manager.crds.yaml: sha256:cc046deb0ef4aaa8237f1ae448ef463446905bfc310cba88f25fc614389f84fd

Both match the GitHub-published asset digests.

## Images (linux/amd64)
- controller: sha256:79a65ab008da7f067d6f68be937ba60d1d8a174168f66b6530c5ed0927c69986
- webhook: sha256:af0a4f097872194799c07e24eda4561ade538fcee1d531d7ff824eeb297b0ae5
- cainjector: sha256:d4962457c0c6b7a1399bdc84bd2748070353b5170bf856f697f09b239187b74a
- acmesolver: sha256:6198cb796023163a6726589d3f9dbe76bb76289fea8c948ea6feb36e4617122c

## Signature / SBOM
Official release asset provenance + immutable digests. No unresolved CRITICAL
identified. Kubernetes compatibility: chart metadata allows >=1.22 (no upper
bound); runtime compatibility validated against 1.36.2 API server via server
dry-run (CERT_MANAGER_K8S_136_SERVER_COMPAT).
