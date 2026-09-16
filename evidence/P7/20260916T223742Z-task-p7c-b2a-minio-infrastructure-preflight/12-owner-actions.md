# P7C-B2A — Required Owner Actions (cannot be done by Hermes without authorization)

1. Allocate/create an external MinIO VM (outside this K8s cluster; not on node-01/02/03).
2. Assign the VM to VLAN143 with IP 172.30.143.10/24.
   (IP 172.30.143.10 shows FREE_CONFIRMED by read-only evidence; confirm in IPAM.)
3. Attach a dedicated data volume (>=100 GiB for demo, recommended 500 GiB) formatted XFS.
4. Approve MinIO installation (single-node) on that VM.
5. Create a dedicated MinIO access key with the least-privilege policy (scoped to
   portal-velero-backup); NOT root credentials.
6. Issue a TLS server certificate (PRIVATE_CA) with SAN IP=172.30.143.10 (and SAN DNS
   minio.demo-pak.local if adopted); publish CA bundle.
7. Create bucket portal-velero-backup with versioning + Object Lock (GOVERNANCE, 7d)
   ENABLED AT CREATION.
8. Provide the Kubernetes Secret reference velero/velero-minio-credentials and the
   CA ConfigMap velero/minio-ca (values supplied out-of-band; not committed).
9. Authorize P7C-B2 runtime deployment (Velero + BSL + VSL + node-agent).
