# TASK-015 / P5A — result

TASK: TASK-015-P5A-LINSTOR-DRBD-COMPATIBILITY-AND-DESTRUCTIVE-STORAGE-PREFLIGHT
RUN_ID: 20260827T212252Z
MODE: READ-ONLY

## Итог: BLOCKED — ARCHITECT DECISION REQUIRED

Read-only preflight выполнен полностью, без единой destructive операции. Все
storage/network/identity/security gates PASS. Два блокера требуют решения Архитектора.

## Что PASSED (read-only evidence)
- P1-P4 cluster: nodes 3/3, calico 3/3, coredns 2/2/2, etcd 3, VIP owner=1, readyz ok.
- Platform: Astra 1.8.5.46 (build_version 3/3), kernel 6.1.158-1-generic, x86_64.
- Kernel headers exact match + build link valid. Module security: unsigned load permitted.
- DRBD network: bond 802.3ad ens2f2+ens2f3, VLAN141, MTU 1500, connectivity 6/6 (0% loss).
- Candidate identity: 6/6 exact unique (serial+WWN+model+bytes).
- Candidate safety: 6/6 clean (no mount/swap/root/LVM/RAID/MP/signature).
- Candidate fingerprint: 12/12 unchanged (P5A nothing mutated).
- Protected devices: 0 touched. Destructive commands: 0. Packages: 0.
- Kubernetes storage state: clean (0 SC/CSI/PV/PVC/LINSTOR CRD).
- Releases verified upstream: operator 2.10.6, LINSTOR 1.33.2, CSI 1.11.0, DRBD 9.2.18.
- Kubernetes 1.36.2 compatibility: COMPATIBLE (LINBIT documented).

## BLOCKERS
1. **DRBD 9.2.18 kernel compatibility: NOT VERIFIED.**
   Astra in-kernel DRBD = 8.4.11 (не 9.2.18). DRBD 9.2.18 требует out-of-tree
   модуля. Build toolchain (gcc/make/dkms) отсутствует на всех узлах → compile-only
   test невозможен без установки (запрещено). Нет официального Astra-пакета DRBD 9.2.18.
2. **Candidate health: NOT VERIFIED.**
   smartctl/sg3-utils/sdparm/lsscsi отсутствуют на всех узлах; установка запрещена.
   Health gate не может быть верифицирован read-only.
3. (вспомогательный) **DRBD userspace version AMBIGUOUS** — drbd-utils не в versions.lock.

## ADR proposal
docs/architecture/ADR-PROPOSAL-P5-drbd-deployment-model.md (PROPOSED / NOT APPROVED):
- выбор deployment model DRBD 9.2.18 (DKMS build vs prebuilt package);
- drbd-utils version lock;
- разрешение установить read-only health tools до P5B.

## Артефакты
- inventory/storage-p5-candidates.yaml (PROPOSED_NOT_AUTHORIZED, 6 candidates)
- docs/storage/P5A-LINSTOR-DRBD-COMPATIBILITY.md
- docs/storage/P5A-DESTRUCTIVE-DEVICE-PREFLIGHT.md
- docs/storage/P5B-IMPLEMENTATION-PREREQUISITES.md
- ansible/playbooks/p5a-linstor-drbd-preflight.yml (read-only)
- ADR proposal

## Статус
BLOCKED. Требуется решение Главного Архитектора. Никакая destructive операция,
установка пакета или загрузка модуля не выполнялась.
