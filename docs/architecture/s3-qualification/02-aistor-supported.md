# Candidate Profile — MinIO AIStor supported commercial tier (C2)

## Product
MinIO AIStor — two paid tiers (exact official names): **AIStor Enterprise Lite**
and **AIStor Enterprise**.

## Candidate version
`RELEASE.2026-09-19T17-05-25Z` (same AIStor binary as Free; tier enforced by license).

## Release date
2026-09-20.

## Maintenance status
ACTIVE. Enterprise Lite = 12-month support term per release (no hotfixes);
Enterprise = 24-month LTS + hotfix backports.

## License/support
Commercial "MinIO Software License" (term-based, per-usable-capacity pricing).
Enterprise Lite: SUBNET Lite subscription + optional direct-to-engineer (<5-day SLA).
Enterprise: Enterprise SUBNET + 24/7/365 direct-to-engineer (<4-hour SLA, Panic Button).

## Deployment model
Horizontally scalable multi-node. Enterprise Lite targets <400 TiB; Enterprise no cap.

## Resource requirements
Multi-node architecture. Can run single-node but designed for distributed/HA.
For this demo VM it is over-specified; the license is capacity-priced.

## S3 compatibility
Same full S3 surface as Free (see C1) + version-specific deletion, replication,
tiering, telemetry, `mc support`.

## Versioning
Full, including version-specific object deletion.

## Object Lock / Governance / Lifecycle
GOVERNANCE + COMPLIANCE + legal hold; lifecycle expiration + tiering/transitions.

## Encryption
**NATIVE SSE available**: SSE-S3, SSE-KMS (MinIO KMS/KES/Vault/static key), SSE-C.
Envelope encryption; enabling SSE also encrypts backend IAM/config state.

## IAM/credentials
Full (built-in, LDAP, OIDC, K8s SA, policies, STS).

## TLS/private CA
Fully supported.

## Velero / Barman compatibility
SUPPORTED / EXPECTED_COMPATIBLE (same as C1).

## Security findings
Actively maintained with LTS + hotfixes (Enterprise). Lowest security risk of the
MinIO options.

## Supply-chain
Proprietary binary + SUBNET subscription + license activation. SBOM published.

## Current VM fit
PASS (technically runnable single-node) but cost/licensing is the blocker.

## Operational complexity
MEDIUM (mature) + commercial license/SUBNET management + cost.

## Known blockers
1) Requires a commercial license PURCHASE (NOT authorized in this task).
2) Capacity pricing + SUBNET subscription; offline/airgap still needs license renewal.
3) No purchase/registration authorized.

## Qualification result
CONDITIONAL (feature-complete incl. native SSE, but license/cost decision required;
no purchase authorized — LEGAL_REVIEW_REQUIRED = YES).

## Evidence sources
min.io/pricing; docs.min.io/aistor/operations/licenses/;
docs.min.io/aistor/operations/software-lifecycle/; docs.min.io/aistor/operations/hotfixes/.
