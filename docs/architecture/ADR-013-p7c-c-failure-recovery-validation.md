# ADR-013 — P7C-C Failure/Recovery Validation

STATUS: ACCEPTED
ACCEPTED_BY: Chief Architect / Technical Authority
DATE: 2026-10-19
SOURCE_TASK: P7C-C-R1

## Decision

P7C-B2 = FINAL ACCEPTED / CONNECTOR VERIFIED

P7C-C = AUTHORIZED

P7C-C scope = failure injection + repeated restore + recovery validation of the
Velero / CSI Snapshot Data Movement backup subsystem (ADR-009 refinement). P7C-C
does NOT rebuild the backup subsystem.

P8 = NOT AUTHORIZED

P9 = NOT AUTHORIZED

## Authorized failure injection (P7C-C-R1)

- FC-01 repeated restore;
- FC-02 Velero controller Pod loss;
- FC-03 one node-agent Pod loss at idle;
- FC-04 node-agent loss during active DataUpload;
- FC-05 node-agent loss during active DataDownload;
- FC-06 temporary node-agent -> S3 network-path denial (client-side NetworkPolicy);
- FC-07 final clean restore after all failures.

## NOT authorized in P7C-C-R1

Physical node power-off; node reboot; kubelet stop; containerd stop; etcd member
failure; kube-apiserver failure injection; DRBD replica failure injection;
LINSTOR satellite failure injection; SeaweedFS VM power-off; SeaweedFS service
stop; switch/VLAN shutdown; BMC actions; disk failure; LUKS manipulation;
Object Lock bypass; production PostgreSQL/CNPG tests.

Broader infrastructure failure-domain tests belong to later controlled acceptance
work, primarily P9.

## Preserved baseline

Velero 1.18.1 (digest sha256:2752a01188bd8f16572a76b3b2c4331a6a5337a5cbe65715c22ac7f91b31bfa8);
AWS plugin v1.14.2 (digest sha256:abe29a7b360231e359f7aaee79668141bd619ab6989c7cc78d041110987f6ca2);
uploader Kopia; node-agent 3/3; node-agent ConfigMap node-agent-config with
restorePVC.ignoreDelayBinding=true; BSL default/Available; S3 SeaweedFS 4.48
endpoint https://s3-backup.demo-pak.test; bucket portal-velero-backup; prefix
velero/; Object Lock GOVERNANCE 7d; network VLAN143; VolumeSnapshotClass
piraeus-r2-snapclass; CSI driver linstor.csi.linbit.com; combined-node taint
PreferNoSchedule 3/3.

## Supersession

Historical ADR-009 authorization statement is retained as historical record.
This ADR supersedes that authorization boundary for P7C-C.

## FC-06 remediation decision

ORIGINAL_FC06_SELECTOR = role=node-agent
ORIGINAL_RESULT = BLOCK_NOT_INDUCED
ROOT_CAUSE = S3 transfer is performed by CSI Snapshot Data Movement hosting/data-mover pod, not by the node-agent Pod itself
VELERO_1_18_1_DATA_DOWNLOAD_LABEL_KEY = velero.io/data-download
VELERO_1_18_1_DATA_UPLOAD_LABEL_KEY = velero.io/data-upload
CORRECTED_FC06_SELECTOR = velero.io/data-download Exists
FAILURE_TYPE = CLIENT_S3_PATH_OUTAGE
ARCHITECT_DECISION = AUTHORIZED

This section supersedes ONLY the FC-06 selector wording in the original ADR-013
test plan. All other P7C-C boundaries remain unchanged.
