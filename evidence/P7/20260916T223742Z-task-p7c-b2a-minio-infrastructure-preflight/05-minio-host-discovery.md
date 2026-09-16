# P7C-B2A — MinIO Host Discovery (external to K8s)

Requirement: MinIO must run OUTSIDE the Kubernetes cluster being backed up
(not on node-01/02/03, not as a workload in this cluster).

Search performed (read-only):
- repo inventory (`docs/p0/infrastructure-passport.md`, `access-requirements.md`): only
  node-01/02/03 (K8s nodes) + BMC (172.100.10.x / VLAN142) documented.
- grep for hypervisor/proxmox/esxi/vmware/kvm/libvirt/utility-VM/backup-server: NOT FOUND.
- no external server / dedicated backup VM / utility VM referenced anywhere.

Candidates found: NONE

MINIO_HOST = NOT_AVAILABLE
OWNER_ACTION_REQUIRED = CREATE_EXTERNAL_VM

The 3 K8s nodes are NOT eligible (task forbids placing MinIO on node-01/02/03 or
as a cluster workload). A dedicated external VM must be provisioned by the Owner.
