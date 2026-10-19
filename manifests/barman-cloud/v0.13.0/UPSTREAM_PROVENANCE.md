# Barman Cloud Plugin 0.13.0 — Upstream Provenance

- repository: github.com/cloudnative-pg/plugin-barman-cloud
- tag: v0.13.0
- release date: 2026-06-10
- release target commit: 1cd26c92867bd27a8cc14beab8e455cf3b64cb10

## Release asset
- manifest.yaml (GitHub RELEASE asset): sha256:d2e71e7b06822448f1a421f05781846cfdb9cc621e7ef32eef5e20c5133213b0 (matches GitHub-published digest)

Deployable source = official release asset (NOT the repository-tree manifest.yaml,
which contains development refs like plugin-barman-cloud-testing:main).

## Floating ref scan
No -testing / :main / :master / :latest references in the release asset.

## Images (linux/amd64)
- plugin: ghcr.io/cloudnative-pg/plugin-barman-cloud@sha256:417449fe4f6f0a56acdeb30e4131930815f2b46b9afeb808059b57aa8b4c2ef5
- sidecar: ghcr.io/cloudnative-pg/plugin-barman-cloud-sidecar@sha256:15cb1a01e7c5235eedac2061cab8208e5f7c39dbda292f9c2d4ddaa0c1f211e6

## Embedded runtime (verified independently)
- Barman: 3.19.1
- boto3: 1.43.26

## SIDECAR_IMAGE pinning
SIDECAR_IMAGE is stored base64-encoded inside the plugin configuration object.
Decoded for verification (ghcr.io/cloudnative-pg/plugin-barman-cloud-sidecar:v0.13.0),
then replaced with the digest-pinned reference and re-encoded.
