# TASK-015-R5 — result

TASK: TASK-015-R5-P5A-FINAL-BUSY-DEVICE-AND-REGRESSION-PROOF
RUN_ID: 20260829T121019Z

## Итог: финальная busy-device proof закрыта. OVERALL = PASS.

## Исправленные дефекты (D1-D8)
- D1: holders через os.listdir(/sys/class/block/<kname>/holders) == 0 (не cat директории).
- D2: DM dependency через major:minor (dmsetup deps), не literal /dev/sdX поиск.
- D3: root/boot/home ancestry fail-closed (findmnt source + lsblk PKNAME walk + norm /dev).
- D4: pvs rc=0 + JSON parse до оценки ceph тегов.
- D5: Ceph OSD block/block.db/block.wal ссылки резолвятся через readlink -f.
- D6: ceph-volume fail-closed если есть; UNAVAILABLE если нет.
- D7: CoreDNS desired/available/ready=2 в P4A PRE/POST.
- D8: etcd member list --write-out=json (member learners JSON-aware).

## Чистый R5 run (18-r5-playbook-run.txt)
PLAY RECAP: node-01 ok=21, node-02 ok=11, node-03 ok=11; failed=0 unreachable=0.
21 задача PASS: p5a_mode gate, P1-P4 PRE (P1 VLAN, P2 containerd/kubelet, P3 JSON
etcd+leader+livez, P4A CoreDNS+IPPool+BGP, P4B), composite resolver 6/6, holders 6/6=0,
DM deps 6/6 clear, root ancestry 6/6 clear, LVM/RAID clear, Ceph excluded 6/6,
K8s storage clean, P1-P4 POST, VIP owner=1.

## Технические решения
- mdadm/multipath/ceph-volume отсутствуют → структурная проверка (os.listdir holders,
  dmsetup deps major:minor, /proc/mdstat, readlink -f OSD links) с явным
  UNAVAILABLE-маркером, не fail-open.
- DRBD compile/health/fingerprint НЕ выполнялись (R4 ACCEPTED, не повторялись).

## Статус
versions.lock и ADR-003 не изменялись. Никакой destructive операции.
Статусы присваивает только Главный Архитектор после независимого Connector audit.
