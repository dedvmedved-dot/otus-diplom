# CloudNativePG 1.30.1 — Upstream Provenance

## Source
- repository: github.com/cloudnative-pg/cloudnative-pg
- tag: v1.30.1
- commit: 2a35abb4628f209d149825ef3c38011e0701ff2f
- release date: 2026-09-23

## Release asset
- asset: cnpg-1.30.1.yaml
- sha256: 37237f145d8138256ea25ae830f87759255665ff08f8d552fdd8224a5ec032fb (matches GitHub-published digest)

## Signature verification (cosign v3.1.3)
- manifest (cnpg-1.30.1.yaml) sigstore bundle: Verified OK
- operator image (ghcr.io/cloudnative-pg/cloudnative-pg:1.30.1): cosign verified (keyless; docker-manifest-digest sha256:923c267ec29636db3bee20f993d0ec4973fa22998e1adad37da79e4d32b5bc07)
- operand image (ghcr.io/cloudnative-pg/postgresql:17.10-system-trixie): cosign verified (keyless; docker-manifest-digest sha256:74f29d3343f8db89135b33b0b4c55641c415b96d08605034a6d0c2782f929146)

## Image digests (linux/amd64)
- operator: sha256:b0f9805bd5f98592e7320b5ea624dd10a7a6ef8e477df5650655c94f0b242497
- PostgreSQL 17.10 operand: sha256:ba9e496920d2baeffa6e383a72e66b90af336e2d67990a68e6216f34e25e4515

## SBOM / provenance availability
- SLSA provenance: multiple.intoto.jsonl (release asset)
- sigstore bundles: cnpg-1.30.1.sigstore.json, per-asset .sbom.json (kubectl-cnpg)
- no CRITICAL vulnerability identified; images are official signed CNPG releases

## Compatibility (official docs, supported_releases.md @ v1.30.1)
- 1.30.x: supported Kubernetes 1.34, 1.35, 1.36 (EOL ~Dec 2026)
- 1.29.x: supported Kubernetes 1.33, 1.34, 1.35 (EOL 2026-09-29)
