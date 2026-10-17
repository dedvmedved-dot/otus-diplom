# Candidate Profile — SeaweedFS (C3)

## Product
SeaweedFS (github.com/seaweedfs/seaweedfs), S3-compatible object store + filer.

## Candidate version
`4.48` (git tag `4.48`, commit `530be3e37337488ecc34d58441e0bc476e121c93`).

## Release date
2026-09-28.

## Maintenance status
ACTIVE (pushed 2026-10-17; ~144 PRs into 4.48; monthly releases).

## License/support
Apache-2.0 (open source). Community support; no vendor SLA.

## Deployment model
Single binary `weed server -s3` = master + volume + filer + S3 gateway in one
process. Single-node single-filer single-volume = default demo topology.

## Resource requirements
4 vCPU / 7.7 GiB / 500 GB: trivially FITS (Go daemons; 500 GB = single volume).

## S3 compatibility
Versioning, Object Lock, lifecycle, multipart, path-style is NATIVE (no virtual-host
required). Verified in 4.48 source.

## Versioning
Enabled/Suspended, delete markers, ListObjectVersions (pagination bug #11594 in 4.48,
fixed only post-4.48).

## Object Lock
Bucket enable + PutObjectRetention (GOVERNANCE + COMPLIANCE) + legal hold.

## Governance semantics
**VERIFIED IN 4.48 SOURCE**: `enforceObjectLockProtections` on delete path.
GOVERNANCE bypass requires header + `s3:BypassGovernanceRetention` permission.
COMPLIANCE non-bypassable. DeleteBucket checks locked objects. Delete-marker
behavior AWS-correct. Lifecycle respects Object Lock (SKIPPED_OBJECT_LOCK).
Fixed in 4.48: #8350 (COMPLIANCE not enforced), #11333/#11335 (regression),
#11450 (bucket recreate wiped lock/lifecycle/versioning), #11361/#11362/#11475/#11476/#11492
(object-lock permission pinning).

## Lifecycle
Supported (expiration days/date, noncurrent, NewerNoncurrentVersions).
Respects Object Lock. **OPEN gap #8757: lifecycle removes metadata but does NOT
reclaim volume disk space** (must handle compaction separately).

## Encryption
SSE-S3 (AES256), SSE-KMS (SeaweedFS-internal key marker, NOT external KMS), SSE-C,
and `-s3.encryptVolumeData` (storage-layer at-rest). Post-4.48 fixes (#11647/#11688/#11556)
NOT in 4.48. Prefer `-s3.encryptVolumeData` or LUKS for at-rest.

## IAM/credentials
Static identities + advanced IAM (`-s3.iam.config`), per-identity access/secret keys,
scoped actions, dedicated `s3:BypassGovernanceRetention` + `s3:PutObjectLockConfiguration`
permissions (separated in 4.48). Least-privilege per workload feasible.

## TLS/private CA
`-s3.port.https`, `-s3.cert.file`, `-s3.key.file`, `-s3.cacert.file`, mTLS.

## Velero compatibility
SUPPORTED (path-style native + custom CA + TLS verify).

## Barman compatibility
EXPECTED_COMPATIBLE (boto3 custom endpoint; Object Lock requires retention coordination).

## Security findings
25 GHSA advisories (mostly 2026) concentrated in S3/IAM/auth: multiple CRITICAL/HIGH
(SigV4 bypass, SSRF, path-traversal, AQL injection, IAM escalation). ALL CRITICAL/HIGH
S3-data-path advisories are FIXED in 4.48 (vulnerable ranges ≤4.45). Hardening REQUIRED:
set `jwt.filer_signing.key` (else the PutIdentity fix is a no-op), expose ONLY the S3
HTTPS port (never filer/volume/gRPC to untrusted nets). Object Lock enforced at the
S3 gateway layer only (not filer core).

## Supply-chain
PASS — open source (Apache-2.0), reproducible source build feasible, tagged releases,
checksums on GitHub releases. No license activation.

## Current VM fit
PASS (single-node trivially fits).

## Operational complexity
MEDIUM (single binary, but multi-component: master/volume/filer/S3; plus hardening
+ lifecycle disk-reclaim handling).

## Known blockers
1) Lifecycle disk-reclaim gap #8757 (OPEN) — capacity grows unless compacted.
2) `-s3.allowDeleteBucketNotEmpty` defaults true in 4.48 (set false).
3) Hardening mandatory (jwt key + S3-only exposure) for the immutability claim to hold.

## Qualification result
PASS (with documented conditions) — RECOMMENDED candidate. Hard-gates pass; lifecycle
is CONDITIONAL (disk reclaim); encryption = PASS_NATIVE (SSE-S3 + encryptVolumeData).

## Evidence sources
github.com/seaweedfs/seaweedfs (releases/tag/4.48, issues #8350/#11333/#11450/#8757/#9884/#11594,
PRs #11335/#11361/#11362/#11475/#11476/#11492/#11769, security advisories);
local source clone at 4.48 (weed/s3api/*).
