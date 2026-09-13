# P7C-B1 Canonical Design (DESIGN ONLY)

DESIGN ONLY — RUNTIME DEPLOYMENT NOT AUTHORIZED.

selected release: external-snapshotter v8.5.0
controller digest: sha256:c6ed5c488dc72a01e7d69caf4d6efe44cb5fecd08fac1a037626171bf90482d1
CRDs: v8.5.0 single-volume (3 CRDs, SHA256 pinned)
object set: CRD x3 + SA + ClusterRole + ClusterRoleBinding + Role + RoleBinding +
  Deployment (replicas 2, leader-election, minReadySeconds 35, maxSurge 0, maxUnavailable 1)
  + VolumeSnapshotClass piraeus-r2-snapclass
tolerations: exact control-plane NoSchedule
securityContext: canary-gated optional hardening
canary: CRDs established, controller 2/2 Ready, correct digest live 2/2, leader election
  active, no RBAC expansion, snapshot API discovery, VolumeSnapshotClass correct, snapshot
  create/readyToUse/restore/checksum PASS, cleanup PASS, no LINSTOR residue, P1-P7B2 regression
negative tests: per 34-b1-negative-test-contract.txt
rollback: per 35-b1-rollback-contract.txt
security gate: GO_WITH_DOCUMENTED_ACCEPTED_RISK (Architect acceptance required)
