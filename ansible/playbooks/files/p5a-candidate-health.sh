#!/bin/bash
# p5a-candidate-health.sh
# TASK-015-R2: FAIL-CLOSED read-only candidate health via SCSI tooling from the
# official piraeus-server image (ephemeral chroot, NO host install, NO self-test).
#
# usage: p5a-candidate-health.sh <device> <expected_serial> <expected_model>
#
# Exit code 0 ONLY on full PASS; non-zero otherwise. No pipeline masks rc.
#
# NEVER: smartctl -t / sg_format / sg_write* / sdparm --set.
set -uo pipefail

DEV="${1:-}"
EXP_SERIAL="${2:-}"
EXP_MODEL="${3:-MZILT3T8HBLS/007}"

[ -n "$DEV" ] || { echo "FAIL: no device"; exit 1; }
[ -n "$EXP_SERIAL" ] || { echo "FAIL: no expected serial"; exit 1; }

ROOTFS=/tmp/sat-inspect/rootfs
[ -d "$ROOTFS" ] || { echo "FAIL: no piraeus-server rootfs at $ROOTFS"; exit 2; }
[ -x "$ROOTFS/usr/bin/sg_inq" ] || { echo "FAIL: sg_inq missing in rootfs"; exit 2; }
[ -x "$ROOTFS/usr/bin/sg_logs" ] || { echo "FAIL: sg_logs missing in rootfs"; exit 2; }

mkdir -p "$ROOTFS/dev" "$ROOTFS/proc"
# required mounts must succeed (fail-closed)
mount --bind /dev "$ROOTFS/dev" || { echo "FAIL: cannot bind /dev"; exit 3; }
mount -t proc proc "$ROOTFS/proc" || { echo "FAIL: cannot mount proc"; exit 3; }

cleanup() { umount "$ROOTFS/dev" 2>/dev/null; umount "$ROOTFS/proc" 2>/dev/null; }
trap cleanup EXIT

FAIL=0

# --- identity (sg_inq) ---
inq=$(chroot "$ROOTFS" /usr/bin/sg_inq "$DEV" 2>&1)
rc=$?
[ $rc -eq 0 ] || { echo "FAIL: sg_inq rc=$rc"; echo "$inq"; exit 4; }

serial=$(echo "$inq" | grep -i 'Unit serial number' | awk -F: '{print $2}' | tr -d '[:space:]')
model=$(echo "$inq" | grep -i 'Product identification' | awk -F: '{print $2}' | tr -d '[:space:]')

[ "$serial" = "$EXP_SERIAL" ] || { echo "FAIL: serial mismatch got='$serial' want='$EXP_SERIAL'"; exit 5; }
[ "$model" = "$EXP_MODEL" ] || { echo "FAIL: model mismatch got='$model' want='$EXP_MODEL'"; exit 5; }
echo "IDENTITY_OK serial=$serial model=$model"

# --- temperature page 0x0d ---
tpage=$(chroot "$ROOTFS" /usr/bin/sg_logs -p 0x0d "$DEV" 2>&1)
trc=$?
[ $trc -eq 0 ] || { echo "FAIL: sg_logs temp rc=$trc"; echo "$tpage"; exit 6; }
cur=$(echo "$tpage" | grep -i 'Current temperature' | grep -oE '[0-9]+' | head -1)
ref=$(echo "$tpage" | grep -i 'Reference temperature' | grep -oE '[0-9]+' | head -1)
[ -n "$cur" ] || { echo "FAIL: current temperature missing"; exit 7; }
[ -n "$ref" ] || { echo "FAIL: reference temperature missing"; exit 7; }
[ "$cur" -lt "$ref" ] || { echo "FAIL: current temp $cur >= reference $ref"; exit 7; }
echo "TEMP_OK current=${cur}C reference=${ref}C"

# --- write error page 0x02 ---
wpage=$(chroot "$ROOTFS" /usr/bin/sg_logs -p 0x02 "$DEV" 2>&1)
wrc=$?
[ $wrc -eq 0 ] || { echo "FAIL: sg_logs write rc=$wrc"; echo "$wpage"; exit 8; }
wue=$(echo "$wpage" | grep -i 'Total uncorrected errors' | grep -oE '[0-9]+' | head -1)
[ -n "$wue" ] || { echo "FAIL: write uncorrected count missing"; exit 8; }
[ "$wue" = "0" ] || { echo "FAIL: write uncorrected errors=$wue"; exit 8; }
echo "WRITE_OK uncorrected=$wue"

# --- read error page 0x03 ---
rpage=$(chroot "$ROOTFS" /usr/bin/sg_logs -p 0x03 "$DEV" 2>&1)
rrc=$?
[ $rrc -eq 0 ] || { echo "FAIL: sg_logs read rc=$rrc"; echo "$rpage"; exit 9; }
rue=$(echo "$rpage" | grep -i 'Total uncorrected errors' | grep -oE '[0-9]+' | head -1)
[ -n "$rue" ] || { echo "FAIL: read uncorrected count missing"; exit 9; }
[ "$rue" = "0" ] || { echo "FAIL: read uncorrected errors=$rue"; exit 9; }
echo "READ_OK uncorrected=$rue"

# --- non-medium error page 0x06 (informational only, not a media fault) ---
npage=$(chroot "$ROOTFS" /usr/bin/sg_logs -p 0x06 "$DEV" 2>&1)
nme=$(echo "$npage" | grep -i 'Non-medium error count' | grep -oE '[0-9]+' | head -1)
echo "NON_MEDIUM_COUNT=${nme:-NA}"

echo "HEALTH_PASS serial=$EXP_SERIAL model=$EXP_MODEL temp=${cur}C uncorr_write=0 uncorr_read=0"
exit 0
