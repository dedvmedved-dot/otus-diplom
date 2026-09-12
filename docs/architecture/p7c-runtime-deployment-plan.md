# P7C Runtime Deployment Plan (PLAN ONLY)

1. install approved snapshot CRDs + snapshot-controller (external-snapshotter v8.6.0)
2. verify snapshot API health
3. create approved LINSTOR VolumeSnapshotClass
4. deploy Velero 1.18.1 digest-pinned (sha256:2752a011...)
5. deploy velero-plugin-for-aws v1.14.2 digest-pinned (sha256:abe29a7b...)
6. reference pre-created credential Secret (namespace/name)
7. create BackupStorageLocation
8. verify BSL Available
9. run K8s-1.36 compatibility canary
10. create small backup; perform restore canary
11. execute failure/recovery tests
12. run regressions

NOT executed in P7C-A.
