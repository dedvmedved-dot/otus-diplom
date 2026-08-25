# TASK-012-R1 — result

TASK: TASK-012-R1-APPROVAL-CONTROLLED-EXECUTION
RUN_ID: 20260825T151414Z

## Итог
Реальная инжекция отказа node-01 выполнена и HA подтверждена. Кластер полностью восстановлен к 3/3.

## Хронология
1. Fresh precheck PASS: control-plane 3/3, etcd 3/3 (leader=node-01), kube-vip 3/3, VIP owner=node-01.
2. probe ConfigMap (phase=baseline) + dead-man (180s) armed.
3. FAILURE INJECTION node-01: systemctl stop kubelet + graceful stop 5 exact containers (kube-vip, apiserver, etcd, controller-manager, scheduler). Result: kubelet inactive, 0/5 targets running.
4. HA GATES:
   - VIP failover: node-01→node-02 (single owner), ≤15s.
   - API recovery: VIP 172.30.140.100:6443 ok, ≤15s.
   - API stability: 30/30 PASS.
   - etcd: 2/2 survivors healthy, новый leader=node-02 (raft term 2→3), quorum 2/3 доступен.
   - API write/read during failure: phase=during-failure PASS.
   - readyz during failure: ping/etcd/etcd-readiness ok.
5. RECOVERY: systemctl start kubelet node-01 → control-plane 3/3, etcd 3/3 healthy, kube-vip 3/3, VIP single-owner (node-02), API 3/3.
6. Cleanup: probe удалён, dead-man timer removed.
7. Post-recovery: P1/P2 preserved 3/3, CNI absent, etcd membership 3 (не изменён), 0 learners.

## Ключевые выводы
- Single-node HA подтверждена: потеря node-01 (kube-vip owner + etcd leader одновременно) не нарушила API и etcd quorum.
- etcd пережил потерю leader: election нового leader (node-02) за <15s, raft term 2→3.
- kube-vip ARP failover: VIP переехал на node-02, single owner, split не наблюдался.
- API write → etcd quorum commit → API read работал во время отказа (phase=during-failure).
- Восстановление node-01 прошло штатно без ручного вмешательства в etcd/kubeadm.

## Примечание по approval
Destructive операция выполнена через проектный Ansible path (host-key verification, StrictHostKeyChecking=yes), НЕ через sshpass -p. Approval получен штатным путём. BYPASS ATTEMPTED: NO.
