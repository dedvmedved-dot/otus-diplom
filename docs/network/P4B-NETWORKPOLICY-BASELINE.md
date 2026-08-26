# P4B — Baseline NetworkPolicy

## Контракт

1. Каждый non-system workload namespace начинает с default-deny ingress+egress.
2. DNS UDP/TCP 53 к CoreDNS — единственное baseline исключение.
3. Application трафик требует explicit allow policy.
4. kube-system / default / kube-public / kube-node-lease НЕ покрываются автоматически.
5. P4B использует стандартный Kubernetes NetworkPolicy API (networking.k8s.io/v1).
6. GlobalNetworkPolicy (Calico) в P4B НЕ вводится.
7. Baseline применяется ДО допуска workload pods в будущих стадиях.
8. Любой egress к Internet/API/databases/storage требует explicit policy.

## Будущие стадии (P7/P8/...)

Любой application namespace обязан применить:
1. `baseline-default-deny-all`
2. `baseline-allow-dns-egress`

до или атомарно с первым application workload, затем добавить explicit
application-specific allows.

## Файлы

- `ansible/playbooks/files/networkpolicy/baseline-default-deny-all.yaml`
- `ansible/playbooks/files/networkpolicy/baseline-allow-dns-egress.yaml`
- `ansible/playbooks/files/networkpolicy/validation-allow-client-egress-to-server.yaml`
- `ansible/playbooks/files/networkpolicy/validation-allow-server-ingress-from-client.yaml`

## CoreDNS selector (проверено)

- namespace: `kubernetes.io/metadata.name=kube-system`
- pod: `k8s-app=kube-dns`
