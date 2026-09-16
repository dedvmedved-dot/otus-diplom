# P7C-B2A — MinIO Storage Design

Model (demonstration environment):
- single-node MinIO (external to K8s)
- dedicated data volume (XFS)
- versioning: ENABLED
- Object Lock: ENABLED, mode GOVERNANCE, 7-day immutability
- lifecycle retention: 30 days

Implications (documented, no silent scope upgrade):
- Single-node MinIO is acceptable for backup-function demonstration.
- It is NOT itself HA (no erasure-coding distribution, no multi-drive spread across nodes).
- Backup data survives Kubernetes-cluster failure, but NOT failure of the MinIO VM/storage.
- Production HA would require a separate distributed MinIO design (multi-node erasure set)
  — explicitly OUT OF SCOPE for this demonstration PAK.
