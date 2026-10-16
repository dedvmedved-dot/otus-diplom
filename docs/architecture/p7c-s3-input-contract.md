# P7C S3 Input Contract

NO SECRET VALUES ARE TO BE COMMITTED TO GIT. Only references/names allowed.

```text
S3_PROVIDER_TYPE=MINIO
S3_ENDPOINT=https://s3-backup.demo-pak.test
S3_BUCKET=portal-velero-backup
S3_REGION=ru-west-1
S3_FORCE_PATH_STYLE=true
S3_TLS_CA_MODE=PRIVATE_CA
S3_TLS_CA_REF=velero/minio-ca (future ConfigMap reference, not yet created)
S3_CREDENTIAL_SECRET_REF=velero-minio-credentials (future, not yet created)
S3_CREDENTIAL_SECRET_NAMESPACE=velero
S3_OBJECT_LOCK_REQUIRED=true
S3_OBJECT_LOCK_ENABLED=unknown (until SC2 runtime validation)
S3_VERSIONING_ENABLED=unknown (until SC2 runtime validation)
S3_RETENTION_MODE=GOVERNANCE
S3_RETENTION_PERIOD=7 days (object lock) / 30 days (lifecycle)
S3_SERVER_SIDE_ENCRYPTION=unknown (do not invent)
S3_KMS_REF=
BACKUP_NETWORK_PATH=node-level VLAN143 expected; pod-level path NOT_PROVEN
BACKUP_SOURCE_CIDRS=172.30.143.0/24 (VLAN143)
CANONICAL_DNS_NAMESPACE=demo-pak.test
OLD_DNS_NAMESPACE=demo-pak.local RETIRED BY ADR-005
```

Current status: accepted architectural inputs recorded above. Runtime state
(versioning, object lock, encryption, credential objects) remains NOT_DEPLOYED
until P7C-B2B-SC2 runtime validation. No secret values are present.
