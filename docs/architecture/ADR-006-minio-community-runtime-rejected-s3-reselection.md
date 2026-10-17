# ADR-006 — MinIO Community runtime rejected; external S3 provider reselection

STATUS: ACCEPTED
ACCEPTED_BY: Chief Architect / Technical Authority
ACCEPTED_DATE: 2026-10-17
SCOPE: DEMO / NON-PRODUCTION ONLY
SOURCE TASK: P7C-S3-R1

## Decision

MinIO Community `RELEASE.2025-10-15T17-29-55Z`:

- SOURCE BUILD: VERIFIED
- RUNTIME DEPLOYMENT: REJECTED

REASON: post-release security findings + archived upstream + no acceptable
maintained patch path for the selected Community release.

ACTION: reselect external S3-compatible backup implementation.

## Explicit statements

- Source-build evidence remains valid (P7C-B2B-SC2-R1: exact tag/commit/tree
  verified, upstream Makefile build succeeded, binary provenance verified).
- Build failure is NOT the reason for rejection.
- MinIO Community binary must NOT be installed.
- The data disk `/dev/vdb` remains untouched (never formatted).
- External S3 architecture requirement remains in force.
- `172.30.143.10/24`, VLAN143 and `s3-backup.demo-pak.test` remain reserved
  for the selected replacement.
- ADR-005 (demo-pak.test internal DNS) remains valid.
- No Velero deployment is authorized by this ADR.

## Consequences

- S3 provider decision state = RESELECTION_PENDING.
- Candidates (MinIO AIStor Free, supported AIStor tier, SeaweedFS, Ceph RGW)
  are qualified in P7C-S3-R1.
- Final provider selection remains with the Chief Architect.
