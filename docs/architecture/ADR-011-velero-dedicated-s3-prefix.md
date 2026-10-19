# ADR-011 — Velero dedicated S3 prefix

STATUS: ACCEPTED
ACCEPTED_BY: Chief Architect / Technical Authority
ACCEPTED_DATE: 2026-10-19
SOURCE_TASK: P7C-B2-R1-PFX1

## Decision

Velero SHALL use a dedicated logical prefix inside the accepted backup bucket.

BUCKET: portal-velero-backup
PREFIX: velero
EFFECTIVE ROOT: s3://portal-velero-backup/velero/

## Rationale

- bucket root already contains valid historical P7C-S3 PoC evidence objects;
- some historical objects remain protected by GOVERNANCE/COMPLIANCE retention;
- deleting evidence or bypassing Object Lock is not acceptable;
- Velero supports an object-storage prefix for isolation;
- Velero data must have a stable dedicated namespace independent of unrelated objects.

## Explicitly recorded

OLD P7C-S3 VALIDATION OBJECTS: PRESERVED
OBJECT LOCK BYPASS: FORBIDDEN
BUCKET ROOT CLEANUP: NOT REQUIRED
NEW BUCKET: NOT REQUIRED
S3 ENDPOINT: UNCHANGED
S3 CREDENTIAL: UNCHANGED
TLS: UNCHANGED
