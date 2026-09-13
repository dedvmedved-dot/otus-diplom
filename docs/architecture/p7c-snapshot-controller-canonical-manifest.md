# P7C Snapshot Controller Canonical Manifest (DESIGN ONLY)

DESIGN ONLY — RUNTIME DEPLOYMENT NOT AUTHORIZED.

namespace=kube-system
replicas=2
image=registry.k8s.io/sig-storage/snapshot-controller:v8.5.0@sha256:c6ed5c488dc72a01e7d69caf4d6efe44cb5fecd08fac1a037626171bf90482d1
--v=5
--leader-election=true
imagePullPolicy=IfNotPresent
serviceAccountName=snapshot-controller

tolerations:
  - key: node-role.kubernetes.io/control-plane
    operator: Exists
    effect: NoSchedule

Object set:
  ServiceAccount snapshot-controller
  ClusterRole snapshot-controller-runner
  ClusterRoleBinding snapshot-controller-role
  Role snapshot-controller-leaderelection
  RoleBinding snapshot-controller-leaderelection
  Deployment snapshot-controller

Change classification:
  image digest pin        = PROJECT_HARDENING (upstream YAML lags image tag v8.4.0)
  control-plane toleration = PROJECT_SCHEDULING_ADAPTATION
  all else                = UPSTREAM_PRESERVED

Upstream anomaly: v8.5.0 tag deployment YAML references image v8.4.0 and
replicas=2. The released v8.5.0 image is normative; this manifest pins it explicitly.
