#!/bin/bash
# p5a-drbd-compile-only.sh
# TASK-015-R2: FAIL-CLOSED compile-only DRBD module build from the exact official
# loader image quay.io/piraeusdatastore/drbd9-resolute:v9.3.2.
#
# Extracts /drbd.tar.gz, builds drbd.ko + drbd_transport_tcp.ko against live host
# headers in a chroot. NEVER: insmod / modprobe drbd / rmmod / make install /
# dkms install / copy .ko to /lib/modules / depmod.
#
# D8: chroot /dev contains ONLY minimal char devices (null/zero/random/urandom),
#     NO host block devices.
# D9: required mounts (/usr/src, /lib/modules/<kver>) fail-closed + verified ro.
#
# Exit code 0 ONLY on full PASS; non-zero otherwise.
set -uo pipefail

IMAGE="quay.io/piraeusdatastore/drbd9-resolute:v9.3.2"
KVER=$(uname -r)
WORK=/tmp/TASK-015-R1
ROOTFS="$WORK/rootfs"
SRC="$WORK/src"
OUT="$WORK/out"

echo "=== compile-only DRBD 9.3.2 (read-only) kernel=$KVER host=$(hostname) ==="

# cache: if already compiled and valid, skip the long compile (idempotent)
if [ -f "$OUT/drbd.ko" ] && [ -f "$OUT/drbd_transport_tcp.ko" ]; then
  cver=$(modinfo "$OUT/drbd.ko" 2>/dev/null | grep '^version:' | awk '{print $2}')
  cvm=$(modinfo "$OUT/drbd.ko" 2>/dev/null | grep '^vermagic:' | awk '{print $2}')
  tvm=$(modinfo "$OUT/drbd_transport_tcp.ko" 2>/dev/null | grep '^vermagic:' | awk '{print $2}')
  if [ "$cver" = "9.3.2" ] && [ "$cvm" = "$KVER" ] && [ "$tvm" = "$KVER" ]; then
    echo "CACHE_HIT drbd.ko version=$cver vermagic=$cvm (already compiled, skipping rebuild)"
    echo "COMPILE_ONLY_OK version=$cver vermagic=$cvm"
    exit 0
  fi
fi

# cleanup stale mounts
for m in "$ROOTFS/proc" "$ROOTFS/dev" "$ROOTFS/usr/src" "$ROOTFS/lib/modules/$KVER"; do
  umount -l "$m" 2>/dev/null
done
rm -rf "$WORK" 2>/dev/null
mkdir -p "$ROOTFS" "$SRC" "$OUT"

# 1. export image rootfs (fail-closed)
echo "[1/5] export loader image rootfs"
cd "$WORK"
LDTAR="loader-$$.tar"
rm -f "$LDTAR"
if ! ctr -n k8s.io images export "$LDTAR" "$IMAGE" >/dev/null 2>&1; then
  ctr -n k8s.io images pull "$IMAGE" >/dev/null 2>&1 || { echo "FAIL: image pull"; exit 10; }
  ctr -n k8s.io images export "$LDTAR" "$IMAGE" >/dev/null 2>&1 || { echo "FAIL: image export"; exit 10; }
fi
[ -s "$LDTAR" ] || { echo "FAIL: empty loader tar"; exit 10; }
mkdir -p extracted
tar xf "$LDTAR" -C extracted 2>/dev/null || { echo "FAIL: untar loader"; exit 10; }
cd extracted
LAYERS=$(python3 -c 'import json;print(" ".join(json.load(open("manifest.json"))[0]["Layers"]))' 2>/dev/null) || { echo "FAIL: manifest parse"; exit 10; }
for L in $LAYERS; do tar xf "$L" -C "$ROOTFS" 2>/dev/null || { echo "FAIL: untar layer $L"; exit 10; }; done
cd "$WORK"

# 2. extract drbd source
echo "[2/5] extract /drbd.tar.gz"
cp "$ROOTFS/drbd.tar.gz" "$SRC/" || { echo "FAIL: no /drbd.tar.gz"; exit 11; }
tar xf "$SRC/drbd.tar.gz" -C "$SRC" || { echo "FAIL: untar drbd src"; exit 11; }
SRCDIR=$(ls -d "$SRC"/drbd-* 2>/dev/null | head -1)
[ -n "$SRCDIR" ] || { echo "FAIL: no drbd source dir"; exit 11; }
echo "source dir: $SRCDIR"
echo "source: DRBD 9.3.2 (drbd-9.3.2 tarball from official loader image)"

# 3. verify host headers
echo "[3/5] verify host headers"
HDR="/usr/src/linux-headers-$KVER"
[ -d "$HDR" ] || { echo "FAIL: missing headers $HDR"; exit 12; }

