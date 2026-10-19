# Velero 1.18.1 (digest-pinned)

- velero image: docker.io/velero/velero@sha256:2752a01188bd8f16572a76b3b2c4331a6a5337a5cbe65715c22ac7f91b31bfa8
- aws plugin: docker.io/velero/velero-plugin-for-aws@sha256:abe29a7b360231e359f7aaee79668141bd619ab6989c7cc78d041110987f6ca2
- namespace: velero; Secret: velero-s3-credentials (key cloud); CA ConfigMap: velero-s3-ca (key ca.crt); BSL: default (provider aws, bucket portal-velero-backup, region ru-west-1, s3Url https://s3-backup.demo-pak.test, s3ForcePathStyle true, private CA).
- EnableCSI + node-agent (kopia). use-volume-snapshots=false (NO LINSTOR/AWS VSL — CSI via piraeus-r2-snapclass).
- control-plane toleration added (all nodes are combined control-plane).
- Secret renamed cloud-credentials -> velero-s3-credentials (per task §16).

NOTE: deployment is BLOCKED at BSL validation — pod DNS cannot resolve s3-backup.demo-pak.test (BIND9 ACL 172.30.143.0/24 vs pod egress IP). See evidence result.md.
