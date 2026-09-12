# P7C CSI Snapshot Stack Decision

LINSTOR CSI 1.11.0 supports Kubernetes CSI VolumeSnapshot (local LINSTOR snapshots).
Kubernetes snapshot API is NOT yet present on the cluster (CRDs + controller ABSENT).

Proposed stack:
- external-snapshotter v8.6.0 (latest stable, 2026-05-28): VolumeSnapshot CRDs
  (snapshot.storage.k8s.io/v1) + snapshot-controller (+ optional validation webhook)
- LINSTOR VolumeSnapshotClass (design in P7C-B, points to linstor.csi.linbit.com)

CSI_SNAPSHOT_STACK_DECISION=READY_FOR_ARCHITECT_APPROVAL

Local CSI snapshots alone do NOT satisfy offsite backup; offsite requires
CSI Snapshot Data Movement (node-agent -> S3) or LINSTOR-native S3 shipping.
