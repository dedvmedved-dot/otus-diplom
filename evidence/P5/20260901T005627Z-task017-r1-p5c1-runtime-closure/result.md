# TASK-017-R1 — result

TASK: TASK-017-R1-P5C1-RUNTIME-REPRODUCIBILITY-AND-EVIDENCE-CLOSURE
RUN_ID: 20260901T005627Z

## Итог: P5C1 runtime reproducibility + evidence закрыты. OVERALL = PASS.

## Закрытые дефекты (D1-D6)
- D1 execution chronology задокументирована (03-task017-execution-chronology.txt):
  mutation run упал unreachable после Operator apply, работа продолжилась отдельно.
  Historical evidence НЕ изменён.
- D2 bootstrap source исправлен: committed control-plane patches (6A) + LB_MAKEOPTS
  apply (8A) + корректный порядок фаз §19.
- D3 fail-open waits убраны: `|| true` = 0, `kubectl wait || true` = 0.
- D4 DRBD gate полный: /sys/module/drbd + version 9.3.2 + srcversion (old 8.4.11 not
  loaded) + lsmod + tcp + uname + modinfo rc + vermagic.
- D5 новый read-only verify playbook (p5c1-runtime-verify.yml) — единственный
  выполненный, full P1-P4 PRE/POST.
- D6 images.lock digest verification: все 15 verified:true фактически доказаны
  runtime imageID (match 15/15), downgrade не потребовался.

## Чистый run (39-runtime-verify-playbook-run.txt)
PLAY RECAP: node-01 ok=29, node-02/03 ok=10; changed=0 failed=0 unreachable=0.

## Ключевые факты (read-only верификация)
- Piraeus Operator 2.10.6 Ready, controller 1.33.2, satellites 3/3 Online, CSI 1.11.0
- DRBD 9.3.2 runtime 3/3 (RAM-load: загруженный srcversion per-node != in-tree 8.4.11)
- drbd-utils 9.34.3
- Toleration source == live, LB_MAKEOPTS source == live
- Project diskful pool/resources/SC/PV/PVC = 0/0/0/0/0
- P5B LVM UNCHANGED (canonical UUID diff empty)
- VLAN141 six-path PASS, P1-P4 full PRE/POST PASS, P4B fingerprint unchanged

## Инфраструктура
R1 INFRASTRUCTURE MUTATION: 0 (read-only). P5C2 NOT STARTED.

Статусы присваивает только Главный Архитектор после независимого Connector audit.
