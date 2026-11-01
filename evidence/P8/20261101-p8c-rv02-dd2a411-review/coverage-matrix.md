# Requirement -> code -> test -> evidence

Scope: source05d61ac74e88256adee455dcefd2d9c33335b6b3, reviewed main dd2a4115e6d4c7799a4acf5156a42ab0590ceea8.
Code paths below are portal/networkpolicy/. Test IDs refer to followup_test.py unless prefixed.
All rows PASS in this independent offline replay; no live claims.

| Requirement | Code | Test | Evidence |
|---|---|---|---|
| B1 bound before projection, single501 and third-page remaining100 | followup.py:_list_pages | TestBoundedProjection.test_single_501_projects_only_500; test_third_page_remaining_budget | followup-tests.txt; bounded-projection-tests.txt |
| B1 discard suffix UNKNOWN, preserve500; retained malformed invalidates | _list_pages | TestBoundedProjection.test_invalid_discarded_suffix_not_projected; TestRemainingContract.test_projector_failure_stops_continuation | bounded-projection-tests.txt; observations.json *_bounded_prefix_invalid_suffix |
| B2 per-item validated after strict serialization; no false count | _list_pages | TestBoundedProjection.test_validated_count_on_midpage_error; TestRemainingContract.test_projector_journal_is_not_success | bounded-projection-tests.txt; regression-tests.txt |
| R1 project before next-page, unknown semantics -> UNSUPPORTED empty | _list_pages; PROJECTOR | TestRemainingContract.test_projector_failure_stops_continuation; test_unsupported_stops_continuation | regression-tests.txt; observations.json *_badprojector_* / *_unsupported_projector |
| R1 exactly one journal/attempt, real exit, terminal unknown exit=null | _list_pages.finish | TestRemainingContract.test_unknown_later_process_returncode_is_null; test_one_journal_record_per_repeated_token_attempt; TestR1JournalAndExit | regression-tests.txt; observations.json first/later transport cases |
| R2 strict envelope, kind/apiVersion, metadata, null, scope, finite output | _list_pages; _cluster_meta; _cluster_check; _finite_num | TestPagination; TestR2Boundaries; TestClusterScope; TestStructuralIsolation | followup-tests.txt; observations.json *_null_continue / *_null_namespace / *_nonfinite |
| R3 typed versions and uniqueness across ALL names, dependent blocked | project_crd_schema | TestR3CRDVersions; TestRemainingContract.test_duplicate_nonselected_versions_rejected | followup-tests.txt; regression-tests.txt |
| R4 five-kind matrix: empty/one-page/distinct201/501/overlong/error/RV | _list_pages | TestFiveListMatrix; TestPagination; independent reproduce.py all five kinds | followup-tests.txt; observations.json; reproduce-summary.json (151/151) |
| FU-01 exact context before dir/subprocess | main | TestContext | followup-tests.txt; observations.json wrong_context |
| FU-03 first error actual disposition, later transport retains prefix | _list_pages | TestListErrors; TestRemainingContract.test_unknown_later_process_returncode_is_null | observations.json *_forbidden/notserved/connection/timeout/oserror_first/later |
| FU-04 isolation, independent reads continue, no scalar crash | main; _cluster_meta; projectors | TestStructuralIsolation; TestRemainingContract | followup-tests.txt; regression-tests.txt |
| FU-05 schema fingerprint, annotation-only vs semantic description | normalize_schema; project_crd_schema | TestCRDSchema | followup-tests.txt |
| FU-06 CNP/HEP/Tier typed semantics, null vs absent, directional allowlists, finite values | project_cnp; project_hep; project_tier; helpers | TestCNP; TestHEP; TestTier | followup-tests.txt |
| FU-07 resource-specific discovery dependencies | _project_d1; main | TestDiscovery | followup-tests.txt; observations.json discovery_* (20 variants) |
| S1 accepted identity legacy/config + fail-closed, safe unsupported diagnostic | supplemental.py:verify_calico_identity; main | TestIdentity; TestR2Boundaries.test_unbound_identity_retained; supplemental_test.py | followup-tests.txt; supplemental-tests.txt; observations.json identity_unsupported_diagnostic |
| R4 actual archived I1 mapping, explicit synthetic distinction | derived-i1-fixture.json; test harness | TestRemainingContract.test_real_archived_identity_mapping; TestHappyPath.test_three_synthetic_pod_identity_formats | followup-tests.txt; regression-tests.txt; fixture unchanged blob4dca83405d37d72d551007930e742e8d4b102b9b |
| URL encoded continuation, token not emitted, repeated/RV/cap stop | _list_pages | TestPagination.test_repeated_token_partial; test_rv_swap_partial; TestEnv.test_no_continue_token_in_output | followup-tests.txt; observations.json journal_encoded_token |
| No overwrite/no kubectl before output; no raw credential/error leaks | main; typed projectors | TestEnv | followup-tests.txt; observations.json transport/error outputs |
| Final provenance and exact-byte reproducibility | Connector fetch + verify.py | independent replay; hash checks | execution.json; observations.json.hashes; replay.md; acceptance document |

Counters: 99 author unittest methods, 36 supplemental regression methods, 7 previous reviewer methods,
4 bounded reviewer methods. Parameter cases overlap; do not sum these as independent requirements.
151 observation checks all explicitly matched; reproduce.py exit0 by itself is not PASS.
Original author UTC is not substituted with reviewer UTC. Live coverage/effective policy union remains UNKNOWN.
