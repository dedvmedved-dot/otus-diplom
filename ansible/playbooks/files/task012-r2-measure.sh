#!/usr/bin/env bash
# task012-r2-measure.sh — точный сбор HA timings (TASK-012-R2).
# Режимы (первый аргумент):
#   vip   — локальная проверка VIP 172.30.140.100/32 на bond0.140 (0/1), каждые ~200ms
#   api   — curl VIP /livez (PASS/FAIL), каждые ~500ms
#   etcd  — etcdctl endpoint status по 2 survivors (leader detection), каждые ~1s
# Вывод: TSV в stdout. timestamp в миллисекундах (date +%s%3N).
#
# Запускается на узле ДО инжекции, пишет в файл, файл забирается после теста.
# НЕ выполняет никаких destructive действий — только read-only sampling.

set -u
MODE="${1:-}"

case "$MODE" in
  vip)
    while true; do
      ts=$(date -u +%s%3N)
      has=$(ip -4 addr show dev bond0.140 2>/dev/null | grep -c '172.30.140.100/32')
      echo -e "${ts}\t${has}"
      sleep 0.2
    done
    ;;
  api)
    while true; do
      ts=$(date -u +%s%3N)
      if curl -k --connect-timeout 1 --max-time 2 -s https://172.30.140.100:6443/livez 2>/dev/null | grep -q ok; then
        r="PASS"
      else
        r="FAIL"
      fi
      echo -e "${ts}\t${r}"
      sleep 0.5
    done
    ;;
  etcd)
    ETC_CA="/etc/kubernetes/pki/etcd/ca.crt"
    ETC_CERT="/etc/kubernetes/pki/etcd/healthcheck-client.crt"
    ETC_KEY="/etc/kubernetes/pki/etcd/healthcheck-client.key"
    # survivors передаются аргументами 2 и 3
    EP_A="${2:-https://172.30.140.101:2379}"
    EP_B="${3:-https://172.30.140.103:2379}"
    while true; do
      ts=$(date -u +%s%3N)
      out=$(kubectl --kubeconfig /etc/kubernetes/admin.conf -n kube-system exec etcd-node-02 -- \
        etcdctl --endpoints="${EP_A},${EP_B}" \
        --cacert=${ETC_CA} --cert=${ETC_CERT} --key=${ETC_KEY} \
        endpoint status -w json 2>/dev/null)
      # извлечь: есть ли лидер и какой endpoint
      echo -e "${ts}\t${out}" | head -c 2000
      echo ""
      sleep 1
    done
    ;;
  *)
    echo "usage: $0 {vip|api|etcd [ep_a ep_b]}" >&2
    exit 1
    ;;
esac
