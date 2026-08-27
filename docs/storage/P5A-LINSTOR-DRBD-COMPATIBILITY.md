# P5A — LINSTOR / DRBD Compatibility Matrix

STATUS: PROPOSED / NOT AUTHORIZED (read-only preflight)

| Layer | Required | Actual / Verified | Evidence | Result |
|---|---|---|---|---|
| Astra Linux | 1.8.5.46 | 1.8.5.46 (build_version) | /etc/astra/build_version 3/3 | VERIFIED |
| kernel | 6.1.158-1-generic | 6.1.158-1-generic | uname -r 3/3 | VERIFIED |
| arch | x86_64 | x86_64 | uname -m / dpkg 3/3 | VERIFIED |
| kernel headers | exact kernel | 6.1.158-1-generic, build link valid | /lib/modules/build 3/3 | PASS |
| build toolchain (gcc/make/dkms) | required for DRBD out-of-tree | gcc=MISSING make=MISSING dkms=MISSING | command -v 3/3 | NOT AVAILABLE |
| module signing | load permitted | modules_disabled=0, lockdown=none, MODULE_SIG=y (no FORCE) | /proc, /boot/config | PASS (unsigned load permitted) |
| DRBD | 9.2.18 | in-kernel module = 8.4.11 (NOT 9.2.18) | modinfo drbd 3/3 | NOT VERIFIED (needs out-of-tree 9.2.18) |
| DRBD userspace | explicit mapping | drbd-utils version absent from versions.lock | versions.lock | AMBIGUOUS — ADR required |
| LINSTOR | 1.33.2 | bundled in operator 2.10.6 | LINBIT release notes | VERIFIED |
| LINSTOR CSI | 1.11.0 | bundled in operator 2.10.6 | LINBIT release notes | VERIFIED |
| LINSTOR Operator | 2.10.6 | piraeus-operator 2.10.6 | LINBIT/GitHub | VERIFIED |
| Kubernetes | 1.36.2 | 1.36.2 live | kubectl | VERIFIED |
| K8s compat | — | LINBIT runs LINSTOR on K8s 1.36 (documented) | LINBIT blog | COMPATIBLE |
| DRBD network | VLAN141 | 6/6 peer paths, 0% loss, MTU 1500 consistent | ping -I bond1.141 | PASS |
| candidate disks | 6 exact | 6/6 exact unique identity | lsblk WWN/SERIAL | PASS |
| candidate safety | 6 clean | 6/6 no mount/LVM/RAID/MP/signature | wipefs -n etc | PASS |
| candidate health | 6 SMART PASS | smartctl/sg3-utils NOT AVAILABLE | command -v | NOT VERIFIED |

## Блокеры (P5A = BLOCKED)

1. **DRBD 9.2.18 kernel compatibility: NOT VERIFIED.** Astra Linux SE 1.8.5.46
   поставляет in-kernel DRBD 8.4.11. Locked DRBD = 9.2.18 (другая мажорная ветка)
   требует out-of-tree модуля (LINBIT DKMS/package). Build toolchain (gcc/make/dkms)
   отсутствует на всех 3 узлах → compile-only test невозможен без установки
   (запрещено в P5A). Требуется Architect решение: DKMS package vs prebuilt,
   и подтверждение совместимости 9.2.18 с kernel 6.1.158.

2. **Candidate health: NOT VERIFIED.** smartctl, sg_inq, sg_logs, sdparm, lsscsi
   отсутствуют на всех 3 узлах; установка запрещена в P5A. Без SMART-инструмента
   health gate не может быть верифицирован. Требуется Architect разрешение
   установить smartmontools/sg3-utils (read-only tools) до P5B, либо принять
   альтернативный health-метод.

3. **DRBD userspace version: AMBIGUOUS.** versions.lock не фиксирует drbd-utils
   версию. Требуется Architect clarification перед P5B.

## Не-блокеры (PASS)

- Точные identity 6/6, все безопасны (не использованы, без сигнатур).
- DRBD network 6/6, bond 802.3ad, MTU 1500 consistent.
- P1-P4 preserved, no destructive action.
- Kubernetes 1.36.2 совместим с LINSTOR стеком (LINBIT документирует 1.36).
