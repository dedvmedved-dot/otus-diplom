#!/bin/bash
# p5a-drbd-compile-only.sh
# TASK-015-R1: compile-only DRBD module build from the exact official loader image.
# READ-ONLY. Extract /drbd.tar.gz from quay.io/piraeusdatastore/drbd9-resolute:v9.3.2,
# build drbd.ko + drbd_transport_tcp.ko against live host headers in a chroot.
# NEVER: insmod / modprobe drbd / rmmod / make install / dkms install / copy .ko to
# /lib/modules / depmod. Build output only under /tmp/TASK-015-R1.
set -uo pipefail

IMAGE="quay.io/piraeusdatastore/drbd9-resolute:v9.3.2"
KVER=$(uname -r)
WORK=/tmp/TASK-015-R1
ROOTFS="$WORK/rootfs"
SRC="$WORK/src"
OUT="$WORK/out"
HDR="/usr/src/linux-headers-$KVER"

echo "=== compile-only DRBD 9.3.2 (read-only) ==="
echo "kernel=$KVER host=$(hostname)"

# cleanup any stale mounts + dirs
umount -l "$ROOTFS/proc" 2>/dev/null || true
umount -l "$ROOTFS/dev" 2>/dev/null || true
umount -l "$ROOTFS/usr/src" 2>/dev/null || true
umount -l "$ROOTFS/lib/modules/$KVER" 2>/dev/null || true
umount -l "$ROOTFS$HDR" 2>/dev/null || true
rm -rf "$WORK" 2>/dev/null
mkdir -p "$ROOTFS" "$SRC" "$OUT"

# 1. export image rootfs from containerd
echo "[1/5] export loader image rootfs"
cd "$WORK"
ctr -n k8s.io images export loader.tar "$IMAGE" >/dev/null 2>&1 || {
  ctr -n k8s.io images pull "$IMAGE" >/dev/null 2>&1
  ctr -n k8s.io images export loader.tar "$IMAGE" >/dev/null 2>&1
}
mkdir -p extracted
tar xf loader.tar -C extracted 2>/dev/null
cd extracted
LAYERS=$(python3 -c 'import json;print(" ".join(json.load(open("manifest.json"))[0]["Layers"]))')
for L in $LAYERS; do tar xf "$L" -C "$ROOTFS" 2>/dev/null || true; done
cd "$WORK"

# 2. extract drbd source tarball
echo "[2/5] extract /drbd.tar.gz"
cp "$ROOTFS/drbd.tar.gz" "$SRC/"
tar xf "$SRC/drbd.tar.gz" -C "$SRC"
SRCDIR=$(ls -d "$SRC"/drbd-* | head -1)
echo "source dir: $SRCDIR"

# 3. verify headers exist on host (read-only)
echo "[3/5] verify host headers"
[ -d "$HDR" ] || { echo "MISSING headers $HDR"; exit 2; }

# 4. chroot compile (make only, NO install/load)
echo "[4/5] chroot compile (make only)"
mkdir -p "$ROOTFS/proc" "$ROOTFS/dev" "$ROOTFS/tmp" "$ROOTFS/usr/src" "$ROOTFS$HDR" "$ROOTFS/lib/modules/$KVER"
mount --bind -o ro "/usr/src" "$ROOTFS/usr/src" 2>/dev/null || true
mount --bind -o ro "/lib/modules/$KVER" "$ROOTFS/lib/modules/$KVER" 2>/dev/null || true
mount -t proc proc "$ROOTFS/proc" 2>/dev/null || true
mount --bind /dev "$ROOTFS/dev" 2>/dev/null || true
cp -r "$SRCDIR" "$ROOTFS/tmp/drbd-src"

chroot "$ROOTFS" /bin/bash -c "cd /tmp/drbd-src && make -j4 KDIR=/lib/modules/$KVER/build CONFIG_GCC_PLUGINS=n CONFIG_GCC_PLUGIN_STACKLEAK=n" 2>&1 | tail -30
RC=${PIPESTATUS[0]}
echo "make rc=$RC"

# 5. collect produced .ko
echo "[5/5] collect produced modules"
find "$ROOTFS/tmp/drbd-src/drbd" -name 'drbd.ko' -o -name 'drbd_transport_tcp.ko' 2>/dev/null | while read ko; do cp "$ko" "$OUT/"; done
ls -la "$OUT/"

umount -l "$ROOTFS/proc" 2>/dev/null || true
umount -l "$ROOTFS/dev" 2>/dev/null || true
umount -l "$ROOTFS/usr/src" 2>/dev/null || true
umount -l "$ROOTFS/lib/modules/$KVER" 2>/dev/null || true

[ "$RC" = "0" ] || { echo "COMPILE_FAILED"; exit 3; }

echo "=== MODULE METADATA ==="
for ko in "$OUT"/*.ko; do
  echo "--- $ko ---"
  modinfo "$ko" 2>/dev/null | grep -E '^(filename|version|vermagic|srcversion)' || true
done

[ -f "$OUT/drbd.ko" ] && [ -f "$OUT/drbd_transport_tcp.ko" ] || { echo "MISSING_KO"; exit 4; }
echo "COMPILE_ONLY_OK"
