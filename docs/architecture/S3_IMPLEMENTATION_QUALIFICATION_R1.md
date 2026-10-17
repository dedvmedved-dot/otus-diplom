# S3 Implementation Qualification — R1 (P7C-S3-R1)

Retrieval date: 2026-10-17. Research-only task; no candidate installed.

## 1. Reason for reselection

MinIO Community `RELEASE.2025-10-15T17-29-55Z` (AGPLv3, archived `minio/minio`) was
REJECTED for runtime deployment (ADR-006) after P7C-B2B-SC2-R1 found 7 CRITICAL +
64 HIGH (Trivy) and 73 reachable vulnerabilities (govulncheck), with no acceptable
maintained patch path. This document qualifies replacement candidates.

## 2. TR v4.0 requirements (Layer A)

A01 external S3-compatible storage; A02 protected objects (PostgreSQL+WAL, non-DB PVC
Velero, etcd, LINSTOR metadata); A03 versioning; A04 encryption (layer not prescribed →
NATIVE_S3 / BLOCK_DEVICE / CLIENT_SIDE); A05 separate credentials; A06 delete
protection; A07 Object Lock "where supported"; A08 retention baseline (WAL ≥14d, PG full
8 copies, PG incr 14, etcd 14, Velero 14, monthly 12).

## 3. Current accepted contract (Layer B)

B01 S3; B02 https://s3-backup.demo-pak.test; B03 TCP/443; B04 private-CA TLS verify;
B05 path-style; B06 bucket portal-velero-backup; B07 region ru-west-1; B08 versioning;
B09 Object Lock; B10 GOVERNANCE; B11 default lock 7d; B12 lifecycle 30d; B13 no
BypassGovernanceRetention; B14 least-privilege identities; B15 no admin for Velero;
B16 external placement; B17 VLAN143; B18 maintained security path; B19 pinned supply
chain; B20 no latest/master.

## 4. Candidate summary

| | C1 AIStor Free | C2 AIStor Ent.Lite/Ent | C3 SeaweedFS 4.48 | C4 Ceph RGW 20.2.4 |
|---|---|---|---|---|
| Version | RELEASE.2026-09-19T17-05-25Z | same | 4.48 (530be3e) | Tentacle 20.2.4 |
| License | Proprietary Free (single-node) | Commercial | Apache-2.0 | LGPL/GPL (RGW LGPL) |
| Native SSE | **NO (plaintext)** | YES | YES (SSE-S3+vol) | YES but external KMS |
| Object Lock | GOV+COMP | GOV+COMP | GOV+COMP (verified) | GOV+COMP |
| Single-node | YES (no parity) | multi-node (cost) | YES (trivial) | **FAIL (multi-disk)** |
| License activation | SUBNET required | SUBNET | none | none |

## 5. Hard-gate matrix

