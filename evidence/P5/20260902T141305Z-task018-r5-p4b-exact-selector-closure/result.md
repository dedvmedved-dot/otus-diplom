# TASK-018-R5 — result

TASK: TASK-018-R5 P4B EXACT SELECTOR FAIL-CLOSED CLOSURE
RUN_ID: 20260902T141305Z
BASELINE: 309e831de8a1248145eb7b1eb3b8145b3d7f3d54

## Итог: OVERALL = PASS. STRICTLY READ-ONLY.

## Один чистый run
p5c2-final-regression-verify.yml: changed=0, failed=0, unreachable=0.
node-01 ok=15, node-02/03 ok=6. ZERO infrastructure mutation.

## Ужесточение P4B semantic source validation (fail-closed)
Манифесты НЕ менялись, runtime НЕ менялся. Ужесточён verifier:

baseline-allow-dns-egress:
  rule exact keys == {to,ports}
  peer exact keys == {namespaceSelector,podSelector}
  namespaceSelector keys == {matchLabels} → {kubernetes.io/metadata.name:kube-system}
  podSelector keys == {matchLabels} → {k8s-app:kube-dns}
  ports len == 2, set == {(UDP,53),(TCP,53)}

validation-allow-client-egress-to-server:
  podSelector keys == {matchLabels} → {role:client}
  egress rule keys == {to,ports}
  peer keys == {podSelector}, peer podSelector keys == {matchLabels} → {role:server}
  ports len == 1, TCP/8080; ingress == []

validation-allow-server-ingress-from-client:
  podSelector keys == {matchLabels} → {role:server}
  ingress rule keys == {from,ports}
  peer keys == {podSelector}, peer podSelector keys == {matchLabels} → {role:client}
  ports len == 1, TCP/8080; egress == []

Любой дополнительный ключ (matchExpressions / ipBlock / лишний peer selector)
=> AssertionError => FAIL.

Не изменялись: P3 gate, StorageClass gate, P5B, P5C1, P5C2, манифесты, runtime,
historical evidence. Новый verifier не создавался.

Статусы присваивает только Главный Архитектор после независимого Connector audit.
