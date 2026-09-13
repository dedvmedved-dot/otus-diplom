# P7C Snapshot Controller Canonical Manifest (DESIGN ONLY)

DESIGN ONLY — RUNTIME DEPLOYMENT NOT AUTHORIZED.

Deployment (kube-system):
  replicas=2
  selector/pod labels: app.kubernetes.io/name=snapshot-controller
  serviceAccountName=snapshot-controller
  container name=snapshot-controller
  image=registry.k8s.io/sig-storage/snapshot-controller:v8.5.0@sha256:c6ed5c488dc72a01e7d69caf4d6efe44cb5fecd08fac1a037626171bf90482d1
  args: --v=5 --leader-election=true
  imagePullPolicy=IfNotPresent
  minReadySeconds=35
  strategy: type=RollingUpdate, maxSurge=0, maxUnavailable=1
  restartPolicy=Always
  terminationGracePeriodSeconds=30
  dnsPolicy=ClusterFirst
  tolerations: node-role.kubernetes.io/control-plane=NoSchedule (operator Exists, key exact)
  securityContext: OPTIONAL_PROJECT_HARDENING_TO_CANARY (runAsNonRoot,
    allowPrivilegeEscalation=false, readOnlyRootFilesystem=true,
    capabilities.drop=[ALL], seccompProfile=RuntimeDefault) => P7C_B1_CANARY_REQUIRED

Object set: ServiceAccount, ClusterRole snapshot-controller-runner, ClusterRoleBinding,
  Role/RoleBinding snapshot-controller-leaderelection, Deployment, + 3 single-volume CRDs
  + VolumeSnapshotClass piraeus-r2-snapclass.

Field classification: image digest pin = PROJECT_HARDENING; minReadySeconds/strategy =
  PROJECT_HARDENING; toleration = PROJECT_SCHEDULING_ADAPTATION; securityContext =
  OPTIONAL_PROJECT_HARDENING_TO_CANARY; all else UPSTREAM_PRESERVED.
