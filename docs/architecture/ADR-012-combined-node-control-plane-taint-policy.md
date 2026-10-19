# ADR-012 — Combined-node control-plane taint policy

STATUS: ACCEPTED
ACCEPTED_BY: Chief Architect / Technical Authority
ACCEPTED_DATE: 2026-10-19
SOURCE_TASK: P7C-B2-R1-T1

## Decision

Current DEMO topology consists of 3 combined Control Plane / Worker / Storage nodes.

Canonical scheduling taint: node-role.kubernetes.io/control-plane:PreferNoSchedule
Previous state: node-role.kubernetes.io/control-plane:NoSchedule

## Reason

NoSchedule prevents dynamically generated workloads that cannot receive a custom
toleration, including Velero 1.18.1 CSI Snapshot Data Movement exposer pods, despite
the fact that all three control-plane nodes are intentionally also worker nodes.

## Explicitly recorded

CONTROL_PLANE_LABELS: PRESERVED
CONTROL_PLANE_ROLE: PRESERVED
ETCD: PRESERVED
STATIC CONTROL PLANE PODS: PRESERVED
TAINT KEY: PRESERVED
TAINT EFFECT: NoSchedule -> PreferNoSchedule
TAINT REMOVAL: NO
VELERO PATCH: NO
VELERO UPGRADE: NO

Future dedicated worker nodes: REASSESS POLICY.

## Implementation result (P7C-B2-R1-T1)

IMPLEMENTATION_RESULT: PASS
CURRENT_POLICY: PreferNoSchedule on node-01/node-02/node-03
P7C_B2_DATA_MOVER_SCHEDULING: PASS
COMBINED_NODE_TAINT_POLICY: PreferNoSchedule
