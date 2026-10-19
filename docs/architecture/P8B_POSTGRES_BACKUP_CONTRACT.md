# P8B PostgreSQL Backup Contract

```text
CNPG:                 1.30.1
PostgreSQL:           17.10
plugin:               Barman Cloud 0.13.0
embedded Barman:      3.19.1
S3:                   SeaweedFS 4.48
endpoint:             https://s3-backup.demo-pak.test
bucket:               portal-postgres-backup
effective server root: s3://portal-postgres-backup/portal-db/
region:               ru-west-1
addressing:           path-style
TLS:                  private CA / verification mandatory
identity:             barman-portal
credentials Secret:   portal/portal-barman-s3-credentials
CA Secret:            portal/portal-barman-s3-ca
ObjectStore:          portal/portal-db-backup
scheduled backup:     portal/portal-db-daily
schedule:             02:00 UTC daily
target:               prefer-standby
retention:            14d recovery window
Object Lock:          GOVERNANCE 7d
lifecycle:            30d
WAL:                  continuous
archive_timeout:      300s
latest restore:       PASS
PITR:                 PASS
external DB exposure: NONE
```
