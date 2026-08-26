# TASK-013 / P4A — result

TASK: TASK-013-P4A-CALICO-CNI-FOUNDATION-AND-DNS-RESTORATION
RUN_ID: 20260826T191434Z

## Итог
Calico CNI v3.32.0 установлен в 3-node control-plane кластер. Кластер полностью
Ready, CoreDNS работает, pod-to-pod и service connectivity подтверждены.

## Что сделано
1. Vendored exact upstream manifest v3.32.0 (calico.yaml), Pod CIDR явно 10.244.0.0/16.
2. Все 3 Calico images (node/cni/kube-controllers) pull + digest verified на 3 узлах,
   images.lock обновлён реальными sha256.
3. Применён manifest (Kubernetes API datastore, не Tigera operator).
4. Валидация: cross-node 6/6, ClusterIP 3/3, DNS 3/3+3/3.

## Ключевой дефект, обнаруженный и исправленный
При первом apply calico-node на node-01 не сходился BGP mesh: BIRD auto-detection
на multi-homed узлах выбирал РАЗНЫЕ интерфейсы (node-01 → bond1.141/172.30.141.101,
node-02/03 → bond0.143/172.30.143.x), поэтому BGP peering не устанавливался.

Исправление (не dataplane change, IPIP остаётся Always): добавлен явный
`IP_AUTODETECTION_METHOD=interface=bond0.140` в calico-node DaemonSet — BGP node IP
закреплён за управляющей сетью 172.30.140.0/24 (той же, где kube-vip/API). После
restart pods BGP mesh сошёлся (router id 172.30.140.x на всех 3 узлах), calico-node
3/3 Ready.

## Валидация
- nodes Ready 3/3, стабильно 60s
- CoreDNS 2/2 Ready, стабильно 60s
- IPPool 10.244.0.0/16, ipipMode=Always, natOutgoing=true, 0 unexpected pools
- test pods: по одному на node, IP 10.244.190.1/184.1/254.68 (в 10.244.0.0/16)
- cross-node ICMP 6/6 (0.3-0.5ms)
- ClusterIP service 3/3 (pong через nc)
- DNS kubernetes.default 3/3, test service DNS 3/3

## Регрессии
- API readyz ok, etcd 3/3, VIP single-owner node-02 (P3 intact)
- P1 preserved 3/3 (bond/VLAN/default route unchanged; только Calico tunl0/cali*/BIRD routes)
- P2 preserved 3/3 (containerd 2.3.3, kubelet 1.36.2, swap 0)

## Cleanup
namespace p4a-net-validation удалён (NotFound verified), post-cleanup 60s stable.

## Статус
Не имеет права присваивать статусы. Присваивает только Главный Архитектор после
независимого GitHub Connector audit.
