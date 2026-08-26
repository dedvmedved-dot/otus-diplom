# TASK-012-R3 — result

TASK: TASK-012-R3-FINAL-HA-METROLOGY-AND-FAILURE-CONTROL-CLOSURE
RUN_ID: 20260826T073946Z

## Итог
Финальный approval-controlled HA run закрыл метрологию и failure-control. Все 3 HA-SLO
зафиксированы численно и recalculable из raw TSV.

## Динамический target (третья миграция ролей)
VIP owner == etcd leader == node-03 (после R2 роли были на node-03).
Target = node-03, survivors = node-01/node-02, sampler host = node-01 (≠ target).

## Метрология (ключевое исправление R3)
FAILURE_T0 больше НЕ является начальной точкой HA-SLO. Метрики измерены от фактической
потери защищаемой функции:

| Метрика | Значение | Порог | Результат |
| --- | --- | --- | --- |
| T_VIP_FAILOVER | 485 ms | ≤15000 | PASS |
| T_API_RECOVERY | 1527 ms | ≤15000 | PASS |
| T_ETCD_LEADER | ≤1230 ms (верхняя граница 1s sampling) | ≤15000 | PASS |

- T_INJECTION_TOTAL = 51504 ms — DIAGNOSTIC (время последовательной инжекции), НЕ SLO.

## Target-independent sampler architecture
- SAMPLER_HOST = node-01 (survivor), assert ≠ target.
- etcd sampler использует ЛОКАЛЬНЫЙ survivor etcd контейнер (36ad39f2..., via ctr exec),
  НЕ kubectl exec к target pod. Это сохранило измерение при API VIP failover.
- 3 samplers запущены ДО инжекции, baseline 5s подтверждён.

## Измерения
- VIP: 703/701/699 samples (по 3 узлам), max owner_count=1, split=0.
  LOSS node-03 → NEW OWNER node-02 за 485ms.
- API: 270 samples, ровно 1 FAIL, recovery за 1527ms.
- etcd: 58 samples, leader node-03 → node-01 (target down + new leader в одном 1s interval).
- API stability R3: 30/30 PASS (новый замер, не R1).

## Failure-control closure
- 10 живых flags, каждый с block/rescue, все в final fail.
- Post-injection 0/5 assertion.
- Recovery: 5 отдельных блоков (kubelet, exact 5/5, etcd 3/3, kube-vip 3/3, API).
- Cleanup: samplers (pgrep verified 0), probe (NotFound verified), dead-man (is-active verified).

## Post-recovery invariants
P1/P2 preserved 3/3, CNI absent, etcd membership 3 (не изменился), 0 learners,
нет постоянных изменений, temp objects/processes = NONE.

## ЧЕСТНАЯ ОГОВОРКА
T_ETCD_LEADER_MS записан как 0, потому что target etcd down и новый leader появились
в одном 1-second sampling sample. Это верхняя граница: реальное время election ≤ ~1230ms
(интервал между сэмплами). Connector может пересчитать из raw TSV 24-etcd-leader-samples.tsv.
