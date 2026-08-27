# P5B — Implementation Prerequisites (PLAN ONLY)

STATUS: PROPOSED / NOT AUTHORIZED. Ничего не выполняется в P5A.

## Resolution status (после TASK-015-R1)

Все блокеры TASK-015 закрыты:
1. DRBD deployment model: locked 9.3.2, compile-only PASS (loader image
   drbd9-resolute:v9.3.2, gcc-15 внутри, host toolchain НЕ требуется).
2. Candidate health: verified 6/6 (read-only SCSI tooling).
3. DRBD userspace: drbd-utils 9.34.3 зафиксирован.

## Required packages/artifacts (exact)

- linstor-operator (piraeus-operator) 2.10.6
  - manifest: https://charts.linstor.io/static/v2.10.6.yaml
  - helm: linstor/linstor-operator
- linstor-server 1.33.2 (bundled)
- linstor-csi 1.11.0 (bundled)
- drbd 9.3.2 (out-of-tree kernel module, loader image drbd9-resolute:v9.3.2)
- drbd-utils 9.34.3 (bundled in piraeus-server:v1.33.2)
- build toolchain: supplied by loader image (gcc-15); host gcc/make/dkms not required

## Kernel prerequisites
- headers 6.1.158-1-generic (уже установлены, build link valid)
- module signing: MODULE_SIG=y (no FORCE), modules_disabled=0, lockdown=none
  → unsigned out-of-tree module load technically permitted.

## Kubernetes artifacts (P5B)
- LINSTOR Operator 2.10.6 (CRDs, controller)
- LINSTOR CSI 1.11.0 (driver)
- StorageClass (после storage pool)

## Candidate device identity resolver procedure
- stable identity (serial + WWN + model + exact bytes) → live lsblk JSON → exactly
  one current /dev path. Никогда по /dev/sdX.

## Rollback boundary
- До destructive init: чистые candidate disks с fingerprint.
- P5B destructive init (LVM PV/VG/thin pool/DRBD metadata) только после explicit
  Architect authorization с allowlist по serial+WWN.

НЕ ВЫПОЛНЯТЬ в P5A.