| Gate | AIStor Free | AIStor Ent | SeaweedFS 4.48 | Ceph RGW |
|---|---|---|---|---|
| TR-S3 | PASS | PASS | PASS | PASS |
| TR-VERSIONING | PASS | PASS | PASS | PASS |
| TR-ENCRYPTION | CONDITIONAL (LUKS) | PASS_NATIVE | PASS (SSE-S3+vol) | CONDITIONAL (KMS/SSE-C) |
| TR-SEPARATE-CREDENTIALS | PASS | PASS | PASS | PASS |
| TR-NO-DELETE | PASS | PASS | PASS (flag) | PASS |
| CURRENT-OBJECT-LOCK | PASS | PASS | PASS | PASS |
| CURRENT-GOVERNANCE | PASS | PASS | PASS | PASS |
| CURRENT-LIFECYCLE | PASS | PASS | CONDITIONAL (#8757) | PASS |
| VELERO | SUPPORTED | SUPPORTED | SUPPORTED | SUPPORTED |
| BARMAN | EXPECTED | EXPECTED | EXPECTED | EXPECTED |
| TLS-PRIVATE-CA | PASS | PASS | PASS | PASS |
| PATH-STYLE | PASS | PASS | PASS | PASS |
| SECURITY-MAINTAINED | CONDITIONAL | PASS | CONDITIONAL | PASS |
| SUPPLY-CHAIN | CONDITIONAL | CONDITIONAL | PASS | PASS |
| CURRENT-VM-FIT | PASS | PASS (cost) | PASS | **FAIL** |

(Evidence references: candidate profiles under docs/architecture/s3-qualification/.)

## 6. Encryption comparison

- AIStor Free: none (plaintext) → CONDITIONAL_LUKS.
- AIStor Ent: SSE-S3/SSE-KMS/SSE-C (native).
- SeaweedFS 4.48: SSE-S3 + SSE-KMS(internal) + SSE-C + `-s3.encryptVolumeData` (native + storage-layer).
- Ceph RGW: SSE-C (free) / SSE-KMS (Vault/Barbican/KMIP) / SSE-S3 (Vault only) → native needs external KMS.

## 7. Object Lock semantics comparison

- AIStor (both): GOVERNANCE bypass requires header + `s3:BypassGovernanceRetention`;
  COMPLIANCE non-bypassable (documented; proprietary binary, not code-verified).
- SeaweedFS 4.48: VERIFIED in source — delete path enforces Object Lock; GOVERNANCE
  bypass = header + permission; COMPLIANCE non-bypassable; DeleteBucket checks locks;
  lifecycle respects locks. Fixed #8350/#11333/#11450 in 4.48. Caveat: enforced at S3
  gateway layer only (filer/non-S3 paths NOT protected).
- Ceph RGW: GOVERNANCE/COMPLIANCE documented (not code-verified here).

## 8. Velero / Barman comparison

Velero 1.18.1 + aws-plugin v1.14.2: SUPPORTED for all (s3Url + s3ForcePathStyle +
caCert + insecureSkipTLSVerify=false). Barman Cloud (boto3 --endpoint-url):
EXPECTED_COMPATIBLE for all (Object Lock requires retention coordination).

## 9. Security comparison

- AIStor: actively patched (AIStor tags); Free no LTS/hotfix term.
- SeaweedFS 4.48: all CRITICAL/HIGH S3-path advisories fixed in 4.48; high advisory
  load; requires jwt.filer_signing.key + S3-only exposure.
- Ceph 20.2.4: recent HIGH (SigV4/STS/CephX) fixed in 20.2.4; active to 2027-06.

## 10. Current VM fit

- SeaweedFS: PASS (trivial).
- AIStor Free: PASS (single-node; single-drive = no parity).
- AIStor Ent: PASS technically (cost blocker).
- Ceph RGW: **FAIL** (needs ≥2 OSD disks, ≥16–32 GiB RAM, 3 MONs; single 500 GB disk insufficient).

## 11. Licensing / support

- SeaweedFS: Apache-2.0, no activation, community support.
- AIStor Free: proprietary Free license + SUBNET activation (renew every 24h; offline ladder).
- AIStor Ent: commercial subscription + SUBNET + capacity pricing (LEGAL_REVIEW_REQUIRED).
- Ceph: open source, community.

## 12. Operational complexity

SeaweedFS MEDIUM; AIStor Free MEDIUM (+SUBNET+LUKS); AIStor Ent MEDIUM (+commercial);
Ceph RGW VERY_HIGH.

## 13. Weighted ranking (100)

| | AIStor Free | AIStor Ent | SeaweedFS 4.48 | Ceph RGW |
|---|---|---|---|---|
| TR/contract 25 | 21 | 25 | 22 | 22 |
| Security 25 | 18 | 23 | 18 | 19 |
| Velero+Barman 15 | 14 | 15 | 14 | 14 |
| Immutability 10 | 8 | 9 | 7 | 8 |
| Operational 10 | 5 | 5 | 6 | 2 |
| VM fit 5 | 5 | 4 | 5 | 0 |
| Supply-chain 5 | 2 | 2 | 5 | 4 |
| License 5 | 2 | 1 | 4 | 3 |
| **Total** | **75** | **84** | **81** | **72** |

Note: AIStor Ent (84) is blocked by license/cost (no purchase authorized). Ceph RGW
is disqualified by VM fit despite feature score. SeaweedFS (81) is the top action-able
open-source candidate.

## 14. Blockers

- SeaweedFS: lifecycle disk-reclaim #8757 (OPEN); hardening mandatory.
- AIStor Free: no native encryption (LUKS), SUBNET license dependency.
- AIStor Ent: commercial license not authorized.
- Ceph RGW: hardware unfit.

## 15. Recommendation

RECOMMENDED_CANDIDATE = SeaweedFS 4.48 (open-source, correct Object Lock, native SSE,
no license dependency, single-node fit). SECOND_CHOICE = MinIO AIStor Free.
REJECTED = Ceph RGW (hardware), AIStor Enterprise (license/cost).
Final selection remains with the Chief Architect.
