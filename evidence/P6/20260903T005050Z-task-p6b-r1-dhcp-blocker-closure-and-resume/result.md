# TASK-P6B-R1 — result

TASK: TASK-P6B-R1
RUN_ID: 20260903T005050Z
BASELINE: dea3121eba11a69a6638407e99b56bc32847667b
MODE: BLOCKER CLOSURE + CONTROLLED RESUME

## Итог: MetalLB 0.16.1 L2 foundation развёрнут и доказательно принят.

## Blocker closure
DHCP/IPAM blocker закрыт Owner-подтверждением: сеть 172.30.140.0/24 без DHCP.
Ingress pool 172.30.140.110-119 разрешён. (Историческое BLOCKED evidence не тронуто.)

## MetalLB 0.16.1 L2 (digest-pinned)
- controller: quay.io/metallb/controller@sha256:5a3e101335f5ea2cfb0ddf51acdfa9538251e0623ffcd6cbfc1b274b7898790c
- speaker:    quay.io/metallb/speaker@sha256:37a98a9d1cd970051c5dededb6f922c1e6c3b90fdd0fc1350d1686e67675af0e
- controller Ready 1/1, speaker 3/3 Ready, runtime imageIDs == pinned digests.

## IPAddressPool + L2Advertisement (exact)
- p6-ingress-pool: addresses=[172.30.140.110-172.30.140.119] (availableIPv4=10)
- p6-ingress-l2: ipAddressPools=[p6-ingress-pool]
- BGPPeer=0, BGPAdvertisement=0, BFDProfile=0.

## Validation proof
- LB IP = 172.30.140.110 (из approved pool).
- L2/ARP: route к .110 идёт через bond0.140 (src 172.30.140.102), соединение устанавливается.
- HTTP functional: curl http://172.30.140.110/ → HTTP 200, body "P6B_METALLB_HTTP_OK"
  (с node-01 и node-02; node-02 не на том узле, где backend — реальный L2-путь).

## Preservation
- kube-vip: cp_enable=true, svc_enable=false, VIP 172.30.140.100 owner aggregate=1 (сохранён).
- P1-P5 post-regression: changed=0 failed=0 unreachable=0 (после cleanup).
- P4B fingerprint вернулся к f3624ec7... после удаления validation netpol.

## Cleanup
- p6b-validation namespace удалён (NotFound), LB services = NONE, residue = 0.

## Production state (P6B)
- MetalLB 0.16.1 installed, controller Ready, speaker 3/3.
- p6-ingress-pool (exact), p6-ingress-l2, BGP=0.
- images.lock дополнен factual metallb-controller + metallb-speaker entries.

## Deviation note
Post-regression первый прогон дал P4B fingerprint mismatch из-за временных
validation NetworkPolicies (ожидаемо); после cleanup fingerprint вернулся.
Валидационный backend имел 2 итерации исправления (mkdir /www → /tmp/www, и
добавление control-plane toleration к controller Deployment) — все в authorized scope.

Hermes НЕ присваивает статусы и НЕ приступает к P6C / Envoy Gateway.
