# TASK-017 — result

TASK: TASK-017-P5C1-PIRAEUS-DRBD-RUNTIME-BOOTSTRAP
RUN_ID: 20260831T234225Z

## Итог: Piraeus/LINSTOR/DRBD runtime развёрнут. OVERALL = PASS.

## Развёрнуто (все версии совпали с versions.lock)
- Piraeus Operator v2.10.6 (CRDs + operator Deployment Ready)
- LinstorCluster (Applied/Available/Configured=True, satellites 3/3)
- LINSTOR controller 1.33.2 (Running, API reachable)
- LINSTOR satellites 3/3 Online (node-01/02/03)
- LINSTOR CSI 1.11.0 (controller 7/7, node 3/3, CSIDriver present)
- DRBD 9.3.2 runtime loaded 3/3 (vermagic 6.1.158-1-generic, drbd_transport_tcp)
- drbd-utils 9.34.3 (DRBDADM_VERSION)

## Преодолённая runtime-проблема (задокументировано)
1. Control-plane taint: все 3 узла NoSchedule control-plane → добавил toleration
   (operator/gengcert patch + LinstorCluster.spec.tolerations) — штатно для
   control-plane-only кластера.
2. DRBD loader gcc plugin mismatch: drbd9-resolute (gcc 15) vs Astra kernel
   (gcc 12.2.0 + stackleak plugin). Решение — LB_MAKEOPTS="CONFIG_GCC_PLUGINS=n
   CONFIG_GCC_PLUGIN_STACKLEAK=n" через LinstorSatelliteConfiguration podTemplate
   (ровно то, что TASK-015-R1/ADR-003 compile-only доказали). НЕ смена образа/версии.

## Boundaries preserved
- P5B LVM UNCHANGED (6 PV UUID, 3 VG UUID, 3 LV UUID идентичны PRE/POST)
- Project diskful pool = 0 (только DfltDisklessStorPool)
- DRBD data resources = 0
- SC/PV/PVC = 0
- P1-P4 PRE/POST PASS, VIP owner=1, VLAN141 read-only PASS

## Mutation scope
Только authorized Piraeus runtime objects. P5C2 NOT STARTED.

Статусы присваивает только Главный Архитектор после независимого Connector audit.
