# Candidate Profile — Ceph RGW (C4)

## Product
Ceph RADOS Gateway (RGW) — S3-compatible gateway on Ceph.

## Candidate version
Ceph **Tentacle 20.2.4** (release line v20.2.x).

## Release date
20.2.4 released 2026-08-19 (initial 20.2.0 on 2025-11-18). EOL 2027-06-01.

## Maintenance status
ACTIVE (security updates only on Active Releases). Squid 19.2.7 EOL 2026-10-31
(do not start new deployment); Reef EOL 2026-03-20.

## License/support
LGPL-2.1/3.0 + GPL-2.0 mix (Ceph core LGPL; RGW LGPL). Community support; vendor
support via third parties.

## Deployment model
Distributed: MON (quorum), MGR, OSD (one drive each), RGW. Multi-node for production.

## Resource requirements
**HARD FAIL on current VM.** Documented minimums: ≥2 dedicated OSD devices (even
single-host test cluster), MON ≥5 GiB RAM + 100 GB SSD, OSD ≥4 GiB RAM each,
MON+MGR "very small cluster" = 32 GiB RAM, 3 MONs + 3 OSDs across hosts for
supportable redundancy. Current: 1× 500 GB disk, 7.7 GiB RAM, 4 vCPU, 50 GB OS.

## S3 compatibility
Full (versioning, Object Lock, lifecycle, multipart, path-style default).

## Versioning
Supported (Enabled/Suspended).

## Object Lock
Supported (GOVERNANCE + COMPLIANCE; Tentacle 20.2.4 can enable Object Lock on
existing versioning-enabled bucket). Legal hold not documented in current API ref.

## Governance semantics
GOVERNANCE/COMPLIANCE retention (standard S3). Documented (docs.ceph.com), not
independently code-verified.

## Lifecycle
Supported (`rgw_lc_*` workers); delete-marker removal fixed in 20.2.4.

## Encryption
SSE-C (no external dep), SSE-KMS (Vault/Barbican/KMIP), SSE-S3 (Vault only).
**No built-in KMS** — native SSE adds an external KMS. Default AES-256-CBC (use
AES-256-GCM). Realistic single-VM path = SSE-C or LUKS.

## IAM/credentials
IAM API (users/groups/roles/access-keys/policies, managed policies) — added Squid.

## TLS/private CA
Beast frontend, TLS 1.2/1.3, custom/private CA (`ssl_certificate`/`ssl_private_key`),
`ssl_reload`.

## Velero / Barman compatibility
SUPPORTED / EXPECTED_COMPATIBLE (feature-level).

## Security findings
Actively patched. Recent HIGH CVEs fixed in 20.2.4: CVE-2026-54330 (RGW SigV4
privilege escalation), CVE-2026-39944 (STS CBC bit-flip), CVE-2025-30156 (CephX auth
bypass). Must pin ≥20.2.4 + prefer AES-256-GCM.

## Supply-chain
PASS (open source, reproducible, tagged releases, active). Container-based (cephadm
requires Podman/Docker). Astra Linux SE is not a first-party Ceph target.

## Current VM fit
**FAIL** — CURRENT_HARDWARE_FIT = FAIL (single 500 GB disk, 7.7 GiB RAM insufficient).
ARCHITECTURAL_FIT = POSSIBLE_WITH_HARDWARE_CHANGE (needs ≥2 disks, ≥16–32 GiB RAM,
≥8 vCPU, ideally 3 nodes).

## Operational complexity
VERY_HIGH (MON+MGR+OSD+RGW daemons, cephadm/containers, KMS, multi-disk).

## Known blockers
1) CURRENT_HARDWARE_FIT = FAIL (single small VM insufficient for supportable Ceph).
2) Native SSE needs external KMS (Vault/Barbican/KMIP).
3) Not a first-party Astra Linux target (container runtime to validate).

## Qualification result
FAIL (deployment fit) — feature fit PASS, but not deployable on specified hardware.

## Evidence sources
docs.ceph.com/en/latest/releases/; .../releases/tentacle/; .../radosgw/s3/;
.../radosgw/s3/bucketops/; .../radosgw/encryption/; .../radosgw/iam/;
.../radosgw/frontends/; .../start/quick-start-cephadm/; .../start/minimum-hardware/;
.../start/hardware-recommendations/; .../security/.
