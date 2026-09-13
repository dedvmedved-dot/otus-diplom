# P7C Snapshot Controller RBAC (exactness)

From upstream rbac-snapshot-controller.yaml (v8.5.0), preserved exactly.

ClusterRole snapshot-controller-runner:
  - apiGroups: snapshot.storage.k8s.io
    resources: volumesnapshotclasses, volumesnapshotcontents, volumesnapshots
    verbs: get, list, watch
  - apiGroups: snapshot.storage.k8s.io
    resources: volumesnapshotcontents/status, volumesnapshots/status
    verbs: update, patch
  - apiGroups: "" (core)
    resources: persistentvolumeclaims, persistentvolumes
    verbs: get, list, watch
  - events: create, patch, update
  - apiGroups: coordination.k8s.io, resources: leases, verbs: get,watch,list,delete,update,create

Role snapshot-controller-leaderelection (kube-system): coordination.k8s.io leases.

RBAC_EXPANSION_OVER_UPSTREAM=NO (no cluster-admin, no wildcard additions).
