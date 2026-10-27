# P8C RV-02 — requirement → code → test → evidence matrix

Governing: reviews c52c42f (G2), e80ff8d (SP-01..05), 3262a9b, 8598f73, 5d0e965.
Source: `portal/networkpolicy/supplemental.py`; tests: `supplemental_test.py` (31/31).
Evidence: `evidence/P8/20261027T060000Z-p8c-rv02-r2-r4-r5/` + earlier review evidence dirs.

| Requirement | Code | Test | Evidence |
|---|---|---|---|
| Calico runtime identity: exact registry+version pin, digest bound to pinned manifest, per-pod verdict, empty/unknown/mixed block | `CALICO_IMAGE_REFS`, `PINNED_DIGEST`, `IMAGE_ID_RE`, `verify_calico_identity()` | `test_identity_exact_contract`, `test_identity_gate_negatives`, `test_calico_identity_present` | observations identity cases (empty/unreviewed/missing/mixed/wrong-ns/unidentified → 0 dependent calls) |
| Discovery gate: exact kind/scope/verbs, C5 requires felixconfigurations, version-pinned request | `project_discovery`, `DISCOVERY_EXPECT`, `READ_CONTRACT` (version-qualified `resource.version.group`) | `test_wrong_group_blocks`, `test_scope_verb_kind_missing_felix`, `test_missing_discovery_scope_rejected` | request_contract + closed cases |
| Unsupported vs malformed discovery | `UnsupportedDiscovery`, D2 classification | `test_policy_api_unsupported`, `test_unsupported_discovery` | unsupported_discovery_preserved (UNSUPPORTED + sanitized output) |
| Policy projection: finite per-kind allowlist, icmp/notICMP/notProtocol/ipVersion/http/serviceAccountSelector/services/tier/notSelector/namespaceSelector | `NP_SPEC_ALLOWED`/`GNP_SPEC_ALLOWED`/`RULE_ALLOWED`/`ENTITY_ALLOWED`/etc, `_policy_rule`, `_policy_entity`, `_http`, `_icmp`, `_sa`, `_services` | `test_semantic_fields_preserved`, `test_icmp_namespace_selector_preserved`, `test_unsupported_field_rejected`, `test_namespaced_policy_rejects_global_only_fields`, `test_global_policy_fields_preserved` | silent_semantic_loss → preserved; unsupported_* → UNSUPPORTED |
| Typed leaves, no truthiness coercion, port range, container types | `_int_range`, `_icmp`, `_container_ports`, `_http` (list validation), `_str/_num/_bool/_enum/_str_list` | `test_container_port_range_rejected`, `test_http_paths_malformed_rejected`, `test_pod_port_leaf_typed` | http_paths_* / port_* cases |
| Pod identity: kind=Pod, namespace binding, spec+status imageID join, malformed reject | `project_pod_identity`, `NS_EXPECT` | `test_pod_wrong_kind_rejected`, `test_pod_imageID_from_status`, `test_malformed_containers_rejected`, `test_scoped_list_namespace_rejected`, `test_invalid_status_rejected` | pod_wrong_kind / malformed / status cases |
| ObjectStore/CNPG correct paths + named scope | `project_objectstore` (spec.configuration), `project_cluster` (spec.plugins), name+namespace binding | `test_named_get_bound`, `test_wrong_binding` | LI-01, named_binding_* cases |
| Felix mode + precedence limit | `project_felix` (bpfEnabled/nftablesMode/iptablesBackend/nodeSelector), `supplemental-design.md` | `test_felix` | schema-facts felixconfiguration |
| Barman directed-flow limit | `supplemental-design.md` (declared ports ≠ traffic) | — | PLAN/flow-matrix Barman direction UNKNOWN |
| API/DNS interpretation (R3) | base inventory R2/R3 (default/kubernetes 10.96.0.1:443→6443, kube-dns 10.96.0.10:53, eps) | — | flow-matrix/gaps/PLAN proof rows |
| No-overwrite / no-kubectl / error categories / no raw leak | `main()` (mkdir exist_ok=False, which check, classify), error stdout suppressed | `test_no_overwrite`, `test_no_kubectl` | D1 forbidden/connection/timeout/oserror/nonjson → no SYNTHETIC_RAW leak |
| Documentation sync (4 docs) | PLAN.md, flow-matrix.md, collection-map.md, gaps.md, supplemental-design.md | — | source-audit blob diff across reviews |

## Live-only UNKNOWN (legitimate, not offline-blocking)
- Actual runtime platform-child digest vs pinned manifest-list digest (out of scope; gate conservatively blocks).
- Effective per-node Felix mode (only cluster-default read).
- Barman plugin actual direction (DB vs S3) — configuration ≠ traffic.
- Effective policy union enforcement (Calico iptables/eBPF mode; DNAT path).
- Monitoring scrape identity (not-found-in-surveyed-sources; no Prometheus operator).
