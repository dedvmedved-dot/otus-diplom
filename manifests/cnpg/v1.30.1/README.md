# CloudNativePG 1.30.1 (digest-pinned)

## Images (digest-pinned)
- operator: ghcr.io/cloudnative-pg/cloudnative-pg@sha256:b0f9805bd5f98592e7320b5ea624dd10a7a6ef8e477df5650655c94f0b242497 (linux/amd64)
- operator index digest: sha256:923c267ec29636db3bee20f993d0ec4973fa22998e1adad37da79e4d32b5bc07

## PostgreSQL operand
- image: ghcr.io/cloudnative-pg/postgresql:17.10-system-trixie
- amd64 digest: sha256:ba9e496920d2baeffa6e383a72e66b90af336e2d67990a68e6216f34e25e4515
- index digest: sha256:74f29d3343f8db89135b33b0b4c55641c415b96d08605034a6d0c2782f929146

## Compatibility (verified against official CNPG docs)
- Kubernetes 1.34 / 1.35 / 1.36 supported
- PostgreSQL 14-18 supported
- (replaces 1.29.1, which supports only 1.33/1.34/1.35 and is EOL 2026-09-29)

## Files
- cnpg-1.30.1-upstream.yaml — exact official signed release asset (unaltered)
- cnpg-1.30.1-digest-pinned.yaml — operator image pinned to digest (only image refs changed)

## Deploy
```
kubectl apply --server-side -f cnpg-1.30.1-digest-pinned.yaml
```
Operator namespace: cnpg-system. See UPSTREAM_PROVENANCE.md for supply-chain evidence.
