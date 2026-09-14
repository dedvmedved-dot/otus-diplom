# P7C Snapshot Controller Canonical Manifest (DESIGN ONLY, R4-corrected)

DESIGN ONLY — RUNTIME DEPLOYMENT NOT AUTHORIZED.

Deployment (kube-system):
  replicas=2                                  UPSTREAM_PRESERVED
  selector/pod labels                         UPSTREAM_PRESERVED
  serviceAccountName=snapshot-controller      UPSTREAM_PRESERVED
  container name=snapshot-controller          UPSTREAM_PRESERVED
  image=snapshot-controller:v8.6.0@sha256:d1ab1b095eb81ce689abc8b8094badc4c4ea657051749014a631f8cca876a620  PROJECT_HARDENING
  args: --v=5 --leader-election=true          UPSTREAM_PRESERVED
  imagePullPolicy=IfNotPresent                UPSTREAM_PRESERVED
  minReadySeconds=35                          UPSTREAM_PRESERVED
  strategy RollingUpdate maxSurge=0 maxUnavailable=1  UPSTREAM_PRESERVED
  tolerations: node-role.kubernetes.io/control-plane=NoSchedule  PROJECT_SCHEDULING_ADAPTATION
  securityContext                             OPTIONAL_PROJECT_HARDENING_TO_CANARY

Selected controller: v8.6.0 (k8s.io/client-go v0.36.1 = K8s 1.36 exact match).
Selected CRDs: v8.5.0/v8.6.0 single-volume (identical SHA256).
