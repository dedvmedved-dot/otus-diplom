#!/bin/bash
# p5a-candidate-health.sh
# TASK-015-R1: read-only candidate health via SCSI tooling from official
# piraeus-server image (ephemeral chroot, NO host install, NO SMART self-test).
# Uses sg_inq (identity) + sg_logs (temperature + read/write error counters).
# NEVER: smartctl -t / sg_format / sg_write* / sdparm --set.
set -uo pipefail
ROOTFS=/tmp/sat-inspect/rootfs
DEV="$1"
[ -n "$DEV" ] || { echo "usage: $0 <device>"; exit 1; }
[ -d "$ROOTFS" ] || { echo "no piraeus-server rootfs at $ROOTFS"; exit 1; }

mkdir -p "$ROOTFS/dev" "$ROOTFS/proc"
mount --bind /dev "$ROOTFS/dev" 2>/dev/null
mount -t proc proc "$ROOTFS/proc" 2>/dev/null

echo "=== $DEV identity (sg_inq) ==="
chroot "$ROOTFS" /usr/bin/sg_inq "$DEV" 2>&1 | grep -E 'Vendor|Product|revision|Unit serial'

echo "=== $DEV temperature (sg_logs -p 0x0d) ==="
chroot "$ROOTFS" /usr/bin/sg_logs -p 0x0d "$DEV" 2>&1 | grep -iE 'temperature|Current|Reference' || echo "temp page N/A"

echo "=== $DEV write errors (sg_logs -p 0x02) ==="
chroot "$ROOTFS" /usr/bin/sg_logs -p 0x02 "$DEV" 2>&1 | grep -iE 'uncorrected|Total errors' || echo "N/A"

echo "=== $DEV read errors (sg_logs -p 0x03) ==="
chroot "$ROOTFS" /usr/bin/sg_logs -p 0x03 "$DEV" 2>&1 | grep -iE 'uncorrected|Total errors' || echo "N/A"

echo "=== $DEV non-medium errors (sg_logs -p 0x06) ==="
chroot "$ROOTFS" /usr/bin/sg_logs -p 0x06 "$DEV" 2>&1 | grep -iE 'uncorrected|Total|Non-medium' || echo "N/A"

umount "$ROOTFS/dev" 2>/dev/null
umount "$ROOTFS/proc" 2>/dev/null
echo "HEALTH_QUERY_DONE"
