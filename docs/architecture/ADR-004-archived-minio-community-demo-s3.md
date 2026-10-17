# ADR-004 — Archived MinIO Community for isolated demonstration S3 target

STATUS: SUPERSEDED FOR RUNTIME DEPLOYMENT
ACCEPTED_BY: Chief Architect / Technical Authority
SUPERSEDED_BY: ADR-006
NOTE: MinIO Community source-build/provenance decision remains historical evidence. Runtime deployment is rejected following P7C-B2B-SC2-R1 security assessment.
ACCEPTED_DATE: 2026-10-13
ACCEPTED_DIRECTION: A-R1
SCOPE: DEMO / NON-PRODUCTION ONLY
PRODUCTION_USE: NOT APPROVED
SOURCE TASK: P7C-B2B-SC1

## Decision

Use the MinIO Community final Security/CVE source release
`RELEASE.2025-10-15T17-29-55Z` (commit `9e49d5e7a648f00e26f2246f4dc28e6b07f8c84a`),
built from the official `minio/minio` source repository, as the S3-compatible
external backup target for the isolated demonstration PAK.

The older prebuilt `RELEASE.2025-09-07T16-13-09Z` binary is REJECTED for new
deployment.

Scope: DEMO ONLY. Production use: NOT APPROVED.

## Context

- TR v4.0 requires an external S3-compatible backup target (it does NOT require
  MinIO specifically).
- Owner selected MinIO as the implementation.
- MinIO Community upstream/distribution/support model materially changed:
  the open-source `minio/minio` repository is archived, and the official binary
  mirror `dl.min.io` no longer serves files (HTTP 410 Gone).
- The last selected security source release has no downloadable binary assets,
  so a controlled source build is required.

## Evidence

- GitHub API `minio/minio`: `archived: true`, `license.spdx_id = AGPL-3.0`.
- `git ls-remote` tag `RELEASE.2025-10-15T17-29-55Z` = `9e49d5e7a648f00e26f2246f4dc28e6b07f8c84a`.
- Release body: "Security/CVE RELEASE.2025-10-15T17-29-55Z" (prerelease false, 0 assets).
- `go.mod` at tag: `go 1.24.0`, `toolchain go1.24.8`.
- `dl.min.io` returns 410 Gone ("archived and no longer maintained").

## Alternatives

- A0 — old September prebuilt binary: REJECT (older than final security release).
- A-R1 — final Community security source tag built from source: PROPOSED.
- B — commercial/vendor MinIO offering: NOT SELECTED FOR CURRENT DEMO.
- C — alternative S3-compatible implementation: NOT SELECTED.

## Compensating Controls

See evidence `11-compensating-controls.md`. Highlights: demo/non-production
only, no public Internet exposure, external to protected cluster, HTTPS/TCP443
external endpoint, mandatory TLS verification with private CA, no
insecureSkipTLSVerify, dedicated least-privilege identities, no root/admin for
workloads, no BypassGovernanceRetention, versioning + Object Lock enabled,
secrets outside Git, pinned source/build provenance, SBOM, vulnerability scan
before deployment, no silent auto-upgrade.

## Consequences

- P7C-B2B runtime remains BLOCKED until this ADR is ACCEPTED by the Architect.
- P7C-B2B-SC2 (controlled source build + install) may start only after ADR
  acceptance.
- The external S3 contract is unchanged: `https://s3-backup.demo-pak.local`
  (HTTPS/TCP443), reference IP `172.30.143.10`, region `ru-west-1`, bucket
  `portal-velero-backup`.
