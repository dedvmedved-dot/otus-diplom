# Velero 1.18.1 (digest-pinned) — CURRENT WORKING CONFIGURATION

## Images (digest-pinned)
- velero: docker.io/velero/velero@sha256:2752a01188bd8f16572a76b3b2c4331a6a5337a5cbe65715c22ac7f91b31bfa8
- aws plugin: docker.io/velero/velero-plugin-for-aws@sha256:abe29a7b360231e359f7aaee79668141bd619ab6989c7cc78d041110987f6ca2

## S3 backend
- provider: SeaweedFS 4.48 (FINAL ACCEPTED for DEMO PAK)
- endpoint: https://s3-backup.demo-pak.test (private CA, TLS verification ENABLED)
- bucket: portal-velero-backup, region ru-west-1, s3ForcePathStyle=true

## Velero configuration
- namespace: velero
- BSL: default — Available, prefix velero/ (effective root s3://portal-velero-backup/velero/)
- Secret: velero-s3-credentials (key cloud) — out-of-band, NOT committed
- CA ConfigMap: velero-s3-ca (key ca.crt)
- EnableCSI: YES; uploader: Kopia; node-agent: enabled (3/3)
- LINSTOR VSL: NOT used (use-volume-snapshots=false; CSI via piraeus-r2-snapclass)
- combined-node scheduling: control-plane taint PreferNoSchedule (ADR-012)

## node-agent ConfigMap
- name: node-agent-config
- restorePVC.ignoreDelayBinding: true

WHY restorePVC.ignoreDelayBinding=true: StorageClass piraeus-r2 uses
WaitForFirstConsumer; Velero 1.18.1 generic restore exposer otherwise enters a
WaitPVCConsumed deadlock on the restore path. This is a standard Velero
configuration flag, NOT a source patch.

## E2E validation (proven)
- CSI Snapshot Data Movement backup: PASS
- offsite restore: PASS
- checksum: PASS (meta + payload byte-identical)
- POD_DNS_TO_S3: PASS
- POD_TO_S3_PATH: PASS

## Canonical deployment set (two-file model)
Deploy in this order:
1. kubectl apply -f node-agent-config.yaml
2. kubectl apply -f velero-install.yaml

velero-install.yaml starts node-agent with `--node-agent-configmap=node-agent-config`,
so the ConfigMap must exist before node-agent starts.

Prerequisites (out-of-band): Secret velero-s3-credentials (key cloud), CA ConfigMap velero-s3-ca.

## Historical blockers (RESOLVED — audit trail only, see evidence/)
- P7C-B2-R1 initial: BSL Unavailable due to pod DNS (CoreDNS private-zone forward added → RESOLVED).
- P7C-B2-R1-PFX1: BSL rejected invalid top-level dirs (BSL prefix velero → RESOLVED).
- P7C-B2-R1-T1: data mover pod unschedulable (combined-node taint → PreferNoSchedule, ADR-012 → RESOLVED).
