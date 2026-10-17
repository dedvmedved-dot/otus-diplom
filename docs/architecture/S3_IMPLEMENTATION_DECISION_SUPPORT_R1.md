# S3 Implementation — Architect Decision Support (R1)

Advisory only. Final provider selection remains with the Chief Architect.

## Final table

| Candidate | Hard gates | Security | Encryption | Object Lock | Velero | Barman | Current VM | License | Complexity | Overall |
|---|---|---|---|---|---|---|---|---|---|---|
| AIStor Free | PASS | CONDITIONAL | CONDITIONAL (LUKS) | GOV+COMP | SUPPORTED | EXPECTED | PASS | Prop. Free+SUBNET | MEDIUM | CONDITIONAL |
| AIStor Ent | PASS | PASS | PASS_NATIVE | GOV+COMP | SUPPORTED | EXPECTED | PASS(cost) | Commercial | MEDIUM | CONDITIONAL (license) |
| SeaweedFS 4.48 | PASS | CONDITIONAL | PASS_NATIVE | GOV+COMP (verified) | SUPPORTED | EXPECTED | PASS | Apache-2.0 | MEDIUM | PASS |
| Ceph RGW 20.2.4 | PASS (feature) | PASS | CONDITIONAL (KMS) | GOV+COMP | SUPPORTED | EXPECTED | **FAIL** | LGPL/GPL | VERY_HIGH | FAIL (VM fit) |

## RECOMMENDED_CANDIDATE = SeaweedFS 4.48

## SECOND_CHOICE = MinIO AIStor Free

## REJECTED = Ceph RGW (CURRENT_HARDWARE_FIT=FAIL), MinIO AIStor Enterprise Lite/Enterprise (commercial license purchase not authorized)

## OPEN_ARCHITECT_DECISIONS

1. SeaweedFS lifecycle disk-reclaim gap #8757 (OPEN): accept as known cost for a
   30-day-expiration target + define a compaction/mitigation, or require a fix before PoC.
2. Encryption approach: native SSE-S3 (SeaweedFS) vs storage-layer `-s3.encryptVolumeData`
   vs LUKS2/dm-crypt on /dev/vdb — final interpretation of the generic TR encryption
   requirement.
3. SeaweedFS hardening acceptance: `-s3.allowDeleteBucketNotEmpty=false`,
   `jwt.filer_signing.key`, expose only S3 HTTPS port (Object Lock enforced at S3
   gateway layer only).
4. If AIStor Free is preferred instead: accept LUKS encryption + SUBNET license
   activation/renewal dependency (offline ladder) — explicit risk acceptance.
