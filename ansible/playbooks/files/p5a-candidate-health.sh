#!/bin/bash
# p5a-candidate-health.sh
# TASK-015-R3: FAIL-CLOSED read-only candidate health via SCSI tooling from the
# official piraeus-server image. Composite identity re-resolved by caller.
#
# usage: p5a-candidate-health.sh <resolved_device> <expected_serial> <expected_model>
#
# Exit 0 ONLY on full PASS. Binds minimal char devices + resolved block device only.
set -uo pipefail

DEV="${1:-}"
EXP_SERIAL="${2:-}"
EXP_MODEL="${3:-MZILT3T8HBLS/007}"

[ -n "$DEV" ] || { echo "FAIL: no device"; exit 1; }
[ -n "$EXP_SERIAL" ] || { echo "FAIL: no expected serial"; exit 1; }

ROOTFS=/tmp/sat-inspect/rootfs
[ -d "$ROOTFS" ] || { echo "FAIL: no piraeus-server rootfs"; exit 2; }
[ -x "$ROOTFS/usr/bin/sg_inq" ] || { echo "FAIL: sg_inq missing"; exit 2; }
[ -x "$ROOTFS/usr/bin/sg_logs" ] || { echo "FAIL: sg_logs missing"; exit 2; }

# pre-clean stale mounts (fail-closed: must end clean)
for m in "$ROOTFS/dev" "$ROOTFS/proc"; do
  while mountpoint -q "$m" 2>/dev/null; do umount -l "$m" 2>/dev/null; done
done

mkdir -p "$ROOTFS/dev" "$ROOTFS/proc"

# minimal char devices
for devnode in null zero random urandom; do
  [ -e "/dev/$devnode" ] || { echo "FAIL: /dev/$devnode missing"; exit 3; }
  rm -f "$ROOTFS/dev/$devnode" 2>/dev/null
  mknod "$ROOTFS/dev/$devnode" c $(stat -c '0x%t' "/dev/$devnode") $(stat -c '0x%T' "/dev/$devnode") 2>/dev/null \
    || { echo "FAIL: mknod /dev/$devnode"; exit 3; }
  chmod 666 "$ROOTFS/dev/$devnode" 2>/dev/null
done

# bind only the resolved block device
[ -b "$DEV" ] || { echo "FAIL: $DEV not a block device"; exit 4; }
bname=$(basename "$DEV")
rm -f "$ROOTFS/dev/$bname" 2>/dev/null
mknod "$ROOTFS/dev/$bname" b $(stat -c '0x%t' "$DEV") $(stat -c '0x%T' "$DEV") 2>/dev/null \
  || { echo "FAIL: mknod $bname"; exit 4; }
chmod 660 "$ROOTFS/dev/$bname" 2>/dev/null

# bind proc only (no whole /dev)
mount -t proc proc "$ROOTFS/proc" || { echo "FAIL: mount proc"; exit 5; }

cleanup() { umount "$ROOTFS/proc" 2>/dev/null; rm -f "$ROOTFS/dev/$bname" 2>/dev/null; }
trap cleanup EXIT

# identity
inq=$(chroot "$ROOTFS" /usr/bin/sg_inq "/dev/$bname" 2>&1)
rc=$?
[ $rc -eq 0 ] || { echo "FAIL: sg_inq rc=$rc"; echo "$inq"; exit 6; }
serial=$(echo "$inq" | grep -i 'Unit serial number' | awk -F: '{print $2}' | tr -d '[:space:]')
model=$(echo "$inq" | grep -i 'Product identification' | awk -F: '{print $2}' | tr -d '[:space:]')
[ "$serial" = "$EXP_SERIAL" ] || { echo "FAIL: serial got='$serial' want='$EXP_SERIAL'"; exit 7; }
[ "$model" = "$EXP_MODEL" ] || { echo "FAIL: model got='$model' want='$EXP_MODEL'"; exit 7; }
echo "IDENTITY_OK serial=$serial model=$model"

# temperature
tpage=$(chroot "$ROOTFS" /usr/bin/sg_logs -p 0x0d "/dev/$bname" 2>&1); trc=$?
[ $trc -eq 0 ] || { echo "FAIL: temp rc=$trc"; exit 8; }
cur=$(echo "$tpage" | grep -i 'Current temperature' | grep -oE '[0-9]+' | head -1)
ref=$(echo "$tpage" | grep -i 'Reference temperature' | grep -oE '[0-9]+' | head -1)
[ -n "$cur" ] && [ -n "$ref" ] || { echo "FAIL: temp missing"; exit 8; }
[ "$cur" -lt "$ref" ] || { echo "FAIL: temp $cur >= ref $ref"; exit 8; }
echo "TEMP_OK current=${cur}C reference=${ref}C"

# write errors
wpage=$(chroot "$ROOTFS" /usr/bin/sg_logs -p 0x02 "/dev/$bname" 2>&1); wrc=$?
[ $wrc -eq 0 ] || { echo "FAIL: write rc=$wrc"; exit 9; }
wue=$(echo "$wpage" | grep -i 'Total uncorrected errors' | grep -oE '[0-9]+' | head -1)
[ -n "$wue" ] || { echo "FAIL: write uncorrected missing"; exit 9; }
[ "$wue" = "0" ] || { echo "FAIL: write uncorrected=$wue"; exit 9; }
echo "WRITE_OK uncorrected=$wue"

# read errors
rpage=$(chroot "$ROOTFS" /usr/bin/sg_logs -p 0x03 "/dev/$bname" 2>&1); rrc=$?
[ $rrc -eq 0 ] || { echo "FAIL: read rc=$rrc"; exit 10; }
rue=$(echo "$rpage" | grep -i 'Total uncorrected errors' | grep -oE '[0-9]+' | head -1)
[ -n "$rue" ] || { echo "FAIL: read uncorrected missing"; exit 10; }
[ "$rue" = "0" ] || { echo "FAIL: read uncorrected=$rue"; exit 10; }
echo "READ_OK uncorrected=$rue"

nme=$(chroot "$ROOTFS" /usr/bin/sg_logs -p 0x06 "/dev/$bname" 2>/dev/null | grep -i 'Non-medium error count' | grep -oE '[0-9]+' | head -1)
echo "NON_MEDIUM_COUNT=${nme:-NA}"

echo "HEALTH_PASS serial=$EXP_SERIAL model=$EXP_MODEL temp=${cur}C uncorr_write=0 uncorr_read=0"
exit 0
