# P8B FINAL → P8C NEXT WORK HANDOFF — 2026-10-20

## Source of Truth

Repository: `dedvmedved-dot/otus-diplom`

Branch: `main`

GitHub `main` is the only Source of Truth. At the start of the next Work, independently fetch and verify `origin/main`; do not trust this handoff or any SHA without Connector verification.

Base checkpoint immediately before this Architect handoff commit:

`3c4dde36d8d03dd208d400381ab7b5869dd509d8`

That commit is the Hermes P8B-R2 closure:
`P8B-R2: close scheduled backup metrics and credential hygiene`.

## Architect acceptance decision

Independent Connector verification completed against P8B-R2 evidence.

Accepted:

- P8A — FINAL ACCEPTED / CONNECTOR VERIFIED.
- P8B functional PostgreSQL native backup path — PASS / CONNECTOR VERIFIED.
- P8B-R2 Source-of-Truth / ScheduledBackup / metrics / credential-hygiene closure — PASS / CONNECTOR VERIFIED.
- P8B — FINAL ACCEPTED / CONNECTOR VERIFIED.
- P8 — IN PROGRESS.
- P8C — AUTHORIZED / NOT STARTED.
- P8D-P8G — NOT AUTHORIZED.
- P9 — NOT AUTHORIZED.

## Verified P8A runtime baseline

- Kubernetes 1.36.2.
- CloudNativePG 1.30.1.
- PostgreSQL 17.10.
- Cluster `portal/portal-db`.
- 3/3 PostgreSQL instances; one primary and two streaming replicas.
- Required hostname anti-affinity, one instance per physical node.
- StorageClass `piraeus-r2`, three 10Gi PVCs.
- LINSTOR / DRBD healthy.
- `portal-db-rw`, `portal-db-ro`, `portal-db-r` are internal ClusterIP services.
- application DB `portal`, role `portal_app`, schema `portal`.
- application credentials generated/stored out-of-band in Kubernetes Secret `portal/portal-db-app`.
- TLS `verify-full` validated.
- automatic primary failover validated; data integrity preserved.

Canonical contracts:

- `docs/architecture/P8_PORTAL_DB_CONTRACT.md`
- `docs/architecture/P8_PORTAL_PLATFORM_API_CONTRACT_R0.md`

## Verified P8B runtime baseline

- cert-manager 1.21.0 deployed.
- Barman Cloud Plugin 0.13.0 deployed.
- embedded Barman 3.19.1.
- plugin and sidecar images digest-pinned.
- Barman sidecar present on all three PostgreSQL instances.
- ObjectStore: `portal/portal-db-backup`.
- dedicated S3 bucket: `portal-postgres-backup`.
- S3 endpoint: `https://s3-backup.demo-pak.test`.
- S3 region: `ru-west-1`.
- path-style addressing.
- private CA verification enabled.
- dedicated identity `barman-portal`; no Admin, no BypassGovernanceRetention, no access to Velero bucket.
- versioning enabled.
- Object Lock GOVERNANCE 7 days.
- lifecycle 30 days.
- Barman recovery window 14 days.
- continuous WAL archiving PASS; `archive_timeout=300s`.
- on-demand physical base backup PASS.
- latest restore PASS.
- PITR PASS: recovery target restored markers 1 and 2 while excluding marker 3.
- engineering RPO configuration <=5 minutes; restore/PITR completed well below 60-minute demo target.
- daily ScheduledBackup `portal/portal-db-daily`, schedule `0 0 2 * * *`, plugin method, target `prefer-standby`.
- canonical manifest: `manifests/barman-cloud/v0.13.0/portal-db-daily-scheduledbackup.yaml`.
- Barman runtime metrics verified on CNPG instance metrics endpoint (9187): last available backup and first recoverability point present; last failed backup zero.
- Velero backup domain remains isolated and healthy.
- source `portal-db` remains 3/3 healthy.

P8B architecture/contracts:

- `docs/architecture/ADR-015-postgresql-native-backup-barman-s3.md`
- `docs/architecture/P8B_POSTGRES_BACKUP_CONTRACT.md`
- `docs/architecture/P8_BACKUP_POLICY_GAPS.md`

P8B R2 evidence:

- `evidence/P8/20261020T052255Z-task-p8b-r2-sot-metrics-credential-closure/`

## Security / credentials

A privileged S3-VM login credential disclosed during P8B was treated as compromised and rotated. Its replacement value is intentionally not stored in Git/evidence and must not be requested or reconstructed.

The temporary plaintext automation password file has been removed and verified absent.

Dedicated SSH public-key access remains functional. Password authentication is not the normal automation path. Do not weaken sudo policy or create a new plaintext password store.

Future privileged S3-VM operations, if any, require a separately authorized secure privilege mechanism.

Never place passwords, private keys, Barman/Velero S3 secrets, JWT keys, TLS private keys, or LUKS keys in Git/evidence.

## Known policy gaps carried forward

These do not invalidate P8B functionality but must remain visible until P8G/P9 closure:

- `TR_PG_WAL_14D = IMPLEMENTED_POLICY`
- `TR_PG_FULL_8_COPIES = POLICY_CAPABLE_NOT_TIME_AGED`
- `TR_PG_INCREMENTAL_DIFFERENTIAL_14 = NOT_IMPLEMENTED_IN_SELECTED_PLUGIN_PATH`
- `TR_MONTHLY_CONTROL_12 = DEFERRED_TO_P8G_P9_POLICY_CLOSURE`

Do not silently mark these complete.

## P8C authorization boundary

P8C is now AUTHORIZED.

Goal: deliver the first real Portal MVP (backend + frontend) using the already accepted DB and platform contracts.

P8C must remain read-only toward platform state by default.

Mandatory constraints:

- no cluster-admin;
- no direct BMC;
- no unrestricted shell;
- no arbitrary kubectl execution;
- no destructive/failure scenario execution;
- no mutation/orchestration API yet;
- no P8D/P8E/P8F/P8G/P9 work without a new Architect gate.

Portal should use CNPG Services, not PostgreSQL Pod IP discovery.

Database connection must follow `P8_PORTAL_DB_CONTRACT.md`.

Platform/API design must start from `P8_PORTAL_PLATFORM_API_CONTRACT_R0.md`.

## Required first actions in next Work

1. Independently verify current `main`, latest commits, and this handoff through GitHub Connector.
2. Reconfirm P8B-R2 evidence and current README/P8 stage status. Do not rerun backup/restore/PITR.
3. Perform P8C architecture/preflight before runtime:
   - define backend/frontend implementation stack;
   - define container/supply-chain strategy;
   - define DB schema/migrations for Portal application state;
   - define minimum read-only Kubernetes RBAC;
   - define MVP API/UI contract;
   - define deployment/Service/Gateway model;
   - define security boundaries and secrets model;
   - define evidence and acceptance gates.
4. Prepare one detailed executable Hermes task for P8C-R1.
5. Do not start P8D or any destructive demonstration scenario.

## Target P8C MVP

Minimum useful UI:

- overall PAK status;
- Kubernetes node status;
- workloads/services summary;
- storage/PVC/PV/VolumeSnapshot summary;
- Velero backup/restore/BSL summary;
- CloudNativePG/PostgreSQL status;
- available platform metrics;
- event/status timeline.

The first MVP should prove:

`PORTAL_UI=RUNNING`

`PORTAL_API=RUNNING`

`PORTAL_DB=CONNECTED`

`PLATFORM_STATUS=VISIBLE`

without granting the Portal excessive privileges.
