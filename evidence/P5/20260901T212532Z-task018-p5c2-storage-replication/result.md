# TASK-018 — result (BLOCKED — требуется решение Архитектора)

TASK: TASK-018-P5C2-STORAGE-POOL-VLAN141-REPLICATION-AND-CSI-FAILOVER
RUN_ID: 20260901T212532Z
BASELINE: c1474aaacd74e8bbdd92df9270cda08d0035bd7a

## OVERALL: BLOCKED (на PHASE 13 — DRBD peer connection)

## Выполнено успешно (авторизованная мутация)

PHASE 6:  LINSTOR node interfaces drbd141 — 3/3 (172.30.141.101/102/103)
PHASE 7:  LinstorNodeConnection p5c2-drbd-vlan141 — Configured=True, protocol C
PHASE 8:  LinstorSatelliteConfiguration p5c2-storage-pool — applied
PHASE 9:  piraeus-thin — 3/3 LVM_THIN Ok (vg_piraeus/thin_piraeus)
PHASE 11: StorageClass piraeus-r2 — applied, exact semantics
PHASE 12: namespace/PVC/writer — PVC Bound, writer Running/Ready,
          EXT4 mounted on node-01, данные + hashes записаны

## Блокер (PHASE 13 — RF=2/Connected не достигнут)

DRBD peer connection остаётся Connecting. dmesg (node-01):

  drbd pvc-... node-02: Configured local address not found, retrying every 10 sec, err=-99
  drbd pvc-... node-03: Configured local address not found, retrying every 10 sec, err=-99

err=-99 = EADDRNOTAVAIL. drbdsetup show: _this_host 172.30.141.101:7000 (VLAN141).

## Корневая причина

Satellite pods в pod network (hostNetwork=false), видят только 10.244.x/32.
VLAN141 (172.30.141.x) не доступен внутри pod → DRBD transport tcp не может
bind 172.30.141.101:7000.

Требуется hostNetwork: true для satellite pods (штатный Piraeus механизм через
LinstorSatelliteConfiguration podTemplate). НЕ входит в авторизацию TASK-018 §26.

## Решение ждёт Архитектора

Кластер оставлен в производственном P5C2 состоянии (pool + nodeconnection +
interfaces + StorageClass — это разрешённое итоговое состояние §23).
Валидационный PVC/writer/test-DRBD-resource остаются (quorum:no), ждут
решения по hostNetwork.

## НЕ делал

- hostNetwork для satellite pods (не авторизовано)
- force/discard-my-data/invalidate
- ручное восстановление split-brain
- удаление производственных P5C2 объектов

Подробности: evidence/.../99-BLOCKER-drbd-vlan141-hostnetwork.txt
