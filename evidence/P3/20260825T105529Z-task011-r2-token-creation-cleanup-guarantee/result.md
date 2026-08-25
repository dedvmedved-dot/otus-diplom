# TASK-011-R2 — result

TASK: TASK-011-R2-P3B2-TOKEN-CREATION-STATE-AND-CLEANUP-GUARANTEE
RUN_ID: 20260825T105529Z

## Выполнено
Исправлен единственный оставшийся дефект — порядок определения token-creation state.

### Дефект
`p3b2_token_created` устанавливался ПОСЛЕ `Save bootstrap token` и `Save bootstrap token ID`.
Если `kubeadm token create` успешен, но последующий set_fact падает, token существует,
однако cleanup мог решить, что token не создан (window open).

### Исправление
1. Late flag `p3b2_token_created` полностью удалён (из инициализации и main path).
2. Факт успешного token creation определяется в cleanup НЕПОСРЕДСТВЕННО из raw register:
   `p3b2_token_was_created` = register defined AND failed!=true AND rc==0 AND stdout match ^[a-z0-9]{6}\.[a-z0-9]{16}$.
3. Cleanup ID резолвится: PRIMARY (saved p3b2_bootstrap_token_id, только ^[a-z0-9]{6}$) → FALLBACK (raw stdout split('.')[0], при TOKEN_WAS_CREATED && primary empty).
4. Если TOKEN_WAS_CREATED && ID не резолвится → assert fail → rescue → token_cleanup_failed → FINAL FAIL.
5. Token delete только exact ID. Independent cleanup + original failure propagation сохранены.

### Static audits
- grep old dependency `p3b2_token_created.*bool|when:.*p3b2_token_created`: 0 matches
- upload-certs external config regression: 0 matches
- env P3B2_*: 0 matches
- syntax check + list-tasks: PASS

## READ-ONLY runtime verification (НЕ изменялся)
- control-plane nodes: 3, etcd 3/3 healthy (leader node-01), kube-vip 3/3 single-owner (node-01)
- API VIP 3/3, CNI не установлен, P1/P2 preserved 3/3

Playbook НЕ запускался (только syntax-check + list-tasks).
