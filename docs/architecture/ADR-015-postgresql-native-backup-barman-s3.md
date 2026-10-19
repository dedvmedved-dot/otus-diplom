# ADR-015 — PostgreSQL Native Backup + Barman Cloud Plugin + SeaweedFS S3

STATUS: ACCEPTED
ACCEPTED_BY: Chief Architect / Technical Authority
DATE: 2026-10-20
SOURCE_TASK: P8B-R1

## Decision

PostgreSQL backup is made DATABASE-AWARE. Velero / CSI snapshots remain valuable
for Kubernetes and generic PVC recovery but MUST NOT be treated as the
PostgreSQL-consistency mechanism.

Canonical PostgreSQL backup owner: CloudNativePG + Barman Cloud Plugin.

## Component versions

- Barman Cloud Plugin: 0.13.0
- CloudNativePG: 1.30.1
- PostgreSQL: 17.10
- cert-manager: 1.21.0 (required dependency of Barman Cloud Plugin 0.13.0)

## Object storage

- SeaweedFS: 4.48
- S3 endpoint: https://s3-backup.demo-pak.test
- S3 IP: 172.30.143.10
- port: 443
- region: ru-west-1
- Dedicated PostgreSQL bucket: portal-postgres-backup (DO NOT reuse portal-velero-backup)

Reason for a dedicated bucket: separate credentials; separate retention domain;
no Barman pruning against Velero data; independent audit trail; cleaner
least-privilege IAM; future PostgreSQL recovery lifecycle independent from Velero.

## Barman configuration

- ObjectStore destinationPath: s3://portal-postgres-backup/
- Barman server root: s3://portal-postgres-backup/portal-db/
- Dedicated identity: barman-portal
- Kubernetes Secret: portal/portal-barman-s3-credentials (ACCESS_KEY_ID, ACCESS_SECRET_KEY, AWS_REGION)
- Private CA Secret: portal/portal-barman-s3-ca (key ca.crt)
- ObjectStore: portal/portal-db-backup
- ScheduledBackup: portal/portal-db-daily
- Schedule: 02:00 UTC daily (cron 0 0 2 * * *)
- Backup target: prefer-standby
- retention: 14d (recovery window)
- S3 Object Lock: GOVERNANCE 7d
- S3 lifecycle: 30d
- versioning: Enabled
- BypassGovernanceRetention: FORBIDDEN

## S3 addressing

Path-style (no wildcard bucket DNS dependency): --addressing-style=path on
data/WAL archive+restore commands.

## Demo engineering recovery targets

- RPO engineering target: <= 5 minutes under healthy S3/WAL archiving
- RTO engineering target: <= 60 minutes

These are DEMO acceptance targets, NOT contractual production SLAs.
