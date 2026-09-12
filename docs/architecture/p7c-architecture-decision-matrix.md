# P7C Architecture Decision Matrix

| Criterion | A CSI snap | B CSI data movement | C FS backup | D LINSTOR S3 |
|---|---|---|---|---|
| offsite durability | Low | High | High | High |
| restore complexity | Low | Medium | Medium | High |
| database consistency | Low | Low | Low | High (block) |
| Kubernetes integration | High | High | Medium | Medium |
| LINSTOR compatibility | High | High | Medium | High |
| operational complexity | Low | Medium | Medium | High |
| security | High | High | High | High |
| RPO capability | Good | Good | Good | Good |
| RTO capability | Good | Medium | Medium | Medium |
| vendor lock-in | Low | Low | Low | Medium |
| failure-domain independence | Low | High | High | High |

RECOMMENDED_OPTION=HYBRID (A + B): Velero (K8s objects) + CSI snapshots (local)
+ CSI Snapshot Data Movement (offsite via S3), with CNPG/Barman owning PostgreSQL
data in P8. Final offsite selection depends on Owner S3 target.

RATIONALE: Velero object backup provides cluster-resource DR; LINSTOR CSI snapshots
provide block-level restore; Snapshot Data Movement provides offsite durability.
PostgreSQL database consistency is explicitly delegated to P8.

ARCHITECT_APPROVAL_REQUIRED=YES
