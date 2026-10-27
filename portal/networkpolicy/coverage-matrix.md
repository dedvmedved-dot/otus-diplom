# P8C RV-02 — verified requirement / code / check / evidence matrix

Architect reconciliation after 7970620, 2026-10-27.
Reviewed executable source: b623afb2fa9fd624e3e1ff418adeb9c71b1074df.
supplemental.py blob ad2edaa92de59f657599190842fa7fe68373b582,
SHA256 69dac4747856e5f88ac4666e884fe1263777ca5cb64b197741a4b370c093aa4c.
supplemental_test.py blob 8157b942d9f4066dfda7448f2c71fe170b24f657,
SHA256 991654157f97ab8d9a07948c74423dfbbb44acd6e1c635cd6a21a1083a4e6408.
These files remain byte-identical. The accepted 33-test run is REUSED, not rerun.

Evidence identifiers resolve to these exact repository files:
- E1: `evidence/P8/20261027-p8c-rv02-7584df5-review/execution.json`, array item 0:
  argv `["python3","supplemental_test.py","-v"]`, exit=0, stderr contains 33 unittest results.
  Test names below are exact method names in supplemental_test.py. Each has an
  executed record in this transcript. E1 item 1 is the independent reviewer harness.
- E2: `evidence/P8/20261027-p8c-rv02-7584df5-review/observations.json`; case keys below are literal top-level keys.
  Dot `.calls` selects the actual subprocess argv list within a case.
- E3: `evidence/P8/20261027-p8c-rv02-7970620-review/doc-check.json`;
  current documentary/source/reference checks, not runtime qualification.
- Base: `evidence/P8/20261026T173244Z-p8c-rv02-live-inventory/inventory.jsonl`;
  Rn is the 1-based record number. Original aggregate EXIT=1 is preserved.
- Author executable evidence: `evidence/P8/20261027T080000Z-p8c-rv02-r4b-r5/supplemental-test.txt`.
  Documentary submission: `evidence/P8/20261027T090000Z-p8c-rv02-d1-d3-r5/`.
  Neither is relabeled a fresh test run in this reconciliation.

All code references below are in portal/networkpolicy/supplemental.py;
test methods are in portal/networkpolicy/supplemental_test.py.
Behavioral checks are PASS in the reused evidence. Documentary acceptance is
bounded by the explicit UNKNOWN/live limits; it does not prove runtime flows.

| Requirement | Code / document | Check | Exact evidence identifier / selector |
|---|---|---|---|
| Runtime identity | CALICO_IMAGE_REFS / PINNED_DIGEST / IMAGE_ID_RE / verify_calico_identity | test_identity_exact_contract; test_identity_gate_negatives; test_calico_identity_present | E1 /0/stderr; E2 identity_wrong_registry, identity_wrong_version, identity_missing_imageID |
| Unsupported identity vs malformed | UnsupportedIdentity / main | test_unsupported_identity_diagnostic | E1 /0/stderr; E2 valid_unsupported_identity, malformed_identity_json, malformed_identity_types |
| Fixed requests + response boundary | READ_CONTRACT / project_config / _require | test_literal_api_paths; test_wrong_binding | E1 /0/stderr; E2 literal_main_path.calls, wrong_response_version |
| Discovery kind/scope/verbs/dependency | project_discovery / DISCOVERY_EXPECT / main | test_wrong_group_blocks; test_scope_verb_kind_missing_felix; test_missing_discovery_scope_rejected | E1 /0/stderr; E2 bad_discovery |
| Unsupported discovery | UnsupportedDiscovery / SUPPORTED_POLICY_KINDS | test_policy_api_unsupported; test_unsupported_discovery | E1 /0/stderr (no nonexistent observations key) |
| Finite per-kind and nested policy boundary | NP_SPEC_ALLOWED / GNP_SPEC_ALLOWED / RULE_ALLOWED / ENTITY_ALLOWED / HTTP_ALLOWED / HTTP_PATH_ALLOWED / ICMP_ALLOWED / SA_ALLOWED / SERVICES_ALLOWED | test_semantic_fields_preserved; test_icmp_namespace_selector_preserved; test_unsupported_field_rejected; test_namespaced_policy_rejects_global_only_fields; test_global_policy_fields_preserved | E1 /0/stderr |
| Types / port ranges / no truthiness coercion | _int_range / _icmp / _http / _container_ports | test_container_port_range_rejected; test_http_paths_malformed_rejected; test_pod_port_leaf_typed | E1 /0/stderr |
| Pod binding and imageID join | project_pod_identity / NS_EXPECT | test_pod_wrong_kind_rejected; test_pod_imageID_from_status; test_malformed_containers_rejected; test_scoped_list_namespace_rejected; test_invalid_status_rejected | E1 /0/stderr |
| ObjectStore / Cluster projection and binding | project_objectstore / project_cluster | test_named_get_bound; test_wrong_binding | E1 /0/stderr; D1 field/source inspection |
| No-overwrite / no-kubectl | main | test_no_overwrite; test_no_kubectl | E1 /0/stderr |
| Error categories and retained-output safety | classify / main / projections | independent mocked main-path checks | E2 C1_forbidden, C1_api_not_served, C1_connection, C1_timeout, identity_wrong_registry, malformed_identity_json |
| D1 per-read types / normalization / dispositions | supplemental-design.md section 1 + named code helpers | document/source check | E3 checks; reviewed source blobs below |
| D2 Felix priority and host/tier limit | supplemental-design.md section 3 | exact upstream source + repository CRD check | E3 sources.calico; E3 checks; no executable precedence claim |
| D3 Barman/API/DNS | supplemental-design.md sections 4–5; flow-matrix.md; gaps.md | versioned design / source manifest / base-evidence reconciliation | E3 sources + checks; base inventory R1/R2/R3/R9/R10 |
| Monitoring / Gateway / optional policy limits | supplemental-design.md section 6; collection-map.md | document check; unsupported discovery test above | E3 checks; base inventory R6/R7/R8/R11/R12/R13/R14 |

## Historical evidence

`evidence/P8/20261027-p8c-rv02-010ff33-review/observations.json`
valid_unsupported_identity demonstrates the OLD PARSE_ERROR defect.
It is preserved as historical negative evidence and is not used to prove closure.
Previously cited keys such as unsupported_discovery_preserved, named_binding_*,
http_paths_* and D1_* do not exist in E2; the relevant coverage now points to
the actual E1 test records above.

## Limits

This closes source/documentary D1–D3/R5 for the existing bounded collector.
Live identity/digest compatibility, effective Felix configuration, host/tier policy
evaluation, S3 routing, Barman directed traffic and monitoring completeness remain
UNKNOWN as specified in supplemental-design.md and gaps.md.
No new read, provider, accepted runtime format or apply/CI/production gate is added.
