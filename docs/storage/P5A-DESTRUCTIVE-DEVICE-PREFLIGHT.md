# P5A — Destructive Device Preflight

STATUS: PROPOSED / NOT AUTHORIZED

## Candidates (exact immutable identity; kernel path NOT an identifier)

### node-01
- model MZILT3T8HBLS/007, serial S5G0NC0T407845, WWN 0x5002538b724752b0, 3840755982336 bytes, /dev/sdb — clean, eligible=true
- model MZILT3T8HBLS/007, serial S5G0NC0T407844, WWN 0x5002538b724752a0, 3840755982336 bytes, /dev/sdc — clean, eligible=true

### node-02
- model MZILT3T8HBLS/007, serial S5G0NC0T407077, WWN 0x5002538b724722b0, 3840755982336 bytes, /dev/sdb — clean, eligible=true
- model MZILT3T8HBLS/007, serial S5G0NC0T407075, WWN 0x5002538b72472290, 3840755982336 bytes, /dev/sdc — clean, eligible=true

### node-03
- model MZILT3T8HBLS/007, serial S5G0NC0T403246, WWN 0x5002538b72453970, 3840755982336 bytes, /dev/sdb — clean, eligible=true
- model MZILT3T8HBLS/007, serial S5G0NC0T403289, WWN 0x5002538b72453c20, 3840755982336 bytes, /dev/sdc — clean, eligible=true

## Safety checks (all 6/6 PASS)
- TYPE=disk, no children partitions
- not mounted, not swap, not root/boot/home ancestor
- not LVM PV / VG member / LV backing
- not MD RAID member, not multipath member, not dm-crypt
- not active DRBD backing, not Kubernetes PV
- no filesystem/partition/LVM/RAID signature (wipefs -n + blkid -p clean)

## Health (NOT VERIFIED — BLOCKER)
smartctl/sg3-utils absent on all nodes; health gate cannot be verified read-only.

## Protected classes (NOT TARGETED)
- OS disks (sda 447G, root/boot/swap LVM)
- legacy 1.6T disks (sdd-sdi, AL15SEB18EQ) — OUT OF SCOPE, PROTECTED
- virtual devices (sdj, sr0)

## STATEMENT

NO DEVICE IN THIS DOCUMENT IS AUTHORIZED FOR DESTRUCTIVE USE
UNTIL THE CHIEF ARCHITECT ISSUES A SEPARATE P5B AUTHORIZATION.
