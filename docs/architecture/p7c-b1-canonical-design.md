# P7C-B1 Canonical Design (DESIGN ONLY)

DESIGN ONLY — RUNTIME DEPLOYMENT NOT AUTHORIZED.

selected external-snapshotter release: v8.5.0
selected snapshot-controller digest: sha256:c6ed5c488dc72a01e7d69caf4d6efe44cb5fecd08fac1a037626171bf90482d1
selected CRD tag/hashes: external-snapshotter v8.5.0 (single-volume, 3 CRDs)
exact object set: CRD x3, ServiceAccount, ClusterRole, ClusterRoleBinding, Role,
  RoleBinding, Deployment, VolumeSnapshotClass piraeus-r2-snapclass
replicas=2, leader-election=true
RBAC: upstream-preserved (no expansion)
tolerations: exact control-plane NoSchedule
securityContext: runtime canary required (do not claim unproven hardening)
VolumeSnapshotClass: piraeus-r2-snapclass / linstor.csi.linbit.com / Delete
canary: temp namespace + small PVC + deterministic data + snapshot/restore + checksum + cleanup
rollback: delete canary, VolumeSnapshotClass, controller, CRDs (after no objects), verify LINSTOR CSI unchanged, P1-P7B2 preserved
acceptance: CSI_SNAPSHOT_CREATE=PASS, READY=PASS, RESTORE=PASS, DATA_INTEGRITY=PASS, CLEANUP=PASS
negative tests: per 33-b1-negative-test-design.txt
regression: P1-P7B2 verifiers
security gate: GO_WITH_DOCUMENTED_ACCEPTED_RISK (Architect acceptance required)
