# Current VM fit (4 vCPU / 7.7 GiB / 50 GB OS + 500 GB vdb)

AIStor Free: PASS (single-node single-drive; parity 0).
AIStor Ent: PASS (technically) — cost/license blocker.
SeaweedFS: PASS (trivial single-node).
Ceph RGW: FAIL (needs >=2 OSD disks, >=16-32 GiB RAM, 3 MONs; single 500 GB disk insufficient).
