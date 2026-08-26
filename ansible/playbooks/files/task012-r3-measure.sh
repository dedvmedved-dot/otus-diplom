#!/usr/bin/env bash
# task012-r3-measure.sh — target-independent HA sampling (TASK-012-R3).
#
# Принципы (в отличие от R2):
#  - SAMPLER_HOST = SURVIVOR_A (никогда не target).
#  - etcd sampler использует LOCAL survivor etcd container (crictl/ctr exec),
#    НЕ kubectl exec к target pod. Это сохраняет измерение при API VIP failover.
#  - Все метрики measured от фактической потери сервиса (VIP_LOSS, API_FIRST_FAIL,
#    ETCD_TARGET_DOWN), НЕ от FAILURE_T0.
#
# Режимы:
#   vip    — локальная проверка VIP 172.30.140.100/32 на bond0.140 (0/1), ~200ms
#   api    — curl VIP /livez (PASS/FAIL), ~500ms
#   etcd   — endpoint status по 3 endpoints через локальный etcd контейнер, ~1s
#
# Вывод TSV в stdout (timestamp_ms в первом столбце).

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
    # Локальный etcd контейнер на sampler host (передаётся аргументом 2).
    LOCAL_ETCD_ID="${2:-}"
    EP_A="${3:-https://172.30.140.101:2379}"
    EP_B="${4:-https://172.30.140.102:2379}"
    EP_C="${5:-https://172.30.140.103:2379}"
    ETC_CA="/etc/kubernetes/pki/etcd/ca.crt"
    ETC_CERT="/etc/kubernetes/pki/etcd/healthcheck-client.crt"
    ETC_KEY="/etc/kubernetes/pki/etcd/healthcheck-client.key"
    while true; do
      ts=$(date -u +%s%3N)
      # через локальный survivor etcd контейнер (target-independent)
      out=$(ctr -n k8s.io tasks exec --exec-id "r3etcd-${ts}" \
        "${LOCAL_ETCD_ID}" \
        etcdctl --endpoints="${EP_A},${EP_B},${EP_C}" \
        --cacert=${ETC_CA} --cert=${ETC_CERT} --key=${ETC_KEY} \
        endpoint status -w json 2>/dev/null)
      echo -e "${ts}\t${out}"
      sleep 1
    done
    ;;
  *)
    echo "usage: $0 {vip|api|etcd <local_etcd_id> <ep_a> <ep_b> <ep_c>}" >&2
    exit 1
    ;;
esac
