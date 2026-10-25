# P8C RV-02 — requirement → code → test → evidence matrix

| Requirement (task §) | Code/manifest | Test | Evidence |
|---|---|---|---|
| G1 access path only via authorized session | access-path.md | — | access-path.md |
| G2 safe projection (no managedFields/annotations) | inventory.py `project()` | inventory_test.py TestProjection | python-inventory-mock-test.txt |
| G2 error categories (TIMEOUT/FORBIDDEN/API_NOT_SERVED/CONNECTION) | inventory.py `classify()` | inventory_test.py TestClassify | python-inventory-mock-test.txt |
| G2 JSONL write + exit codes | inventory.py `main()` | inventory_test.py TestMain | python-inventory-mock-test.txt |
| G2 fail-closed on no kubectl (before mkdir) | inventory.py `main()` | inventory_test.py test_no_kubectl_blocks | python-inventory-mock-test.txt |
| G3 flow matrix (14 FLOW-IDs, proof type) | flow-matrix.md | — | flow-matrix.md |
| G3 precise UNKNOWN gaps (8) | gaps.md | — | gaps.md |
| G4 candidate policy union both sides | manifests/networkpolicy.yaml + flows_test.go | TestCandidatePolicyUnionBothSides (18 subtests) | go-networkpolicy-test.txt |
| G4 name+namespace Gateway ownership | networkpolicy.yaml (dataplane selector) | wrong-owner-denied subtest | go-networkpolicy-test.txt |
| G4 migrator no API/S3, Portal no BMC/SSH/mutation | networkpolicy.yaml (migrator/portal egress) | migrator-api-denied / app-s3-denied / management-denied | go-networkpolicy-test.txt |
| G4 deployment/Job labels match manifests | flows_test.go (manifest parse) | workload-label check | go-networkpolicy-test.txt |
| G7 operator handoff | operator-handoff.md | — | operator-handoff.md |
| G7 secret scan | secret-scan.txt (heuristic) | — | secret-scan.txt |

## Not covered by design (documented)
- CNI enforcement point / DNAT: UNKNOWN (gaps.md #8); offline Go evaluator is
  standard NetworkPolicy semantics, NOT CNI/runtime validation.
- Live rows marked UNKNOWN: require operator inventory (gaps.md).
