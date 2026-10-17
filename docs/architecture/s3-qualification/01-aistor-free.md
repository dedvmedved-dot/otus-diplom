# Candidate Profile — MinIO AIStor Free (C1)

## Product
MinIO AIStor — Free tier (exact official name: "AIStor Free"; also documented as
"MinIO AIStor Free (community use)"). Formerly "MinIO"; open-source AGPLv3
"MinIO" is DISCONTINUED/end-of-life.

## Candidate version
`RELEASE.2026-09-19T17-05-25Z` (published 2026-09-20). Binary/Deb/RPM/container
`quay.io/minio/aistor/minio:RELEASE.2026-09-19T17-05-25Z`.

## Release date
2026-09-20.

## Maintenance status
ACTIVE (AIStor product). The AGPLv3 `minio/minio` repo is ARCHIVED
("THIS REPOSITORY IS NO LONGER MAINTAINED"). Security fixes land in AIStor
release tags only; the frozen community codebase has no patch path for 2026 CVEs.

## License/support
Proprietary "MinIO AIStor Free Tier License Agreement" (2026-01-30): royalty-free,
single-node only, no redistribution/sublicensing, "AS IS", no SLA, no warranty,
revocable. NOT open source. Support = community Slack + docs only; no documented
LTS/support term.

## Deployment model
Single-node only (standalone). No HA, no replication, no multi-node.
Single-node single-drive is deployable but provides NO erasure parity.

## Resource requirements
4 vCPU / 7.7 GiB / 500 GB data disk: FITS (single-node single-drive; parity 0).
No minimum node count beyond "single node".

## S3 compatibility
Full Object APIs + Multipart + Bucket APIs + STS. Unsupported: Get/PutObjectAcl,
AbortIncompleteMultipartUpload lifecycle action. Path-style: served by default
(not independently re-verified beyond S3-compat doc — flag for acceptance test).

## Versioning
Available (Enabled/Suspended, delete markers, ListObjectVersions).
"Version-specific object deletion" is Enterprise-only (general versioning OK).

## Object Lock
Available in Free (not tier-gated): GOVERNANCE + COMPLIANCE + legal hold,
Get/PutObjectRetention, Get/PutObjectLegalHold, Get/PutObjectLockConfiguration.

## Governance semantics
GOVERNANCE bypass requires `x-amz-bypass-governance-retention` header + the
`s3:BypassGovernanceRetention` permission. COMPLIANCE/legal-hold non-bypassable.
(AWS S3-compatible; documented, not independently code-verified — proprietary binary.)

## Lifecycle
Local expiration (`PutBucketLifecycle`) available in Free. Tiering/transitions =
Enterprise-only.

## Encryption
**NOT available in Free tier (plaintext only).** SSE-S3 / SSE-KMS / SSE-C are all
gated behind Enterprise Lite/Enterprise. Free tier refuses SSE writes with
`XMinioPaidTierLicenseRequired` (HTTP 405). Key managers: MinIO KMS / KES / static key
(paid). => AIStor_Free_Encryption = CONDITIONAL_LUKS (storage-layer LUKS2/dm-crypt
on /dev/vdb would be required to satisfy the generic TR encryption requirement).

## IAM/credentials
Built-in access keys, LDAP/AD, OIDC, K8s service accounts, policies, STS —
all available in Free (supports separate least-privilege identities).

## TLS/private CA
Fully supported; custom/private CA via /certs/CAs (SAN/SNI selection).

## Velero compatibility
SUPPORTED (S3 API + path-style + private CA + TLS verify; no tier gating).

## Barman compatibility
EXPECTED_COMPATIBLE (boto3 S3 custom endpoint; Object Lock requires retention
coordination).

## Security findings
Actively patched (AIStor). Free tier = same binary, receives security updates.
2026 advisories on the frozen AGPL codebase have NO fix in minio/minio (this is why
Community was rejected) — AIStor Free resolves that. Free has no LTS/hotfix term.

## Supply-chain
Proprietary binary (no source, no reproducible build). SBOM published per release
(CycloneDX+SPDX). Checksum available on dl.min.io. **SUBNET license activation
required even for Free** (license file/JWT; auto-renew every 24h; expiry ladder:
≤30d grace → 30–90d read-only → ≥90d offline). Offline requires periodic manual
license renewal.

## Current VM fit
PASS (single-node fits 4 vCPU / 7.7 GiB / 500 GB; single-drive = no parity).

## Operational complexity
MEDIUM (single binary, mature docs) — but raised by SUBNET license management +
(if chosen) LUKS encryption layer.

## Known blockers
1) No native encryption at rest (plaintext only) — LUKS fallback required.
2) Proprietary license + SUBNET activation/renewal dependency (offline risk).
3) No erasure parity on single drive.

## Qualification result
CONDITIONAL (viable; encryption = CONDITIONAL_LUKS; license/SUBNET dependency).

## Evidence sources
min.io/pricing; min.io/download; www.min.io/legal/aistor-free-agreement;
docs.min.io/aistor/operations/licenses/; docs.min.io/aistor/installation/linux/server-side-encryption/;
docs.min.io/aistor/administration/object-locking-and-immutability/;
dl.min.io/api/releases/aistor/latest; github.com/minio/minio (archived).
