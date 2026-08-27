# TASK-014-R3 — result

TASK: TASK-014-R3-P4B-CALICO-IMAGE-AUTOMATION-FINAL-CLOSURE
RUN_ID: 20260827T203518Z

## Итог
Все три остаточных source-level дефекта Calico image validation исправлены.
Один read-only regression-only run выполнен с failed=0, unreachable=0.

## Исправления
1. `.items[0]` acceptance устранён → PHASE 15 P4A теперь парсит ВСЕ 3 calico-node
   pods (pod count fail-closed, все containers/initContainers image+imageID).
2. DaemonSet template image multiset: node=2, cni=2, total=4, unexpected=0.
3. images.lock теперь реально читается структурно (lookup + from_yaml,
   delegate_to localhost) и проверяет 3 Calico записи (image/tag/digest/verified)
   с duplicates=0, missing=0.

## Read-only regression-only run (реальный transcript)
- DS template multiset: node=2 cni=2 total=4 unexpected=0
- calico-node pods=3, node_img=6 cni_img=6 other_img=0 node_iid=6 cni_iid=6
- controllers: 1 replica, exact image + exact imageID
- images.lock structural parse: 3/3 Calico entries exact (assert ok)
- BGP node IPs 3/3, autodetection bond0.140, IPPool full
- P1 exact VLAN 3/3, P2 3/3, P3 full
- final-state: namespace NotFound, TASK-014 policies 0, system namespaces 0

## Технический нюанс (из R2, сохранён)
BGP node IP читается из аннотации projectcalico.org/IPv4Address (CRD
nodes.crd.projectcalico.org отсутствует в Calico v3.32.0). DS initContainers:
upgrade-ipam (cni), install-cni (cni), ebpf-bootstrap (node); main calico-node (node).

Policy manifests 4/4 unchanged. images.lock unchanged.

## Статус
Не имеет права присваивать статусы. Присваивает только Главный Архитектор после
независимого GitHub Connector audit.
