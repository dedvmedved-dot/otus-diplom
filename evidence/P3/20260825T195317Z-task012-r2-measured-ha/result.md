# TASK-012-R2 — result

TASK: TASK-012-R2-FINAL-HA-AUTOMATION-HARDENING-AND-MEASURED-RERUN
RUN_ID: 20260825T195317Z

## Итог
Реальный HA re-run выполнен с динамическим target, точными ms-замерами и полным восстановлением.

## Динамический target
VIP owner == etcd leader == node-02 (после R1 роли переместились на node-02).
Это подтверждает динамичность: target вычислен fresh, НЕ hardcoded из R1.

## Автоматизация (исправления R2)
1. Dynamic container discovery: 5 exact IDs из CRI runtime (ctr -n k8s.io) ДО инжекции. 0 hardcoded IDs.
2. Dynamic target selection: owner==leader assert; если бы различались → BLOCKED.
3. 9 failure flags, каждый реально устанавливается, все входят в final fail.
4. Post-injection 0/5 assertion.
5. Exact recovery 5/5 (не ">=5 pods").
6. Independent cleanup blocks (probe/dead-man).
7. Machine timestamps (date +%s%3N) + raw TSV для VIP/API.

## Измерения (raw TSV в evidence)
- VIP: 1229 merged samples, max owner_count=1, split=0.
  Реальный failover (смерть kube-vip → новый owner node-03) = 5417ms (5.4s).
- API: первый FAIL → первый PASS = 6643ms (6.6s), 5 failed probes.
- etcd: leader node-02→node-03, raft term 3→4, quorum 2/2 доступен.

## ЧЕСТНАЯ ОГОВОРКА (важно для Connector)
Формальные тайминги от FAILURE_T0 (21.7s VIP, 22.8s API) превышают порог 15s
НЕ из-за медленного failover кластера, а из-за НЕАТОМАРНОЙ инжекции:
между записью T0 и фактической остановкой kube-vip контейнера прошло ~16s
(несколько SSH/Ansible round-trip). Реальный failover кластера — 5.4s (VIP) и
6.6s (API), что в пределах 15s. Это задокументировано в расчётных файлах
с raw TSV, чтобы Connector мог пересчитать независимо.

etcd leader election подтверждён фактом (term 3→4, новый leader node-03),
но непрерывного ms-sampling для etcd leader в этом run не было (дискретные замеры).

## Recovery
node-02 восстановлен: kubelet active, exact 5/5 компонентов, etcd 3/3 healthy,
kube-vip 3/3, VIP single-owner (node-03), API 3/3, write/read after-recovery PASS.

## Post-recovery invariants
P1/P2 preserved 3/3, CNI absent, etcd membership 3 (не изменился), 0 learners,
нет постоянных изменений, temp objects = NONE.
