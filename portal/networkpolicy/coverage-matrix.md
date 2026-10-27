# P8C RV-02 — requirement → code/doc → check → evidence matrix

Source package SHA: b623afb2fa9fd624e3e1ff418adeb9c71b1074df (supplemental.py blob
`ad2edaa9…`, SHA256 `69dac474…`; supplemental_test.py blob `8157b942…`). Test suite
33/33 (exit 0). Current author evidence: `evidence/P8/20261027T080000Z-p8c-rv02-r4b-r5/`.
Independent Connector evidence: `evidence/P8/20261027-p8c-rv02-7584df5-review/`.

| Requirement | Code / Doc | Check | Evidence (exact path/case) |
|---|---|---|---|
| Runtime identity — exact registry/version pin, digest bound to pinned manifest, per-pod verdict | `supplemental.py` `CALICO_IMAGE_REFS`/`PINNED_DIGEST`/`IMAGE_ID_RE`/`verify_calico_identity` | `supplemental_test.py::test_identity_exact_contract`, `test_identity_gate_negatives`, `test_calico_identity_present` | 7584df5-review/observations.json `identity_*` |
| Unsupported identity diagnostic (valid-but-unbound → UNSUPPORTED + retained identity; malformed → PARSE_ERROR) | `supplemental.py` `UnsupportedIdentity` + `verify_calico_identity` | `supplemental_test.py::test_unsupported_identity_diagnostic` | 7584df5-review/observations.json `valid_unsupported_identity`, `malformed_identity_*` |
| Fixed outbound API paths (C1-C5 `get --raw`), literal argv | `supplemental.py` `READ_CONTRACT` | `supplemental_test.py::test_literal_api_paths` | 7584df5-review/observations.json `literal_main_path.calls`; execution.json |
| Discovery gate — exact kind/scope/verbs, C5 requires felixconfigurations | `supplemental.py` `project_discovery`/`DISCOVERY_EXPECT` | `test_wrong_group_blocks`, `test_scope_verb_kind_missing_felix`, `test_missing_discovery_scope_rejected` | 7584df5-review/observations.json scope/verb/kind cases |
| Unsupported vs malformed discovery | `UnsupportedDiscovery` | `test_policy_api_unsupported`, `test_unsupported_discovery` | observations.json `unsupported_discovery_preserved` |
| Per-kind policy allowlist (NP vs GNP) + finite semantic fields | `NP_SPEC_ALLOWED`/`GNP_SPEC_ALLOWED`/`RULE_ALLOWED`/`ENTITY_ALLOWED` | `test_semantic_fields_preserved`, `test_icmp_namespace_selector_preserved`, `test_unsupported_field_rejected`, `test_namespaced_policy_rejects_global_only_fields`, `test_global_policy_fields_preserved` | observations.json `namespaced_policy_global_only_*`, `unsupported_*` |
| Typed leaves, no truthiness coercion, port range 1..65535 | `_int_range`/`_icmp`/`_http`/`_container_ports` | `test_container_port_range_rejected`, `test_http_paths_malformed_rejected`, `test_pod_port_leaf_typed` | observations.json `http_paths_*`, `port_*` |
| Pod identity — kind/namespace/status imageID join | `project_pod_identity`/`NS_EXPECT` | `test_pod_wrong_kind_rejected`, `test_pod_imageID_from_status`, `test_malformed_containers_rejected`, `test_scoped_list_namespace_rejected`, `test_invalid_status_rejected` | observations.json `pod_wrong_kind_*` |
| ObjectStore/CNPG correct paths + named scope | `project_objectstore` (spec.configuration), `project_cluster` (spec.plugins) | `test_named_get_bound`, `test_wrong_binding` | observations.json `named_binding_*` |
| Felix mode + precedence limit (documented, not executable) | `supplemental-design.md` §3 (calico-v3.32.0.yaml FelixConfiguration CRD: default + nodeSelector) | document check (source citation, no unrelated test) | supplemental-design.md §3 |
| Barman four-role directed-flow | `supplemental-design.md` §4 (plugin 9090 `--server-address=:9090` per `plugin-barman-cloud-v0.13.0-release.yaml`) | document check | supplemental-design.md §4 |
| API/DNS interpretation under CNI | `supplemental-design.md` §5 | document check | base inventory R2/R3 |
| No-overwrite / no-kubectl / error categories / no raw leak | `main()` (mkdir exist_ok=False, `which`, `classify`) | `test_no_overwrite`, `test_no_kubectl` | observations.json `D1_*` (no SYNTHETIC_RAW) |
| Monitoring not-found / unsupported kinds / Gateway PLANNED | `supplemental-design.md` §6 | document check | base inventory R7/R8/R11-13 |

## Historical (defect, not closure — preserved, not cited as passing)
- `evidence/P8/20261027-p8c-rv02-010ff33-review/observations.json` `valid_unsupported_identity`
  demonstrated the OLD PARSE_ERROR behavior; superseded by the accepted UNSUPPORTED
  diagnostic in 7584df5-review.

## Live-only UNKNOWN (legitimate, not offline-blocking)
- Platform-child digest vs pinned manifest-list digest (conservative block).
- Effective per-node Felix mode (only cluster-default read; nodeSelector/annotation overrides unread).
- Barman per-instance sidecar live identity + direction (S1 not run; declared ports ≠ traffic).
- Effective policy union enforcement (Calico dataplane mode; DNAT path).
- Monitoring scrape identity (not-found-in-surveyed-sources).
