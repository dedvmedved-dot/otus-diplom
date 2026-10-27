# P8C RV-02 — Phase-2 live run (one read-only execution) — result + reconciliation

Date: 2026-10-27. One permitted run of the pinned supplemental collector on node-01.

## Gate / source identity
```text
GATE_SHA: a7c14cd9942f8a353d6ea846b2e22ea93ab9ca2e
RECOVERY_MAIN_SHA: a7c14cd9942f8a353d6ea846b2e22ea93ab9ca2e
SCRIPT_SOURCE_SHA: b623afb2fa9fd624e3e1ff418adeb9c71b1074df
SCRIPT_GIT_BLOB: ad2edaa92de59f657599190842fa7fe68373b582
SCRIPT_SHA256: 69dac4747856e5f88ac4666e884fe1263777ca5cb64b197741a4b370c093aa4c
ACCESS_PATH: Hermes-VPS -> tun0 (192.168.194.0/24) -> ssh root@node-01 (mgmt 192.168.194.38)
CONTEXT: kubernetes-admin@pak-portal · HOST: node-01 · Python 3.11.2
START_UTC: 2026-10-27T13:57:05Z · END_UTC: 2026-10-27T13:57:06Z
INVENTORY_EXIT_CODE: 1
```
Script SHA-256 verified before transfer (blob + sha256) and on node-01; `sha256sum --check`
passed. Host key pinned via ssh-keyscan; StrictHostKeyChecking=yes; password read from
root-only credential file (not echoed).

## Result records (10) and categories
```text
RECORDS_TOTAL: 10
OK (None): 5   = D1, C1, C2, S1, S2
UNSUPPORTED: 2 = D2 (ClusterNetworkPolicy), I1 (calico-node runtime digest)
BLOCKED_NOT_EXECUTED: 3 = C3, C4, C5 (identity gate)
API_NOT_SERVED/FORBIDDEN/TIMEOUT/CONNECTION/PARSE_ERROR/GET_FAILED: 0
OUTPUT_SHA256: 02e872e7b82918380c89e8f3a2bf74dc039bd48ea6ee167c0f64d477debe642c
PHASE2_RESULT: PARTIAL (5 data reads; 2 unsupported; 3 blocked by identity gate)
```

## Key observed facts
- **D1 (Calico)** `crd.projectcalico.org/v1` served: networkpolicies, globalnetworkpolicies,
  felixconfigurations, **hostendpoints**, **tiers**, ippools, bgp*, ipam*, caliconodestatuses, etc.
- **D2 (policy.networking.k8s.io)** `v1alpha2` serves **ClusterNetworkPolicy** (unsupported kind
  → UNSUPPORTED; not AdminNetworkPolicy as the offline fixture assumed).
- **I1 (Calico identity)** calico-node `quay.io/calico/node:v3.32.0` (tag matches pin), but runtime
  `imageID sha256:6bc9fa4d…` ≠ pinned manifest digest `sha256:f4fafd8…` → platform-child digest,
  gate conservatively UNSUPPORTED → C3/C4/C5 BLOCKED.
- **C1 (ObjectStore)** live endpoint `https://s3-backup.demo-pak.test`, destinationPath
  `s3://portal-postgres-backup`, CA ref `portal-barman-s3-ca`, s3 credentials ref
  `portal-barman-s3-credentials` (ACCESS_KEY_ID / ACCESS_SECRET_KEY / AWS_REGION keys only).
- **C2 (Cluster)** plugin `barman-cloud.cloudnative-pg.io` isWALArchiver=true,
  barmanObjectName=`portal-db-backup`; imageName CNPG postgresql 17.10-system-trixie.
- **S1 (portal pods)** portal-db-1/2/3 each: init `bootstrap-controller` (cloudnative-pg) +
  init `plugin-barman-cloud` (per-instance Barman sidecar) + `postgres` container.
- **S2 (cnpg-system)** `barman-cloud` pod: container `barman-cloud` (plugin-barman-cloud) — plugin controller.

## Reconciliation (FLOW-IDs / gaps)
- **S3-443** → endpoint RESOLVED: `https://s3-backup.demo-pak.test` (origin-only). Port 443 implied
  by https scheme; the bucket path is `portal-postgres-backup`. Secret values NOT collected (refs only).
- **BAR-5432** → plugin controller (S2) + per-instance sidecar (S1 init `plugin-barman-cloud`) +
  barmanObjectName confirmed; direction (sidecar→DB vs sidecar→S3) still UNKNOWN (declared, not traffic).
- **Baseline / CNI policy** → Calico policy CRDs served but NOT read (C3/C4/C5 blocked by identity
  gate) → EFFECTIVE_POLICY_UNION remains UNKNOWN. policy.networking.k8s.io serves ClusterNetworkPolicy.
- **Calico identity/mode** → image tag v3.32.0 matches pin; runtime platform-child digest ≠ pinned
  manifest digest (expected, documented limit) → identity gate blocked version-specific reads.
  Effective mode (iptables/eBPF) + hostendpoints/tiers UNREAD → UNKNOWN.

## Status
```text
GATE_SHA: a7c14cd9942f8a353d6ea846b2e22ea93ab9ca2e
RECOVERY_MAIN_SHA: a7c14cd9942f8a353d6ea846b2e22ea93ab9ca2e
INVENTORY_EXIT_CODE: 1 (preserved; not relabelled)
RECORDS_TOTAL: 10 · OK 5 · UNSUPPORTED 2 · BLOCKED_NOT_EXECUTED 3
PHASE2_RESULT: PARTIAL
FLOW_MATRIX_COMPLETE: NO
REMAINING_UNKNOWNS: effective Calico mode; policy union (C3/C4/C5 unread); plugin direction; platform-child digest binding
FINAL_REMOTE_MAIN_SHA: (set at publish)
NETPOL_APPROVED_FOR_APPLY: NO
P8C: NOT_FINAL_ACCEPTED · P8D–P8G/P9: NOT_AUTHORIZED
```
The one-run authorization is consumed. Further reads / rerun / apply / CI / production require a
new decision. STOP.
