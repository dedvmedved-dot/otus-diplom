# R1 Correction Scope (narrow)

Documentation/evidence remediation only. No runtime changes.

Corrected statements:
1. Velero VolumeSnapshotLocation provider=linstor.csi.linbit.com  ->  NOT REQUIRED
2. node-agent hostNetwork=true  ->  hostNetwork not explicitly enabled
3. POD_TO_MINIO_PATH = PASS  ->  NOT_PROVEN
4. MINIO_IP_STATUS = FREE_CONFIRMED  ->  FREE_OBSERVED (+ IPAM_CONFIRMATION=REQUIRED)

Files updated:
- evidence/P7/20260916T223742Z-task-p7c-b2a-minio-infrastructure-preflight/04-pod-egress-analysis.md (appended correction note; raw output unchanged)
- evidence/P7/20260916T223742Z-task-p7c-b2a-minio-infrastructure-preflight/11-velero-minio-preview.md (VSL + hostNetwork corrected)
- evidence/P7/20260916T223742Z-task-p7c-b2a-minio-infrastructure-preflight/result.md (IP status + POD path + VSL corrected)

Raw observations remain immutable. Only summary/interpretation/design text corrected.
