# P5B — Storage Preparation (LVM Thin)

STATUS: AUTHORIZED (TASK-016). Destructive scope: pvcreate + vgcreate +
lvcreate thin-pool on exactly six authorized devices.

## Architecture
Per node: 2 whole-disk PVs → VG `vg_piraeus` → thin pool `thin_piraeus` at 90%VG.
No partitions, filesystem, mdraid, LUKS, multipath, striping.

Future Piraeus/LINSTOR binds to existing VG/thin pool; must NOT raw-device initialize.

## Authorized devices (full composite identity, never /dev/sdX)
See inventory/storage-p5b-authorized-devices.yaml.

node-01: S5G0NC0T407845 / 0x5002538b724752b0, S5G0NC0T407844 / 0x5002538b724752a0
node-02: S5G0NC0T407077 / 0x5002538b724722b0, S5G0NC0T407075 / 0x5002538b72472290
node-03: S5G0NC0T403246 / 0x5002538b72453970, S5G0NC0T403289 / 0x5002538b72453c20
All: MZILT3T8HBLS/007, 3840755982336 bytes.

## Safety model
- p5b_mode=authorized-destructive-storage-prep (only value permitting writes)
- composite identity re-resolved immediately before EVERY destructive command
- aggregate gate: all 6 pass before any node is destroyed
- serial: 1 (node-01 → 02 → 03), STOP on first destructive failure
- forbidden: pvcreate -ff, wipefs -a, blkdiscard, dd of=, mkfs, mkswap

## Idempotency
- full expected state → ALREADY_PREPARED (validate, do not recreate)
- partial/mismatched → STOP, no auto-repair
