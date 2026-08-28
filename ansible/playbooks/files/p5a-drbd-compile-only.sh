#!/bin/bash
# p5a-drbd-compile-only.sh
# TASK-015-R3: FORCED FRESH compile-only DRBD module build from the exact official
# loader image quay.io/piraeusdatastore/drbd9-resolute:v9.3.2.
#
# FRESH: no cache, always re-extracts and re-runs make.
# READ-ONLY: /usr/src and /lib/modules/<kver> mounted ro (verified).
# Chroot /dev contains ONLY char devices (null/zero/random/urandom), 0 block devices.
# NEVER: insmod / modprobe drbd / rmmod / make install / dkms install /
# copy .ko to /lib/modules / depmod.
# Exit 0 ONLY on full PASS; non-zero otherwise.
set -uo pipefail

IMAGE="quay.io/piraeusdatastore/drbd9-resolute:v9.3.2"
KVER=$(uname -r)
WORK=/tmp/TASK-015-R1
ROOTFS="$WORK/rootfs"
SRC="$WORK/src"
OUT="$WORK/out"

echo "=== FRESH compile-only DRBD 9.3.2 (read-only) kernel=$KVER host=$(hostname) ==="

# cleanup stale mounts + previous output (fresh)
for m in "$ROOTFS/proc" "$ROOTFS/dev" "$ROOTFS/usr/src" "$ROOTFS/lib/modules/$KVER"; do
  umount -l "$m" 2>/dev/null
done
rm -rf "$WORK" 2>/dev/null
mkdir -p "$ROOTFS" "$SRC" "$OUT"
[ -f "$OUT/drbd.ko" ] && { echo "FAIL: stale .ko present"; exit 1; }

# 1. export image rootfs (fail-closed)
echo "[1/6] export loader image rootfs"
cd "$WORK"
LDTAR="loader-fresh.tar"
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
for L in $LAYERS; do tar xf "$L" -C "$ROOTFS" 2>/dev/null || { echo "FAIL: untar layer"; exit 10; }; done
cd "$WORK"

# 2. extract drbd source
echo "[2/6] extract /drbd.tar.gz"
cp "$ROOTFS/drbd.tar.gz" "$SRC/" || { echo "FAIL: no drbd.tar.gz"; exit 11; }
tar xf "$SRC/drbd.tar.gz" -C "$SRC" || { echo "FAIL: untar drbd src"; exit 11; }
SRCDIR=$(ls -d "$SRC"/drbd-* 2>/dev/null | head -1)
[ -n "$SRCDIR" ] || { echo "FAIL: no drbd source dir"; exit 11; }
echo "source: DRBD 9.3.2 ($SRCDIR)"

# 3. verify host headers
echo "[3/6] verify host headers"
HDR="/usr/src/linux-headers-$KVER"
[ -d "$HDR" ] || { echo "FAIL: missing headers $HDR"; exit 12; }

# 4. minimal /dev + read-only mounts (fail-closed, ro verified)
echo "[4/6] minimal /dev + ro mounts"
mkdir -p "$ROOTFS/proc" "$ROOTFS/dev" "$ROOTFS/tmp" "$ROOTFS/usr/src" "$ROOTFS/lib/modules/$KVER"

mount --bind -o ro "/usr/src" "$ROOTFS/usr/src" || { echo "FAIL: mount /usr/src ro"; exit 13; }
mount --bind -o ro "/lib/modules/$KVER" "$ROOTFS/lib/modules/$KVER" || { echo "FAIL: mount /lib/modules ro"; exit 13; }
mount -t proc proc "$ROOTFS/proc" || { echo "FAIL: mount proc"; exit 13; }

