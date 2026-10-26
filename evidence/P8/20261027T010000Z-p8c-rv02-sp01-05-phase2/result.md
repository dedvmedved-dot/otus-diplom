# P8C RV-02 — SP-01..05 closure (supplemental collector)

Date: 2026-10-27 UTC. Correction of review e80ff8d.

## SP-01..05 closure
| ID | Fix | Test (21/21 PASS) |
|---|---|---|
| SP-01 discovery gate | main() enforces per-read dependencies: Calico policy/mode reads (C3/C4/C5) require D1 discovery match; unmet → BLOCKED_NOT_EXECUTED (no subprocess). Discovery validated + projected (kind=APIResourceList, groupVersion, resources name/namespaced/verbs); wrong identity/version/missing resource/malformed JSON → error, dependents blocked | test_wrong_discovery_blocks_dependents, _forbidden, _timeout, _non_json, _extra_member, _valid_discovery |
| SP-02 typed policy | recursive typed projection: selector(str)/order(num)/types(str list)/ingress+egress action+entity(selector,namespaceSelector,nets,ports,notPorts,serviceAccounts); arbitrary metadata/env/unexpected dropped; scalar canary → ValueError | test_policy_scalar_canary_rejected, test_policy_nested_metadata_dropped |
| SP-03 scope/identity | per-kind apiVersion+kind+scope; GlobalNetworkPolicy cluster-scoped (no namespace); invalid list elements reject (not dropped); wrong apiVersion/false-secret-ref/missing-spec/empty-namespace reject | test_gnp_cluster_scoped_valid, test_malformed_items_rejected, test_wrong_api_version_rejected, test_false_secret_ref_rejected, test_missing_spec_rejected, test_empty_namespace_rejected |
| SP-04 coverage | FelixConfiguration mode (bpfEnabled/dataplane), pod initContainers+containers identity (name/image/imageID/ports/restartPolicy, no env/args), policy.networking.k8s.io discovery, namespace/name-scoped ObjectStore+Cluster reads | test_felix, test_pod_identity, projectors |
| SP-05 docs | flow-matrix cnpg.io/podRole; collection-map ObjectStore spec.configuration + Phase-2 implemented (not NOT_DEFINED); PLAN DNS/API already collected | flow-matrix.md, collection-map.md |

## Read contract (dependencies)
D1 (Calico discovery) → C3/C4/C5; D2 (policy.networking.k8s.io discovery); C1 (ObjectStore spec.configuration), C2 (Cluster spec.plugins), S1/S2 (pod sidecar identity) — bound to reviewed apiVersion, no discovery dep.

## Status
```text
RECOVERY_MAIN_SHA: 654f9292d4b9eafb307679a04bddcf553ec3003b
SP-01..05: CLOSED (source + tests)
SUPPLEMENTAL_TESTS: 21/21 PASS (exit 0)
PHASE2_LIVE_READS_APPROVED: NO
OWNER_PHASE2_HANDOFF_ALLOWED: NO
NETPOL_APPROVED_FOR_APPLY: NO
BASE_INVENTORY_ARTIFACT_REVIEW: ACCEPTED_WITH_LIMITS; INVENTORY_EXIT_CODE=1 (preserved)
FLOW_MATRIX_COMPLETE: NO
PHASE2_PACKAGE_REVIEW_READY: YES
P8C: NOT_FINAL_ACCEPTED; P8D–P8G/P9: NOT_AUTHORIZED
CI_RELEASE / OWNER_HELPERS / PRODUCTION_MIGRATION_DEPLOYMENT: NOT_EXECUTED
```
