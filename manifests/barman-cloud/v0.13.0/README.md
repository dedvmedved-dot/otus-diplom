# Barman Cloud Plugin 0.13.0 (digest-pinned)

PostgreSQL native backup for CloudNativePG 1.30.1.

## Images (linux/amd64)
- plugin:  ghcr.io/cloudnative-pg/plugin-barman-cloud@sha256:417449fe4f6f0a56acdeb30e4131930815f2b46b9afeb808059b57aa8b4c2ef5
- sidecar: ghcr.io/cloudnative-pg/plugin-barman-cloud-sidecar@sha256:15cb1a01e7c5235eedac2061cab8208e5f7c39dbda292f9c2d4ddaa0c1f211e6

Embedded Barman 3.19.1, boto3 1.43.26.

## Compatibility
- requires CloudNativePG >= 1.26 (current: 1.30.1)
- requires cert-manager (internal plugin client/server certificates)

## Files
- plugin-barman-cloud-v0.13.0-release.yaml — exact official GitHub release asset (unaltered)
- plugin-barman-cloud-v0.13.0-digest-pinned.yaml — plugin image + SIDECAR_IMAGE pinned to digest
- objectstore-portal-db.yaml — ObjectStore `portal-db-backup` (S3 destination + 14d retention)
- portal-db-daily-scheduledbackup.yaml — ScheduledBackup `portal-db-daily`

## ScheduledBackup
Canonical file: `portal-db-daily-scheduledbackup.yaml`

- schedule: `0 0 2 * * *` — daily at 02:00 UTC
- method: `plugin`
- plugin: `barman-cloud.cloudnative-pg.io`
- target: `prefer-standby`
- backupOwnerReference: `self`

ScheduledBackup controls **when** backups are requested. It does **not** store
`retentionPolicy`. Retention is defined by the ObjectStore `portal-db-backup`
(`retentionPolicy: 14d` Barman recovery-window retention).

## Deploy
Plugin installed in cnpg-system (same namespace as CNPG operator).
