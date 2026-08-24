# TASK-009-P3A — result

TASK: TASK-009-P3A-FIRST-CONTROL-PLANE-BOOTSTRAP
RUN_ID: 20260824T135040Z

## Итог
Первый control-plane Kubernetes-кластера развёрнут на node-01 с kube-vip (ARP, leader election) и локальным stacked etcd.

## Ключевые результаты
- kubeadm init node-01: EXIT=0 (control-plane initialized)
- API VIP: 172.30.140.100/32 на bond0.140 (kube-vip, ARP mode)
- API server: https://172.30.140.100:6443 (readyz ok, etcd ok)
- Control-plane pods: apiserver/controller-manager/scheduler/etcd/kube-vip — Running
- node-01: NotReady (CNI не установлен — ожидаемо), InternalIP=172.30.140.101
- CoreDNS: Pending (до CNI — ожидаемо)
- cert SAN: 172.30.140.100 + 172.30.140.101 + node-01
- node-02 / node-03: NOT JOINED (admin.conf/kubelet.conf/etcd отсутствуют)
- Calico / CNI: НЕ установлен

## Версии
- Kubernetes v1.36.2, containerd 2.3.3, kube-vip v1.2.0 (digest fe8c7b66...)

## Известная проблема (исправлена в ходе)
kube-vip v1.2.0 в static pod требует hostAliases "kubernetes → 127.0.0.1"
(иначе leader election падает с "lookup kubernetes: no such host").
Manifest дополнен hostAliases + port/vip_subnet/svc_enable env.

## Secret hygiene
- certificateKey: локально /root/task009-p3a-*/certkey.txt (0600), не в Git
- kubeadm-init-raw.log (join token): локально (0600), не в Git
- evidence: только sanitized config (certificateKey: REDACTED_LOCAL_SECRET)

## Repro automation
- ansible/playbooks/p3a-bootstrap-first-control-plane.yml (syntax PASS)
- ansible/playbooks/templates/p3a-kubeadm-init-node01.yaml.j2
- images.lock: kube-vip digest зафиксирован
