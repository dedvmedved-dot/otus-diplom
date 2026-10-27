# P8C RV-02 — requirement → code → test → evidence matrix (33/33)

Governing reviews: c52c42f (G2), e80ff8d (SP-01..05), 3262a9b, 8598f73, 5d0e965,
f080cc3, 010ff33. Source `portal/networkpolicy/supplemental.py`; tests
`supplemental_test.py` (33/33, exit 0). Evidence root:
`evidence/P8/20261027T070000Z-p8c-rv02-r4-r5-remainder/`.

| Requirement | Code | Test (supplemental_test.py) | Evidence |
|---|---|---|---|
| Runtime identity — exact registry/version pin, digest bound to pinned manifest, per-pod verdict, empty/unbound/unknown/mixed block | `CALICO_IMAGE_REFS`, `PINNED_DIGEST`, `IMAGE_ID_RE`, `verify_calico_identity` | `test_identity_exact_contract`, `test_identity_gate_negatives`, `test_calico_identity_present` | 010ff33-review/observations.json identity cases |
| Unsupported identity diagnostic (valid-but-unbound → UNSUPPORTED + retained identity; malformed → PARSE_ERROR) | `UnsupportedIdentity`, `verify_calico_identity` | `test_unsupported_identity_diagnostic` | observations.json `valid_unsupported_identity` |
| Fixed outbound API paths (C1-C5 `get --raw`), literal argv | `READ_CONTRACT` | `test_literal_api_paths` | 010ff33-review/execution.json argv |
| Discovery gate — exact kind/scope/verbs, C5 requires felixconfigurations | `project_discovery`, `DISCOVERY_EXPECT` | `test_wrong_group_blocks`, `test_scope_verb_kind_missing_felix`, `test_missing_discovery_scope_rejected` | observations.json scope/verb/kind cases |
| Unsupported vs malformed discovery | `UnsupportedDiscovery` | `test_policy_api_unsupported`, `test_unsupported_discovery` | observations.json `unsupported_discovery_preserved` |
| Per-kind policy allowlist (NP vs GNP) + finite semantic fields | `NP_SPEC_ALLOWED`, `GNP_SPEC_ALLOWED`, `RULE_ALLOWED`, `ENTITY_ALLOWED`, `_policy_rule`, `_policy_entity` | `test_semantic_fields_preserved`, `test_icmp_namespace_selector_preserved`, `test_unsupported_field_rejected`, `test_namespaced_policy_rejects_global_only_fields`, `test_global_policy_fields_preserved` | observations.json `namespaced_policy_global_only_*`, `unsupported_*`, `global_policy_fields_preserved` |
| Typed leaves, no truthiness coercion, port range 1..65535 | `_int_range`, `_icmp`, `_http`, `_container_ports`, `_str/_num/_bool/_enum` | `test_container_port_range_rejected`, `test_http_paths_malformed_rejected`, `test_pod_port_leaf_typed` | observations.json `http_paths_*`, `port_*` |
| Pod identity — kind=Pod, namespace binding, spec+status imageID join | `project_pod_identity`, `NS_EXPECT` | `test_pod_wrong_kind_rejected`, `test_pod_imageID_from_status`, `test_malformed_containers_rejected`, `test_scoped_list_namespace_rejected`, `test_invalid_status_rejected` | observations.json `pod_wrong_kind_*`, `status_image_ids_lost` |
| ObjectStore/CNPG correct paths + named scope | `project_objectstore` (spec.configuration), `project_cluster` (spec.plugins) | `test_named_get_bound`, `test_wrong_binding` | observations.json `named_binding_*`, `wrong_binding_*` |
| Felix mode + precedence limit | `project_felix` (bpfEnabled/nftablesMode/iptablesBackend/nodeSelector) | `test_namespaced_policy_rejects_global_only_fields` (C5 path via `test_literal_api_paths`) | schema-facts.json felixconfiguration; supplemental-design.md §3 |
| Barman directed-flow roles | `supplemental-design.md` §4 (controller/plugin-service/per-instance-sidecar/instance-manager) | — (document check) | supplemental-design.md §4; CNPG 0.13.0 docs |
| API/DNS interpretation under CNI | `supplemental-design.md` §5 | — (document check) | base inventory R2/R3 |
| No-overwrite / no-kubectl / error categories / no raw leak | `main()` (mkdir exist_ok=False, which check, `classify`) | `test_no_overwrite`, `test_no_kubectl` | observations.json `D1_forbidden/connection/timeout/oserror/nonjson` (no SYNTHETIC_RAW) |
| Monitoring not-found / unsupported kinds / Gateway PLANNED | `supplemental-design.md` §6 | — (document check) | base inventory R7/R8/R11-13 |

## Live-only UNKNOWN (legitimate, not offline-blocking)
- Actual runtime platform-child digest vs pinned manifest-list digest (conservative block).
- Effective per-node Felix mode (only cluster-default read; node/env overrides unread).
- Barman per-instance sidecar live identity + direction (S1 not run; declared ports ≠ traffic).
- Effective policy union enforcement (Calico mode; DNAT path).
- Monitoring scrape identity (not-found-in-surveyed-sources).
