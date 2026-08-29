# TASK-015-R6 — result

TASK: TASK-015-R6-P5A-DM-AND-CEPH-FAIL-CLOSED-FINAL-CLOSURE
RUN_ID: 20260829T145811Z

## Итог: DM и Ceph gates приведены к fail-closed. OVERALL = PASS.

## Исправленные дефекты (D1-D2)
- D1: dmsetup ls rc=0 required (иначе DM_QUERY_FAIL exit 1); каждая map deps rc=0
     required (иначе DM_DEPS_FAIL); только пустой stdout → DM_MAPS=0 PASS.
     Больше не «rc != 0 → пустой список → PASS».
- D2: Ceph OSD block/block.db/block.wal — readlink -f rc=0 required → lsblk PKNAME
     ancestry walk до whole disk → compare candidate kname. Больше не прямое
     сравнение строки /dev/sdX.

## Чистый R6 run (14-r6-playbook-run.txt)
PLAY RECAP: node-01 ok=10 skipped=12, node-02/03 ok=6 skipped=5; failed=0 unreachable=0.
Режим final-dm-ceph: mode gate, minimal cluster guard (nodes=3+readyz=ok),
composite resolver 6/6, holders 6/6=0, DM deps (ls rc=0, все deps rc=0, dependency
(8:3)=sda3 OS-диск, кандидаты clear), Ceph (pvs rc=0, 0 tags, 0 OSD links,
ceph-volume UNAVAILABLE), K8s storage clean. Full P1-P4 regression skipped (R5 accepted).

## Технические решения
- ceph-volume отсутствует → UNAVAILABLE (R4 wipefs/blkid CLEAN уже Connector-verified).
- DRBD compile/health/fingerprint НЕ выполнялись.

## Статус
versions.lock и ADR-003 не изменялись. Никакой destructive операции.
Статусы присваивает только Главный Архитектор после независимого Connector audit.
