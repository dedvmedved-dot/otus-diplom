# P8C RV-02 — LI-01..04 correction + bounded Phase-2 source package

Date: 2026-10-27 UTC. Supersedes the inaccurate conclusions in the c52c42f
reconciliation (inline Cluster backup config / EndpointSlice omission / empty-policy
baseline). Historical operator (137bb29d) and ingest (c52c42f) evidence unchanged.

## LI-01..04 closure
| ID | Fix | Artifact |
|---|---|---|
| LI-01 ObjectStore path | ObjectStore endpoint is `spec.configuration` (not `spec.data`); CNPG plugin is `spec.plugins[].parameters.barmanObjectName` (not `spec.backup.barmanObjectStore.name`). New projectors: `project_objectstore_configuration`, `project_cluster_plugins` | supplemental.py |
| LI-02 R3 proof linked | API 172.30.140.101/102/103:6443, kube-dns 10.244.254.65/.66:53, barman-cloud pluginName+9090+10.244.190.49 all in R3 | flow-matrix.md / gaps.md |
| LI-03 policy scope | K8S_NETWORKPOLICY_LIST=EMPTY (R5); EFFECTIVE_POLICY_UNION=UNKNOWN (Calico + policy.networking.k8s.io served, R14); podCIDR ≠ pod-IP allowlist | flow-matrix.md / gaps.md |
| LI-04 direction/Phase-2 | Port 9090 ≠ direction; R1 lacks initContainers. Bounded two-phase supplemental collector (discovery → conditional projection) | supplemental.py + supplemental_test.py |

## Phase-2 read-contract (OFFLINE-ONLY; PHASE2_LIVE_READS_APPROVED=NO)
| ID | Command (GVR) | Safe fields (types) | FLOW-ID |
|---|---|---|---|
| P2-D1 | `get --raw /apis/crd.projectcalico.org/v1` | served resources/versions (raw discovery, non-secret) | CNI semantics |
| P2-D2 | `get --raw /apis/policy.networking.k8s.io/v1alpha2` | served resources | BASELINE |
| P2-C1 | `get objectstores.barmancloud.cnpg.io -A -o json` | spec.configuration.endpointURL/destinationPath (origin-only), endpointCA/s3Credentials NAME+key (secret-ref) | S3-443, BAR-5432 |
| P2-C2 | `get clusters.postgresql.cnpg.io -A -o json` | spec.plugins[].name/isWALArchiver/barmanObjectName, imageName | BAR-5432 |
| P2-C3 | `get networkpolicies.crd.projectcalico.org -A -o json` | selector/order/ingress/egress/types (selector-only) | BASELINE |
| P2-C4 | `get globalnetworkpolicies.crd.projectcalico.org -o json` | selector/order/ingress/egress/types | BASELINE |

Conditional rule: P2-C* run ONLY after P2-D* identity matches the reviewed contract;
otherwise STOP/UNKNOWN. Never reads Secret/ConfigMap. No traffic/exec/iptables.

## Offline verification (9/9 PASS)
`python3 portal/networkpolicy/supplemental_test.py -v`:
- ObjectStore spec.configuration projected; secret refs name+key only (canary absent); spec.data ignored.
- CNPG plugins[] name/barmanObjectName/isWALArchiver; old backup path absent.
- Calico selector-only (no annotations/env).
- origin_only strict (scheme/type/whitespace/IPv6); classify categories; no-overwrite; no-kubectl.

## Status
```text
RECOVERY_MAIN_SHA: 0e67dbc1379eb55fa2e3e52c2969001d7fc861cb
BASE_INVENTORY_ARTIFACT_REVIEW: ACCEPTED_WITH_LIMITS
RECONCILIATION: CORRECTED (LI-01..03)
PHASE2_SOURCE_PREPARATION: PASS (supplemental.py + tests 9/9)
PHASE2_LIVE_READS_APPROVED: NO
OWNER_PHASE2_HANDOFF_ALLOWED: NO
NETPOL_LIVE_INVENTORY: EXECUTED_BASE_PARTIAL; INVENTORY_EXIT_CODE=1 (preserved)
FLOW_MATRIX_COMPLETE: NO
REMAINING_UNKNOWNS: Barman plugin direction + live S3 endpoint, Calico mode/policies,
  API DNAT enforcement, monitoring scrape identity
PHASE2_PACKAGE_REVIEW_READY: YES
NETPOL_APPROVED_FOR_APPLY: NO
P8C: NOT_FINAL_ACCEPTED; P8D–P8G/P9: NOT_AUTHORIZED
CI_RELEASE / OWNER_HELPERS / PRODUCTION_MIGRATION_DEPLOYMENT: NOT_EXECUTED
```
