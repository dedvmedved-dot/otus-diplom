# P7C-B2A — Velero / MinIO Config Preview (NO APPLY)

Velero: v1.18.1 @ sha256:2752a01188bd8f16572a76b3b2c4331a6a5337a5cbe65715c22ac7f91b31bfa8
AWS plugin: v1.14.2 @ sha256:abe29a7b360231e359f7aaee79668141bd619ab6989c7cc78d041110987f6ca2

BackupStorageLocation (intended):
  provider: aws
  objectStorage:
    bucket: portal-velero-backup
    prefix: "" (or per-schedule prefix)
    caCert: (from ConfigMap velero/minio-ca)
  config:
    region: ru-west-1
    s3Url: https://172.30.143.10:9000
    s3ForcePathStyle: "true"
    checksumAlgorithm: "" (auto)
  credential:
    name: velero-minio-credentials
    key: cloud

VolumeSnapshotLocation:
  provider: linstor.csi.linbit.com   (-> VolumeSnapshotClass piraeus-r2-snapclass)

Data movement:
  Velero CSI Snapshot Data Movement (EnableCSI) + node-agent (DaemonSet, kopia
  uploader, hostNetwork=true) + MinIO target.

TLS:
  verify ENABLED (insecureSkipTLSVerify=false); CA via ConfigMap velero/minio-ca.

No manifests applied.
