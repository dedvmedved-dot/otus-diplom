# TASK-010-R2 — result

TASK: TASK-010-R2-P3B1-FAILURE-PATH-CLEANUP-GUARANTEE
RUN_ID: 20260824T230039Z

## Выполнено
1. Playbook p3b1-join-node02-control-plane.yml перестроен на block/rescue/always:
   - node-01 credential generation (delegated, delegate_facts) и node-02 join path
     объединены в один play с блоком, чтобы `always:` гарантированно выполнялся
     на всех exit paths.
   - always: Remove temporary JoinConfiguration (file state=absent, no_log)
   - always: Delete exact generated bootstrap token (delegate_to node-01, when defined, no_log)
   - rescue: только фиксирует ошибку (debug), без kubeadm reset/retry/etcd remediation.
2. Cleanup tasks НЕ имеют ignore_errors → cleanup failure = automation FAIL.

## Сохранённые инварианты
- certificate key flow (kubeadm certs certificate-key → upload-certs same key → join config)
- bootstrap token flow (create → join config → cleanup exact ID)
- CA hash computed internally
- hostvars node-01 → node-02
- env P3B1_* references: 0
- 13 no_log на secret-bearing tasks

## READ-ONLY runtime verification (НЕ изменялся)
- control-plane nodes: 2 (node-01, node-02)
- etcd: 2 members started, health 2/2
- kube-vip: 2/2 Running, single-owner (node-01)
- API readyz: ping/etcd ok
- node-03: NOT JOINED
- P1/P2 preserved

Playbook НЕ запускался (только syntax-check + list-tasks).
