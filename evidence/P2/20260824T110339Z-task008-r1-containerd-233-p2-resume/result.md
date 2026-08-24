# TASK-008-R1 — result

TASK: TASK-008-R1-CONTAINERD-2.3.3-BASELINE-AND-P2-RESUME
RUN_ID: 20260824T110339Z

## Архитектурное решение
- ADR-002 записан: containerd 2.3.1 → 2.3.3 (ACCEPTED, Chief Architect)
- versions.lock: containerd = 2.3.3 (единственное изменение)

## Источники пакетов
- containerd: Docker Debian Bookworm stable (2.3.3-1~debian.12~bookworm)
- Kubernetes: pkgs.k8s.io core:/stable:/v1.36 (1.36.2-2.1)

## Выполнено на node-01/02/03 (serial, через Ansible playbook)
1. Docker repo + Kubernetes repo (keyrings в /etc/apt/keyrings/)
2. swap: swapoff + fstab закомментирован (USED=0 был)
3. kernel modules: overlay + br_netfilter (persistent)
4. sysctl: bridge-nf-call-iptables/ip6tables + ip_forward = 1
5. containerd.io 2.3.3 установлен, CRI включён, SystemdCgroup=true
6. kubelet/kubeadm/kubectl 1.36.2 установлены
7. apt-mark hold: containerd.io kubelet kubeadm kubectl
8. containerd enabled+active, kubelet enabled
9. NO cluster initialized (no kubeadm init)

## Версии (3/3 узла)
- containerd v2.3.3, runc 1.4.3
- kubelet/kubeadm/kubectl v1.36.2

## Гейты
- P1 regression: PASS (bond0/bond1, VLAN 700/140/141/143, gateway, cross-node 6/6)
- No-cluster: PASS
- crictl: NOT AVAILABLE (не устанавливался отдельно)
- CRI plugin: ok

## Итог
P2 host runtime + Kubernetes packages: PASS 3/3.
P3 (kubeadm init и далее) НЕ выполнялся.
