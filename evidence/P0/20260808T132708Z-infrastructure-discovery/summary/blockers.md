# Blockers
RUN_ID: 20260808T132708Z

## BLOCKING FOR P1
BLOCKER-01: SSH access not available on any of the three nodes.
  - All SSH ports tested: 22, 2222, 2200, 8022, 2122, 2022 — Connection refused on all.
  - Required for: OS-level discovery (hostname, OS version, kernel, disk by-id, LVM, filesystem,
    network configuration, time sync), and ALL subsequent stages P1-P9.
  - Without SSH: cannot install packages, configure Kubernetes, deploy DRBD/LINSTOR.

BLOCKER-02: Node 172.100.10.39 unreachable (reported rebooting).
  - Cannot verify: identity, hardware, vendor, serial.
  - Full P0 requires all three nodes identified.

BLOCKER-03: OS-level data NOT VERIFIED.
  - Astra Linux version: NOT VERIFIED
  - Kernel: NOT VERIFIED
  - Disk by-id (/dev/disk/by-id): NOT VERIFIED
  - LVM/RAID/filesystem state: NOT VERIFIED
  - Network addresses (management/DRBD): NOT VERIFIED
  - Time synchronization: NOT VERIFIED

## BACKLOG
- BMC IP addresses (reference 172.30.142.x) not verified against actual BMC management IPs.
- No external dependency checks performed (DNS, NTP, registry, S3, PKI) — requires OS-level access.
- Redfish CPU model reported as "Undefined" for all CPUs (BMC limitation).
- BMC firmware version 10.33.20 — verify compatibility with Astra Linux kernel.
- Storage: 40's OS disks not exported via Redfish (need OS-level lsblk/blkid).
