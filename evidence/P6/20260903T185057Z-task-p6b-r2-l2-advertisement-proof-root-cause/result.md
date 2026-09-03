# TASK-P6B-R2 — result

TASK: TASK-P6B-R2
RUN_ID: 20260903T185057Z
BASELINE: 948b46e19e61acbbb53f6c4b6026b4f778b0141e
MODE: CORRECTIVE VALIDATION / ROOT-CAUSE ANALYSIS

## Итог: BLOCKED — ARCHITECT DECISION REQUIRED

## Root cause (PROVEN, factual)

MetalLB speaker НЕ объявляет LB IP 172.30.140.110, потому что ВСЕ три узла
несут label:

  node.kubernetes.io/exclude-from-external-load-balancers = ""

(значение пустое, но LABEL ПРИСУТСТВУЕТ). MetalLB layer2 controller пропускает
announce для узлов с этим label — debug-лог:

  layer2_controller.go:269 event="skipping should announce l2"
    reason="speaker's node has labeled
            'node.kubernetes.io/exclude-from-external-load-balancers'"
  layer2_controller.go:104 reason="no available nodes"

## Доказательства (packet capture + логи)

1. ARP capture (python AF_PACKET, bond0.140): ARP who-has .110 (3 запроса) ->
   НЕТ reply. При этом kube-vip .100 ОТВЕЧАЕТ (REPLY is-at 6c:b3:11:61:d3:22).
2. Speaker debug-лог: "skipping should announce l2" + "no available nodes".
3. node label присутствует на node-01/02/03 (значение "").

HTTP 200 из R1 (node-01/02) был hairpin/kube-proxy локальной обработкой
Service LoadBalancer, НЕ внешней L2 ARP advertisement — теперь это доказано.

## Почему BLOCKED

Удаление node label `node.kubernetes.io/exclude-from-external-load-balancers`
относится к классу "NOT automatically authorized" (§13/§17/§5). Hermes НЕ
удалил label и сообщает BLOCKED.

## Требуемое решение Архитектора

Авторизовать удаление label
`node.kubernetes.io/exclude-from-external-load-balancers`
с node-01, node-02, node-03 (label был поставлен ранее, вероятно в P3/P4,
и не должен присутствовать для bare-metal MetalLB L2).

После авторизации: удалить label с 3 узлов -> MetalLB speaker начнёт объявлять
.110 -> повторный ARP capture + external HTTP proof.

## Временные изменения — все откачены

- speaker --log-level=debug -> reverted to info.
- L2Advertisement interfaces=[bond0.140] -> reverted to exact.
- validation namespace p6b-r2-validation -> deleted.
- Production state == pre-R2 baseline (controller 1/1, speaker 3/3, pool exact,
  l2adv exact, BGP=0, validation NotFound).

Hermes НЕ присваивает статусы. Ждёт решения Архитектора.
