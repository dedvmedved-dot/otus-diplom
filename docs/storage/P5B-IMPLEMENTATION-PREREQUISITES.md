# P5B — Implementation Prerequisites (PLAN ONLY)

STATUS: PROPOSED / NOT AUTHORIZED. Ничего не выполняется в P5A.

## Blockers, требующие Architect решения ДО P5B

1. DRBD 9.2.18 deployment model:
   - Astra in-kernel DRBD = 8.4.11 (несовместим с LINSTOR 1.33.2, который требует DRBD 9).
   - Нужен out-of-tree DRBD 9.2.18: LINBIT drbd-9.2.18 source + DKMS, либо prebuilt
     LINBIT package для Astra/kernel 6.1.158.
   - Build toolchain (gcc/make/dkms) отсутствует → P5B должен установить их (host package)
     или использовать prebuilt module. Архитектурное решение требуется.

2. Candidate health verification:
   - smartmontools/sg3-utils отсутствуют. P5B должен получить разрешение установить
     их (read-only tools) до destructive init, либо принять альтернативный метод.

3. DRBD userspace version:
   - versions.lock не фиксирует drbd-utils. Требуется explicit lock перед P5B.

## Required packages/artifacts (exact)

- linstor-operator (piraeus-operator) 2.10.6
  - manifest: https://charts.linstor.io/static/v2.10.6.yaml
  - helm: linstor/linstor-operator
- linstor-server 1.33.2 (bundled)
- linstor-csi 1.11.0 (bundled)
- drbd 9.2.18 (out-of-tree kernel module)
- drbd-utils (version TBD — Architect lock required)
- gcc / make / dkms / linux-headers (build prerequisites, if DKMS model)

## Kernel prerequisites
- headers 6.1.158-1-generic (уже установлены, build link valid)
- toolchain gcc/make/dkms (ОТСУТСТВУЮТ — требуется установка в P5B)
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