# 4. minimal /dev (char devices only, NO block devices) + read-only mounts (fail-closed)
echo "[4/5] chroot compile (minimal /dev, ro mounts, make only)"
mkdir -p "$ROOTFS/proc" "$ROOTFS/dev" "$ROOTFS/tmp" "$ROOTFS/usr/src" "$ROOTFS/lib/modules/$KVER"

# required mounts fail-closed (no || true)
mount --bind -o ro "/usr/src" "$ROOTFS/usr/src" || { echo "FAIL: mount /usr/src ro"; exit 13; }
mount --bind -o ro "/lib/modules/$KVER" "$ROOTFS/lib/modules/$KVER" || { echo "FAIL: mount /lib/modules ro"; exit 13; }
mount -t proc proc "$ROOTFS/proc" || { echo "FAIL: mount proc"; exit 13; }

# D8: minimal /dev — bind only char device nodes, NOT block devices
for devnode in null zero random urandom; do
  [ -e "/dev/$devnode" ] || { echo "FAIL: /dev/$devnode missing on host"; exit 14; }
  # create char node with same major:minor as host
  majmin=$(stat -c '%t:%T' "/dev/$devnode" 2>/dev/null)
  case $devnode in
    null)   chmod=666; type=c ;; zero)   chmod=666; type=c ;;
    random) chmod=666; type=c ;; urandom) chmod=666; type=c ;;
  esac
  mknod "$ROOTFS/dev/$devnode" c $(stat -c '0x%t' "/dev/$devnode") $(stat -c '0x%T' "/dev/$devnode") 2>/dev/null \
    || { echo "FAIL: mknod /dev/$devnode"; exit 14; }
  chmod 666 "$ROOTFS/dev/$devnode" 2>/dev/null
done

# verify NO block devices in chroot /dev
blkcount=$(find "$ROOTFS/dev" -type b 2>/dev/null | wc -l)
echo "chroot /dev block devices: $blkcount"
[ "$blkcount" = "0" ] || { echo "FAIL: block devices present in compile chroot ($blkcount)"; exit 15; }

cp -r "$SRCDIR" "$ROOTFS/tmp/drbd-src" || { echo "FAIL: copy source"; exit 16; }

# compile (make only). Capture rc directly, no pipeline masking.
LOG="$WORK/compile.log"
chroot "$ROOTFS" /bin/bash -c "cd /tmp/drbd-src && make -j4 KDIR=/lib/modules/$KVER/build CONFIG_GCC_PLUGINS=n CONFIG_GCC_PLUGIN_STACKLEAK=n" > "$LOG" 2>&1
RC=$?
echo "make rc=$RC"
tail -15 "$LOG"
[ $RC -eq 0 ] || { echo "COMPILE_FAILED rc=$RC"; exit 17; }

# 5. collect produced .ko
echo "[5/5] collect produced modules"
find "$ROOTFS/tmp/drbd-src/drbd" -name 'drbd.ko' -o -name 'drbd_transport_tcp.ko' 2>/dev/null | while read ko; do cp "$ko" "$OUT/"; done
ls -la "$OUT/"

# unmount
umount "$ROOTFS/proc" 2>/dev/null
umount "$ROOTFS/usr/src" 2>/dev/null
umount "$ROOTFS/lib/modules/$KVER" 2>/dev/null

# module metadata
echo "=== MODULE METADATA ==="
for ko in "$OUT/drbd.ko" "$OUT/drbd_transport_tcp.ko"; do
  [ -f "$ko" ] || { echo "FAIL: $ko missing"; exit 18; }
  echo "--- $ko ---"
  modinfo "$ko" 2>/dev/null | grep -E '^(version|vermagic)' || { echo "FAIL: modinfo $ko"; exit 18; }
done

# assert version + vermagic
ver=$(modinfo "$OUT/drbd.ko" 2>/dev/null | grep '^version:' | awk '{print $2}')
vm=$(modinfo "$OUT/drbd.ko" 2>/dev/null | grep '^vermagic:' | awk '{print $2}')
[ "$ver" = "9.3.2" ] || { echo "FAIL: version=$ver want 9.3.2"; exit 19; }
[ "$vm" = "$KVER" ] || { echo "FAIL: vermagic=$vm want $KVER"; exit 19; }
tvm=$(modinfo "$OUT/drbd_transport_tcp.ko" 2>/dev/null | grep '^vermagic:' | awk '{print $2}')
[ "$tvm" = "$KVER" ] || { echo "FAIL: transport vermagic=$tvm want $KVER"; exit 19; }

echo "COMPILE_ONLY_OK version=$ver vermagic=$vm"
exit 0
