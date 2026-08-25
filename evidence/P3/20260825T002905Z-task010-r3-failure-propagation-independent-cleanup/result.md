# TASK-010-R3 — result

TASK: TASK-010-R3-P3B1-FAILURE-PROPAGATION-AND-INDEPENDENT-CLEANUP
RUN_ID: 20260825T002905Z

## Выполнено
Playbook p3b1-join-node02-control-plane.yml перестроен на требуемую модель failure propagation:

1. Initialize control-state flags (p3b1_original_failure / join_config_cleanup_failed / token_cleanup_failed = false).
2. rescue: set_fact p3b1_original_failure: true (НЕ debug с failed_when:false — original failure не конвертируется в success).
3. always: два НЕЗАВИСИМЫХ cleanup block/rescue:
   - JoinConfiguration cleanup → свой flag join_config_cleanup_failed
   - bootstrap token cleanup → свой flag token_cleanup_failed
4. Финал: ansible.builtin.fail если original OR join_config_cleanup_failed OR token_cleanup_failed.

Ключевые свойства (static):
- cleanup #1 failure не блокирует cleanup #2 (независимые block/rescue)
- cleanup #2 failure не скрывает cleanup #1 результат
- original failure + оба cleanup failure → final FAIL
- нет ignore_errors на secret cleanup
- нет automatic reset/retry

## Сохранённые инварианты
- env P3B1_*: 0
- cert key / token / CA hash / hostvars flow — без изменений
- kube-vip config, node-03 read-only — без изменений
- 13 no_log на secret-bearing tasks

## READ-ONLY runtime verification (НЕ изменялся)
- control-plane nodes: 2, etcd 2/2 healthy, kube-vip 2/2 single-owner (node-01)
- API readyz ok, node-03 NOT JOINED, P1/P2 preserved

Playbook НЕ запускался (только syntax-check + list-tasks).
