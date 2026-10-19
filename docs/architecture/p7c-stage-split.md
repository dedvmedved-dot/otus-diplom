# P7C Stage Split

P7C-A-R2: manifest exactness + security gate closure (no runtime mutation)

P7C-B1: CSI Snapshot Foundation — CRDs (v8.5.0, single-volume), snapshot-controller
        (v8.5.0@c6ed5c48, replicas 2, leader-election, exact control-plane toleration),
        LINSTOR VolumeSnapshotClass piraeus-r2-snapclass, local snapshot/restore canary.
        NO Velero, NO S3. SECURITY GATE=GO_WITH_DOCUMENTED_ACCEPTED_RISK.
        STATUS: FINAL ACCEPTED

P7C-B2: Velero/S3 Foundation + CSI Snapshot Data Movement — Velero 1.18.1
        digest-pinned, AWS plugin v1.14.2, BSL default/Available with prefix velero/,
        node-agent Kopia, node-agent-config restorePVC.ignoreDelayBinding=true,
        combined-node taint PreferNoSchedule, E2E backup/restore/checksum PASS.
        STATUS: FINAL ACCEPTED / CONNECTOR VERIFIED

P7C-C: Failure / Recovery Validation — failure injection, repeated restore,
        recovery validation (FC-01..FC-07).
        STATUS: AUTHORIZED / IN PROGRESS

P8 = NOT AUTHORIZED
P9 = NOT AUTHORIZED
