# TASK-014-R2 — result

TASK: TASK-014-R2-P4B-FINAL-REGRESSION-AUTOMATION-CLOSURE
RUN_ID: 20260827T120256Z

## Итог
Оба остаточных source-level дефекта исправлены. Добавлен regression-only mode.
Один read-only regression-only run выполнен с failed=0, unreachable=0.

## Исправления
- A (P1 exact VLAN): PHASE 15 P1 теперь fail-closed проверяет bond slaves + exact
  bond0.140/bond1.141/bond0.143/bond0.700 адреса через host-keyed map
  expected_network_by_host (no nested ternary) + default route count=1/gw/dev.
- B (P4A BGP + images): PHASE 15 P4A теперь проверяет BGP node IPs (3/3 exact),
  IP_AUTODETECTION_METHOD=bond0.140, configured image set (exact v3.32.0),
  runtime platform imageIDs, images.lock digests (manifest-list vs platform различены).

## regression-only mode
Добавлен p4b_mode: normal | regression-only (unknown => fail до mutation).
regression-only выполняет только PHASE 15 (P4A/P3/P2/P1 regression) + final-state
policy check; пропускает namespace/pods/Service/policy apply/delete/DNS/connectivity.

## Read-only regression-only run (реальный transcript)
- P1 exact VLAN: 3/3 PASS (node-01/02/03 exact адреса)
- P2: containerd 2.3.3 / kubelet 1.36.2 / swap 0 (3/3)
- P3: etcd mc=3 ml=0 h=3 el=0 ul=1 al=1 kv=3 readyz=ok; VIP owner=1 API livez=3/3
- P4A: IPPool 10.244.0.0/16 IPIP Always nat true disabled false pools=1; calico 3/3;
  autodetect bond0.140; BGP node IPs 3/3; configured images exact v3.32.0;
  runtime imageIDs exact; images.lock digests exact.
- final-state: validation namespace NotFound; TASK-014 policies cluster-wide 0;
  system namespaces 0.

## Технический нюанс
CRD `nodes.crd.projectcalico.org` отсутствует в Calico v3.32.0 (Kubernetes datastore).
BGP node IP читается из аннотации `projectcalico.org/IPv4Address` на Kubernetes Node
(JSON-aware + CIDR normalize split('/')[0]) — задокументировано в playbook и evidence.

Policy manifests 4/4 unchanged.

## Статус
Не имеет права присваивать статусы. Присваивает только Главный Архитектор после
независимого GitHub Connector audit.
