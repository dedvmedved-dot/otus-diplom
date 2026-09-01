# P5C1 — Piraeus / DRBD Runtime Bootstrap

STATUS: AUTHORIZED (TASK-017). Deploys control/runtime stack ONLY.

## Scope
- Piraeus Operator v2.10.6 (CRDs + operator)
- LinstorCluster (minimal, no nodeSelector → all 3 nodes)
- operator-managed controller + satellites + CSI + DRBD module loader
- Actual runtime DRBD 9.3.2 load on 3/3 nodes

## NOT in P5C1 (forbidden)
- storagePools / source.hostDevices / raw-device init
- vg_piraeus/thin_piraeus binding (read-only)
- diskful project pool, DRBD data resource
- StorageClass / PV / PVC
- LinstorNodeConnection / VLAN141 replication path (P5C2)

## Pinned components (versions.lock, READ-ONLY)
Operator 2.10.6 · LINSTOR 1.33.2 · LINSTOR CSI 1.11.0 · DRBD 9.3.2 · drbd-utils 9.34.3

## Source
manifests/piraeus/v2.10.6/ (vendored upstream release v2.10.6)
  manifest.yaml      SHA256 bffdd616054cb7c02ea9baaed5d6394b53ab9a93b58b8665cfa0d55452c55f13
  piraeus-2.10.6.tgz SHA256 f8150f7ad8085131d555ab28f280ed76b754f7693b5f601d0bfb8f15b1ac49b5

## DRBD module loader
osImage "Astra Linux" → fallback image drbd9-resolute:v9.3.2 (compile/load on node).

## Mode gate
p5c1_mode=authorized-runtime-bootstrap (default disabled).
