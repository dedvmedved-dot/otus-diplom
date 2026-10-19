# P8 Portal Platform API Contract R0 (documentation only)

Early interface preparation for P8C. NO Portal runtime is deployed in P8A.

## Planned read-only data sources for Portal

- Kubernetes Nodes
- Pods / workloads
- Services / Gateway
- PVC / PV / VolumeSnapshot
- LINSTOR / DRBD health summary
- Velero Backup / Restore / BSL state
- CloudNativePG Cluster / instances
- Metrics Server / available metrics
- event timeline

## Constraints (R0)

- NO Portal runtime deployed in P8A
- NO cluster-admin for Portal
- NO direct BMC
- NO unrestricted shell
- NO arbitrary kubectl execution
- NO destructive scenario API yet

This prepares P8C without starting P8C runtime.
