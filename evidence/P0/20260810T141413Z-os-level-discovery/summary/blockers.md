# P0 Blockers
RUN_ID: 20260810T141413Z

## BLOCKING FOR P1

BLOCKER-01: node-03 (172.100.10.39 / astra-39) unreachable.
  - BMC: UNREACHABLE
  - SSH: no route / connection refused
  - Required for: full P0 inventory, P1-P9 deployment. 3/3 nodes mandatory.

BLOCKER-02: root/sudo access not available on astraadm user.
  - DMI serial: DENIED (requires root)
  - LVM pvs/vgs/lvs detail: DENIED
  - blkid: empty without sudo
  - Required for: full storage identification, Ceph VG/LV audit

BLOCKER-03: Ceph OSD LVs present on 6 disks per node.
  - 6× 1.6TB Toshiba SAS HDD with active Ceph LVM signatures
  - Requires: ARCHITECT APPROVAL before wipe
  - DO NOT TOUCH per TASK-006 §9

BLOCKER-04: NTP not configured.
  - System clock synchronized: no on both nodes
  - NTP service: inactive
  - Inter-node skew: ~9 seconds
  - Required before etcd (P3): skew ≤ 1 second

## BACKLOG
- NetworkManager-wait-online.service FAILED on both nodes (ens4f0-3 DOWN = expected)
- No /dev/disk/by-id for physical devices (Adaptec RAID hides them)
- Bond uses different ports: 38=ens2f0+f1, 40=ens2f2+f3 (not blocking)
- Ceph tooling not installed (no read-only ceph-volume available)
- nvme-cli not installed (NVMe drives behind SCSI layer)
- VLAN 700 used for management — target VLAN 140/141 per TR not yet configured
