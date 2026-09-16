# TASK-P7C-B2A result

TASK: P7C-B2A MINIO INFRASTRUCTURE PREFLIGHT
MAIN_HEAD_START: b668e174737a8086bdc3324bff0b630a24f7c841

BASELINE: PASS (nodes Ready 3/3, snapshot-controller 2/2, 3 CRDs, VSC, satellites Online, DRBD clean, VLAN141, residue 0)

MINIO_PROVIDER: MinIO

MINIO_IP: 172.30.143.10
MINIO_IP_STATUS: FREE_OBSERVED (no ARP/ping/TCP9000/DNS/infra reference; no observed active owner)
IPAM_CONFIRMATION: REQUIRED (network-owner confirmation before allocation)

MINIO_HOST: NOT_AVAILABLE (no external VM/hypervisor in inventory)
MINIO_HOST_EXTERNAL_TO_K8S: YES (required; not on node-01/02/03)

VLAN143_NODE_PATH: PASS (bond0.143 UP on 3 nodes: 101/102/103; route to 172.30.143.0/24 present)
POD_TO_MINIO_PATH: NOT_PROVEN (node-level VLAN143 route proven, but actual Velero/node-agent Pod S3 egress not executed)

MINIO_VM_SIZING: 2vCPU/4GiB/40GiB OS + 100GiB XFS data (MINIMUM); 4vCPU/8GiB + 500GiB (RECOMMENDED)

BUCKET: portal-velero-backup
REGION: ru-west-1
VERSIONING: ENABLED
OBJECT_LOCK: GOVERNANCE / 7 days
RETENTION: 30 days
TLS: PRIVATE_CA / VERIFY_ENABLED
CA_REF: velero/minio-ca
CREDENTIAL_REF: velero/velero-minio-credentials
RPO: 24h
RTO_TARGET: 60m
RESTORE_TEST: weekly

DEPLOYMENT_PREVIEW: READY
RUNTIME_CHANGED: NO
SECRETS_EXPOSED: NO
OWNER_ACTION_REQUIRED: YES

OWNER_ACTIONS:
1. Allocate/create external MinIO VM (outside K8s cluster)
2. Assign VLAN143 / 172.30.143.10 (confirm IP in IPAM)
3. Attach dedicated data volume (>=100 GiB demo / 500 GiB recommended, XFS)
4. Approve single-node MinIO installation
5. Create dedicated least-privilege MinIO access key (not root)
6. Issue TLS cert (PRIVATE_CA) SAN IP=172.30.143.10 + publish CA bundle
7. Create bucket portal-velero-backup (versioning + Object Lock GOVERNANCE 7d at creation)
8. Provide Secret velero/velero-minio-credentials + ConfigMap velero/minio-ca (out-of-band)
9. Authorize P7C-B2 runtime deployment (Velero + BSL + node-agent; Velero VSL for LINSTOR NOT required)

HERMES RESULT: PASS
P7C-B2: NOT AUTHORIZED
P7C-C: NOT AUTHORIZED
P8: NOT AUTHORIZED
P9: NOT AUTHORIZED

STATUS: READY FOR CHATGPT CONNECTOR VERIFICATION
