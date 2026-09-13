# P7C Stage Split

P7C-A-R1: architecture/evidence correction (no runtime mutation)
P7C-B1: CSI Snapshot Foundation — CRDs (v8.5.0), snapshot-controller (v8.5.0),
        LINSTOR VolumeSnapshotClass, local snapshot/restore canary; NO Velero, NO S3
P7C-B2: Velero/S3 Foundation — only after Owner S3 input; object-store plugin
        exact approval, credential reference, BSL, Velero canary
P7C-C: CSI Snapshot Data Movement / offsite backup + restore/failure validation

P7C-B1 may be authorized independently from S3.
P7C-B2/P7C-C remain NOT AUTHORIZED in this task.
