# TASK-017-R5 — result

TASK: TASK-017-R5-P5C1-FINAL-BASELINE-SUPPLY-AND-ASSERTION-CLOSURE
RUN_ID: 20260901T201345Z

## Итог: P5C1 final baseline + supply + assertion closure. OVERALL = PASS.

## Закрытые дефекты (D1-D11)
- D1 bootstrap kube-vip Ready: PRE+POST требуют 3 Running AND 3 Ready (Ready condition
  status=True, fallback containerStatuses all ready=true), VIP owner=1.
- D2 OS PV existence: require exactly one /dev/sda3 per node (OS_PV_FOUND=1), exact map
  node-01->astra38644 / node-02->astra39539 / node-03->astra03718.
- D3 runtime P5B baseline assert: PRE и POST выполняют строгую baseline assertion
  (2/2 composite resolve, exact PV path+UUID set, OS PV exists+map, thin-pool type/active,
  Data%/Meta% parseable, VG free>0) перед canonical compare. Wrong-baseline не пройдёт.
- D4 pinned/vendored full verify: versions.lock + полный парсинг vendored image-config
  (17 image/tag), drbd-utils hard-coded fallback УДАЛЁН.
- D5 derived mandatory set: из vendored image-config + images.lock P5C1, set equality 17==17.
- D6 all registries supply: quay.io + registry.k8s.io, generic token flow, no assumed-via-runtime.
- D7 single-manifest digest: Docker-Content-Digest required, unresolved => FAIL.
- D8 complete mandatory key set: derived из images.lock, verified+image+tag+sha256 обязательны.
- D9 running component-bound + non-running registry-bound (не name-only exception).
- D10 CSI controller в effective toleration set.
- D11 CSI cardinality exact (deploy desired/avail/ready=1 + total pod count=1 Running).

## Чистый run (39-runtime-verify-playbook-run.txt)
PLAY RECAP: node-01 ok=33, node-02/03 ok=10; changed=0 failed=0 unreachable=0.

## Инфраструктура
R5 INFRASTRUCTURE MUTATION: 0. Bootstrap НЕ выполнялся. P5C2 NOT STARTED.

Статусы присваивает только Главный Архитектор после независимого Connector audit.
