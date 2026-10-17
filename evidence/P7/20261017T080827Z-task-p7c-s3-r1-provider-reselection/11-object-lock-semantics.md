# Object Lock / delete semantics

DELETE_CREATES_MARKER (versioned): YES for AIStor Free, SeaweedFS 4.48, Ceph RGW (AWS semantics).
LOCKED_VERSION_PHYSICALLY_DELETABLE_BY_NORMAL_BACKUP_ID:
  AIStor Free: NO (documented, proprietary binary)
  SeaweedFS 4.48: NO (verified in source: enforceObjectLockProtections on delete path)
  Ceph RGW: NO (documented)
BYPASS_PERMISSION_EXISTS: YES (all three) — s3:BypassGovernanceRetention (header + permission).
NORMAL_BACKUP_ID_HAS_BYPASS: MUST_BE_NO — withheld by least-privilege policy (all candidates).
LIFECYCLE_RESPECTS_OBJECT_LOCK: YES (AIStor/Ceph documented; SeaweedFS verified SKIPPED_OBJECT_LOCK).

SeaweedFS caveats: -s3.allowDeleteBucketNotEmpty defaults true in 4.48 (set false);
Object Lock enforced at S3 gateway layer only (filer/non-S3 paths unprotected);
lifecycle disk not reclaimed (#8757 OPEN).
