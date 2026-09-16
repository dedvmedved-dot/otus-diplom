# P7C-B2A — MinIO VM Sizing (single-node, demo PAK)

Primary recommendation only (no over-sizing).

MINIMUM_FOR_DEMO:
  vCPU: 2
  RAM: 4 GiB
  OS: Astra Linux SE 1.8 (or Debian/Ubuntu LTS) minimal
  system disk: 40 GiB
  MinIO data disk: 100 GiB (dedicated volume)
  filesystem: XFS (data disk)
  network: 1 vNIC on VLAN143 (172.30.143.10/24)
  backup capacity assumption: ~50 GiB demo backup corpus (PVC data via CSI data movement)

RECOMMENDED:
  vCPU: 4
  RAM: 8 GiB
  OS: Astra Linux SE 1.8 minimal
  system disk: 40 GiB
  MinIO data disk: 500 GiB (dedicated volume, XFS)
  network: 1 vNIC on VLAN143
  backup capacity assumption: ~100-200 GiB working set + 30-day retention
  growth reserve: ~2x (500 GiB covers 30d retention of daily 24h RPO backups)

Notes:
- Single-node MinIO = sufficient for backup-function demonstration (not HA).
- XFS recommended for MinIO data (stable, well-tested).
- No VM creation performed in this task.
