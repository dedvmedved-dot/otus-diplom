# Deployment Preview Corrected (NO APPLY)

Velero:
  version: v1.18.1
  digest: sha256:2752a01188bd8f16572a76b3b2c4331a6a5337a5cbe65715c22ac7f91b31bfa8
  features: EnableCSI

AWS object-store plugin:
  version: v1.14.2
  digest: sha256:abe29a7b360231e359f7aaee79668141bd619ab6989c7cc78d041110987f6ca2

node-agent:
  enabled: true
  uploader: Kopia
  hostNetwork: not explicitly enabled

CSI snapshot:
  VolumeSnapshotClass: piraeus-r2-snapclass
  Velero VolumeSnapshotLocation for LINSTOR CSI: NOT REQUIRED

BackupStorageLocation:
  provider: aws
  bucket: portal-velero-backup
  region: ru-west-1
  s3Url: https://172.30.143.10:9000
  s3ForcePathStyle: true
  TLS verification: enabled
  insecureSkipTLSVerify: false
  CA reference: velero/minio-ca
  credential reference: velero/velero-minio-credentials

MinIO:
  deployment: external to Kubernetes cluster
  versioning: enabled
  Object Lock: enabled (GOVERNANCE, 7 days)
  lifecycle retention: 30 days

No manifests applied. No runtime objects created.
