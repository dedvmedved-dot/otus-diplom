# P7C CSI Snapshot Stack Decision (R1-aligned)

existing csi-snapshotter sidecar: v8.5.0 (digest sha256:da081c27... live==lock)
selected snapshot-controller: v8.5.0 (digest sha256:c6ed5c48...)
CRD tag/source: external-snapshotter v8.5.0 client/config/crd
version skew: NONE (sidecar==controller minor)
Kubernetes 1.36 compatibility: YES (v8.x line)
VolumeGroupSnapshot CRDs: NOT SELECTED (not required for P7C-B1)
future VolumeSnapshotClass name: piraeus-r2-snapclass (driver linstor.csi.linbit.com, deletionPolicy Delete)
P7C-B1 canary: local snapshot/restore + data integrity + cleanup

CSI_SNAPSHOT_STACK_DECISION=READY_FOR_ARCHITECT_APPROVAL
