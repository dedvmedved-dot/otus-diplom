# TASK-015-R1 — result

TASK: TASK-015-R1-P5A-DRBD-BASELINE-REALIGNMENT-AND-COMPATIBILITY-CLOSURE
RUN_ID: 20260827T222100Z

## Итог: все блокеры TASK-015 закрыты. OVERALL = PASS.

## 1. DRBD baseline realignment (ADR-003)
Официальный changelog piraeus-operator v2.10.6 (2026-05-05) указывает DRBD 9.3.2,
НЕ 9.2.18. versions.lock: drbd 9.2.18 → 9.3.2; drbd_utils 9.34.3 добавлен.
ADR-PROPOSAL-P5-drbd-deployment-model → REJECTED/SUPERSEDED.
ADR-003-P5-drbd-operator-version-alignment → APPROVED.

## 2. DRBD 9.3.2 kernel compatibility (compile-only 3/3 PASS)
Из официального loader image quay.io/piraeusdatastore/drbd9-resolute:v9.3.2
(digest sha256:1856f671...), /drbd.tar.gz (drbd-9.3.2) собран против live headers
6.1.158-1-generic в chroot с read-only bind-mount /usr/src + /lib/modules.
Результат на всех 3 узлах: make rc=0, drbd.ko + drbd_transport_tcp.ko,
version=9.3.2, vermagic=6.1.158-1-generic. Module NOT installed/loaded.
(Замечание: host gcc/make/dkms отсутствуют; compile выполнен внутри loader image
gcc-15 с CONFIG_GCC_PLUGINS=n — ядро собрано gcc 12, плагин stackleak несовместим
с gcc 15; это задокументированный технический нюанс, не блокер.)

## 3. DRBD userspace: drbd-utils 9.34.3
Из piraeus-server:v1.33.2 (digest sha256:0db38ed0...) — drbdadm DRBDADM_VERSION=9.34.3.
Зафиксировано в versions.lock.

## 4. Candidate health 6/6 PASS (read-only SCSI)
apt install smartmontools/sg3-utils/lsscsi невозможен (Astra repos закомментированы,
CDROM пуст, download.astralinux.ru 403). Health закрыт read-only SCSI tooling
(sg_inq + sg_logs 0x0d/0x02/0x03) из официального piraeus-server image:
uncorrected media errors = 0, temperature 19-21 C (ref 74 C).

## 5. Kubernetes 1.36.2 compatibility: PASS
Официальный manifest v2.10.6 (3109 строк): только admissionregistration/v1,
apiextensions/v1, apps/v1, rbac/v1, v1 — все присутствуют в live api-versions.

## 6. Candidate resolver + safety + fingerprint
- 4-field resolver (serial+WWN+model+size+TYPE): 6/6 exact unique.
- Full safety: 6/6 clean (no mount/swap/root/LVM/RAID/MP/dm-crypt/holder/signature).
- Fingerprint first+last 1MiB: 12/12 unchanged (P5A R1 ничего не мутировал).

## 7. Eligibility
inventory/storage-p5-candidates.yaml: eligible=true (P5A_VERIFIED),
destructive_authorized=false (все). P5B НЕ авторизован.

## 8. P1-P4 preserved
pre и post check: nodes 3/3, calico 3/3, coredns 2/2/2, etcd 3, VIP owner=1, readyz ok.

## Статус
Никакая destructive операция не выполнялась. DRBD модуль не загружался/не
устанавливался. Статусы присваивает только Главный Архитектор.
