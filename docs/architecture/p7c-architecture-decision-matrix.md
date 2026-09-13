# P7C Architecture Decision Matrix (R1-aligned)

Consistency semantics: BLOCK_LEVEL_SNAPSHOT != DATABASE_AWARE_BACKUP;
CRASH_CONSISTENT != APPLICATION_CONSISTENT. Velero/CSI/LINSTOR snapshots are
crash/storage-consistent, NOT a substitute for WAL-aware PostgreSQL backup.

| Criterion | A CSI snap (local) | B CSI data movement | C FS backup | D LINSTOR S3 |
|---|---|---|---|---|
| offsite durability | Low | High | High | High |
| restore complexity | Low | Medium | Medium | High |
| database consistency (application-aware) | NOT SUFFICIENT | NOT SUFFICIENT | NOT SUFFICIENT | crash-consistent only |
| Kubernetes integration | High | High | Medium | Medium |
| LINSTOR compatibility | High | High | Medium | High |
| operational complexity | Low | Medium | Medium | High |
| security | High | High | High | High |
| RPO/RTO capability | Good | Good | Good | Good |
| failure-domain independence | Low | High | High | High |

RECOMMENDED_P7C_DATA_PATH = CSI_SNAPSHOT_DATA_MOVEMENT_TO_OBJECT_STORAGE
LOCAL_CSI_SNAPSHOT_ROLE = TRANSIENT_SOURCE / LOCAL_RECOVERY_TIER, NOT OFFSITE_BACKUP
POSTGRESQL_APPLICATION_CONSISTENCY_OWNER = CNPG/BARMAN (P8)

ARCHITECT_APPROVAL_REQUIRED=YES