# D5: verify effective ro flags
usr_ro=$(findmnt -n -o OPTIONS "$ROOTFS/usr/src" 2>/dev/null)
mod_ro=$(findmnt -n -o OPTIONS "$ROOTFS/lib/modules/$KVER" 2>/dev/null)
echo "mount /usr/src OPTIONS=$usr_ro"
echo "mount /lib/modules/$KVER OPTIONS=$mod_ro"
echo "$usr_ro" | grep -q '^ro' || { echo "FAIL: /usr/src not ro"; exit 14; }
echo "$mod_ro" | grep -q '^ro' || { echo "FAIL: /lib/modules not ro"; exit 14; }

# D12: minimal /dev — char nodes only, NO block devices
for devnode in null zero random urandom; do
  [ -e "/dev/$devnode" ] || { echo "FAIL: /dev/$devnode missing"; exit 15; }
  rm -f "$ROOTFS/dev/$devnode" 2>/dev/null
  mknod "$ROOTFS/dev/$devnode" c $(stat -c '0x%t' "/dev/$devnode") $(stat -c '0x%T' "/dev/$devnode") 2>/dev/null \
    || { echo "FAIL: mknod /dev/$devnode"; exit 15; }
  chmod 666 "$ROOTFS/dev/$devnode" 2>/dev/null
done

blkcount=$(find "$ROOTFS/dev" -type b 2>/dev/null | wc -l)
echo "chroot /dev block devices: $blkcount"
[ "$blkcount" = "0" ] || { echo "FAIL: block devices present ($blkcount)"; exit 16; }
for b in sda sdb sdc; do
  [ -e "$ROOTFS/dev/$b" ] && { echo "FAIL: /dev/$b present in chroot"; exit 16; }
done
echo "block isolation OK: sda/sdb/sdc absent"

cp -r "$SRCDIR" "$ROOTFS/tmp/drbd-src" || { echo "FAIL: copy source"; exit 17; }

# 5. fresh make (rc direct)
echo "[5/6] fresh make"
LOG="$WORK/compile.log"
chroot "$ROOTFS" /bin/bash -c "cd /tmp/drbd-src && make -j4 KDIR=/lib/modules/$KVER/build CONFIG_GCC_PLUGINS=n CONFIG_GCC_PLUGIN_STACKLEAK=n" > "$LOG" 2>&1
RC=$?
echo "make rc=$RC"
tail -15 "$LOG"
[ $RC -eq 0 ] || { echo "COMPILE_FAILED rc=$RC"; exit 18; }

# 6. collect + verify
echo "[6/6] collect .ko + modinfo"
find "$ROOTFS/tmp/drbd-src/drbd" -name 'drbd.ko' -o -name 'drbd_transport_tcp.ko' 2>/dev/null | while read ko; do cp "$ko" "$OUT/"; done
ls -la "$OUT/"

umount "$ROOTFS/proc" 2>/dev/null
umount "$ROOTFS/usr/src" 2>/dev/null
umount "$ROOTFS/lib/modules/$KVER" 2>/dev/null

for ko in "$OUT/drbd.ko" "$OUT/drbd_transport_tcp.ko"; do
  [ -f "$ko" ] || { echo "FAIL: $ko missing"; exit 19; }
  modinfo "$ko" 2>/dev/null | grep -E '^(version|vermagic)' || { echo "FAIL: modinfo $ko"; exit 19; }
done

ver=$(modinfo "$OUT/drbd.ko" 2>/dev/null | grep '^version:' | awk '{print $2}')
vm=$(modinfo "$OUT/drbd.ko" 2>/dev/null | grep '^vermagic:' | awk '{print $2}')
tvm=$(modinfo "$OUT/drbd_transport_tcp.ko" 2>/dev/null | grep '^vermagic:' | awk '{print $2}')
[ "$ver" = "9.3.2" ] || { echo "FAIL: version=$ver"; exit 20; }
[ "$vm" = "$KVER" ] || { echo "FAIL: vermagic=$vm want $KVER"; exit 20; }
[ "$tvm" = "$KVER" ] || { echo "FAIL: transport vermagic=$tvm want $KVER"; exit 20; }

echo "FRESH_COMPILE_OK version=$ver vermagic=$vm"
exit 0
