# P7C-B2 — Deployment-Ready Preview (NO APPLY)

This is a preview only; nothing is applied.

## 1. Velero deployment
- image: docker.io/velero/velero:v1.18.1@sha256:2752a01188bd8f16572a76b3b2c4331a6a5337a5cbe65715c22ac7f91b31bfa8
- namespace: velero
- initContainers: [velero-plugin-for-aws:v1.14.2@sha256:abe29a7b360231e359f7aaee79668141bd619ab6989c7cc78d041110987f6ca2]
- defaultVolumeSnapshotLocations: piraeus-r2-snapclass (local CSI snapshots)
- features: --features=EnableCSI (CSI snapshot support)
- uploader: kopia (default in Velero 1.15+)
- tolerations: node-role.kubernetes.io/control-plane=NoSchedule

## 2. BackupStorageLocation (values from Owner)
- provider: aws (velero-plugin-for-aws)
- config:
    region: <OWNER>
    s3Url: <OWNER>
    s3ForcePathStyle: <derive from provider>
    publicUrl: <OWNER if needed>
    checksumAlgorithm: <OWNER>
  objectStorage:
    bucket: <OWNER>
    prefix: <OWNER optional>
    caCert: <Secret/ConfigMap name if private CA>
  credential:
    name: <OWNER>
    key: cloud

## 3. VolumeSnapshotLocation
- provider: linstor.csi.linbit.com
- (maps to VolumeSnapshotClass piraeus-r2-snapclass)

## 4. Credential Secret (reference only, no values)
- kind: Secret (or ExternalSecret)
- name/namespace: <OWNER>

## 5. TLS CA (if private CA)
- ConfigMap/Secret reference mounted into velero + BSL caCert field: <OWNER>

## 6. CSI feature
- EnableCSI enabled; node-agent DaemonSet with kopia uploader (hostNetwork=true, toleration)

## 7. Backup canary
- namespaced PVC (piraeus-r2) + payload -> velero backup create -> verify BSL object -> delete

## 8. Restore canary
- velero restore create -> verify PVC + payload checksum -> delete

## 9. Cleanup plan
- delete canary backups/restores, canary namespace, test BSL objects; keep Velero + BSL + VSL

No credentials, no bucket, no endpoint are specified here (OWNER INPUT REQUIRED).
