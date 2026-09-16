# CSI Model Corrected

Corrected architecture:
  StorageClass -> LINSTOR CSI -> VolumeSnapshotClass piraeus-r2-snapclass -> VolumeSnapshot
  -> Velero CSI Snapshot Data Movement -> node-agent / Kopia -> MinIO

VELERO_VSL_FOR_LINSTOR = NOT_REQUIRED

VOLUME_SNAPSHOT_CLASS = piraeus-r2-snapclass  (already deployed, P7C-B1 foundation)

CSI snapshot handling remains through the Kubernetes snapshot API. The P7C-B1
foundation (3 CRDs + snapshot-controller + VolumeSnapshotClass) is NOT modified.
