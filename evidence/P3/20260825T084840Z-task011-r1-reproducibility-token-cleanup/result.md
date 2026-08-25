# TASK-011-R1 — result

TASK: TASK-011-R1-P3B2-REPRODUCIBILITY-AND-TOKEN-CLEANUP-FIX
RUN_ID: 20260825T084840Z

## Выполнено
Исправлены оба замечания Connector audit P3B-2 automation (read-only, cluster не менялся).

### Fix #1 — удалена undeclared upload-certs config dependency
- Из команды `kubeadm init phase upload-certs` убран `--config /root/upload-certs-node03-config.yaml`.
- Теперь: `--upload-certs --certificate-key <KEY> --kubeconfig /etc/kubernetes/admin.conf --skip-certificate-key-print`.
- grep на `upload-certs-node03-config` / `--config /root/upload-certs`: 0 matches.
- Certificate key invariant сохранён (generated → upload-certs same key → join config).

### Fix #2 — token cleanup fallback (failure window закрыт)
- Добавлен флаг `p3b2_token_created` (false → true после успешного token create).
- Cleanup теперь резолвит exact ID в два шага:
  1. PRIMARY: hostvars['node-01']['p3b2_bootstrap_token_id']
  2. FALLBACK: exact ID из успешного p3b2_bootstrap_token_raw.stdout (split('.')[0]),
     только при token_created && primary пуст && full-format match.
- Формат-валидация: full token ^[a-z0-9]{6}\.[a-z0-9]{16}$; cleanup ID ^[a-z0-9]{6}$.
- Если token создан, но ID не резолвится → assert fail → rescue → token_cleanup_failed → final FAIL.
- Token delete — только exact ID (нет hardcoded/all-tokens).
- Independent cleanup (block/rescue) сохранён; final explicit fail сохранён.

## READ-ONLY runtime verification (НЕ изменялся)
- control-plane nodes: 3 (node-01/02/03)
- etcd: 3 members started, health 3/3, leader node-01, 0 learners
- kube-vip: 3/3 Running, VIP single-owner (node-01)
- API VIP: TCP/6443 + livez ok 3/3
- CNI: не установлен
- P1/P2 preserved 3/3

Playbook НЕ запускался (только syntax-check + list-tasks).
