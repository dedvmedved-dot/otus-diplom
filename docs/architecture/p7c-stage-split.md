# P7C Stage Split (R2-refined)

P7C-A-R2: manifest exactness + security gate closure (no runtime mutation)
P7C-B1: CSI Snapshot Foundation — CRDs (v8.5.0, single-volume), snapshot-controller
        (v8.5.0@c6ed5c48, replicas 2, leader-election, exact control-plane toleration),
        LINSTOR VolumeSnapshotClass piraeus-r2-snapclass, local snapshot/restore canary.
        NO Velero, NO S3. SECURITY GATE=GO_WITH_DOCUMENTED_ACCEPTED_RISK.
P7C-B2: Velero/S3 Foundation — only after Owner S3 input.
P7C-C: Snapshot Data Movement / offsite restore + failure validation.

P7C-B1 runtime remains NOT AUTHORIZED. P7C-B2/P7C-C remain NOT AUTHORIZED.
