# P7C Snapshot Stack Version Alignment

| Criterion | v8.5.0 controller + v8.5.0 sidecar | v8.6.0 controller + v8.5.0 sidecar |
|---|---|---|
| Kubernetes 1.36 compatibility | YES (v8.x targets modern K8s) | YES (newer) |
| CSI spec compatibility | CSI 1.x (v1 API) | CSI 1.x (v1 API) |
| VolumeSnapshot v1 | YES (GA) | YES (GA) |
| Exact version alignment | YES (sidecar==controller) | NO (mixed minor) |
| Version skew | NONE | 0.1 minor skew |
| Additional CRDs/features | baseline | group-snapshot refinements |
| Operational risk | LOW | slightly higher (untested mix) |
| Security/release status | stable GA | stable GA (newer) |
| Image digest verified | YES (c6ed5c48) | YES (d1ab1b09) |
| Recommendation | SELECTED | alternative |

SNAPSHOT_STACK_SELECTED=v8.5.0
ARCHITECT_APPROVAL_REQUIRED=YES

Rationale: aligns exactly with the accepted LINSTOR CSI csi-snapshotter sidecar
v8.5.0 (digest sha256:da081c27...), minimizing version skew. VolumeGroupSnapshot GA
is not required for P7C-B1.

snapshot-controller v8.5.0 linux/amd64 digest:
  sha256:c6ed5c488dc72a01e7d69caf4d6efe44cb5fecd08fac1a037626171bf90482d1
