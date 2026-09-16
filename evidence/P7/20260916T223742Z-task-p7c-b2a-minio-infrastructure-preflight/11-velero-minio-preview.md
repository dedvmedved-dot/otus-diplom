# P7C-B2A — Velero / MinIO Config Preview (NO APPLY) — R1-corrected

Velero: v1.18.1 @ sha256:2752a01188bd8f16572a76b3b2c4331a6a5337a5cbe65715c22ac7f91b31bfa8
AWS plugin: v1.14.2 @ sha256:abe29a7b360231e359f7aaee79668141bd619ab6989c7cc78d041110987f6ca2

## Corrected CSI Snapshot Data Movement model

StorageClass -> LINSTOR CSI -> VolumeSnapshotClass piraeus-r2-snapclass -> VolumeSnapshot
-> Velero CSI Snapshot Data Movement -> node-agent / Kopia -> MinIO

- VolumeSnapshotClass `piraeus-r2-snapclass` is the already-deployed Kubernetes object
  (part of P7C-B1 foundation). Do not modify or recreate it.
- CSI snapshot handling remains through the Kubernetes snapshot API.
- Velero VolumeSnapshotLocation for LINSTOR CSI = NOT REQUIRED.

## Velero deployment (intended)

  features: EnableCSI
  uploader: Kopia

## node-agent (intended)

  enabled: true
  DaemonSet, normal Pod networking, Kopia data mover
  hostNetwork: not explicitly enabled

## BackupStorageLocation (intended)

  provider: aws
  objectStorage:
    bucket: portal-velero-backup
    prefix: "" (or per-schedule prefix)
    caCert: (from ConfigMap velero/minio-ca)
  config:
    region: ru-west-1
    s3Url: https://172.30.143.10:9000
    s3ForcePathStyle: "true"
  credential:
    name: velero-minio-credentials
    key: cloud
  TLS: verify ENABLED (insecureSkipTLSVerify=false); CA via ConfigMap velero/minio-ca

## MinIO (intended, external to K8s)

  versioning: enabled
  Object Lock: enabled, GOVERNANCE, 7 days
  lifecycle retention: 30 days

No manifests applied. No runtime objects created.
