# ADR-007 — SeaweedFS 4.48 external S3 PoC

STATUS: ACCEPTED FOR POC
FINAL_RUNTIME_STATUS: PENDING POC ACCEPTANCE
ACCEPTED_BY: Chief Architect / Technical Authority
ACCEPTED_DATE: 2026-10-18
SOURCE_TASK: P7C-S3-P1
SCOPE: DEMO / NON-PRODUCTION ONLY

## Decision

POC_PROVIDER: SeaweedFS
POC_VERSION: 4.48
POC_TAG: 4.48
POC_COMMIT: 530be3e37337488ecc34d58441e0bc476e121c93

## Record

- SeaweedFS is selected ONLY as the PoC candidate.
- SeaweedFS is NOT yet the final production/runtime provider.
- MinIO Community remains rejected (ADR-006).
- AIStor remains the second-choice alternative (P7C-S3-R1).
- Ceph RGW remains rejected for the current hardware (P7C-S3-R1).
- ADR-005 (demo-pak.test DNS) remains valid.
- ADR-006 (S3 reselection) remains valid.

## Scope

Controlled PoC on the existing external S3 VM (172.30.143.10/24, VLAN143):
official SeaweedFS 4.48 artifact + source provenance, SBOM, vulnerability gate,
LUKS2 (/dev/vdb) + XFS, runtime install, systemd, TLS, S3 identities, canonical
bucket with versioning + Object Lock GOVERNANCE + lifecycle, controlled runtime
tests, lifecycle/compaction investigation, reboot persistence.

NOT authorized: Velero, node-agent, Kubernetes Secrets, BSL/VSL, CNPG/Barman
runtime, CoreDNS/LINSTOR/DRBD changes, P7C-B2, P7C-C, P8, P9.
