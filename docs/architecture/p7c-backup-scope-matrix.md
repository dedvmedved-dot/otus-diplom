# P7C Backup Scope Matrix

| Resource/Data | Velero obj | CSI snapshot | FS backup | LINSTOR S3 | CNPG/Barman | Owner |
|---|---:|---:|---:|---:|---:|---|
| K8s manifests/CRDs | X | - | - | - | - | Velero |
| Secrets metadata/data | X | - | - | - | - | Velero |
| ConfigMaps | X | - | - | - | - | Velero |
| LINSTOR PVC data | - | X (local) | alt | X (offsite) | - | TBD |
| PostgreSQL PVC | - | - | - | - | X | CNPG/Barman |
| PostgreSQL WAL | - | - | - | - | X | CNPG/Barman |
| Metrics/observability config | X | - | - | - | - | Velero |
| Gateway/network objects | X | - | - | - | - | Velero |
