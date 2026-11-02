# P8C-R1-CANDIDATE-AND-GATES-R1 — result

Дата: 2026-11-02 (UTC). Исполнитель: PRIMARY HERMES. Offline только.
Принятые collector/S1/inventory 9/9 и offline design 3bbc818 не переоткрыты.

## requirement → code/doc → test/check → evidence

| Requirement | Code/doc | Test/check | Evidence |
|---|---|---|---|
| NP-01 exact API tuples | networkpolicy.yaml egress (10.96.0.1/32:443 + 3×/32:6443) | flows_test.go api-tuple + cross-product cases | go test PASS |
| NP-02 remove Barman controller→5432 | networkpolicy.yaml ingress (peer removed) | flows_test.go barman-db-denied | go test PASS |
| NP-03 dataplane 5-label selectors | networkpolicy.yaml dataplane podSelector + Portal ingress peer | flows_test.go dataplane-* + envoy label cases | go test PASS |
| NP-04 preserve existing flows | networkpolicy.yaml (CNPG/operator/DNS/xDS/Portal) | flows_test.go positive cases | go test PASS |
| union-aware rollback | networkpolicy.yaml + design | flows_test.go deny-only (S0 not restored) | go test PASS |
| release gate | P8C_RELEASE_GATE_DRAFT | static template review + bootstrap dependency | draft |
| runtime-readiness gate | P8C_RUNTIME_READINESS_GATE_DRAFT | RD-01 S3/WAL source-bound proposal | draft |
| deployment gate | P8C_DEPLOYMENT_GATE_DRAFT | DEP-01 order/ownership + DEP-02 matrix | draft |

## Offline policy tests
```text
command: go test -count=1 -v ./networkpolicy
go: go1.27.3 linux/amd64 (GOTOOLCHAIN=local)
exit=0, 1 test function (TestCandidatePolicyUnionBothSides), all subtests PASS
START_UTC=2026-11-02T20:09:50Z · END_UTC=2026-11-02T20:09:51Z
```

## Итог
```text
TASK=P8C-R1-CANDIDATE-AND-GATES-R1
ACCEPTED_DESIGN_SHA=3bbc818245e19f42b9ffb64a14bf510d424ee7e8
CANDIDATE_YAML=REVIEW_READY
OFFLINE_POLICY_TESTS=PASS (go1.27.3, exit=0, 1 function / all subtests)
RELEASE_TEMPLATE_CHANGED=NO
RELEASE_GATE_DRAFT=REVIEW_READY
RUNTIME_READINESS_GATE_DRAFT=REVIEW_READY
DEPLOYMENT_GATE_DRAFT=REVIEW_READY
S3_WAL_OBSERVATION_METHOD=SOURCE_BOUND_PROPOSAL (HC-ARCH-STATE available; HC-WAL-PROGRESS UNRESOLVED)
EXTERNAL_PREREQUISITES: CNPG-metrics scraper OR runtime-допуск sidecar; private GHCR package seed (Owner);
                        безопасный execution wrapper для PR-3/5/6+HC-*; tool checksum verification.
COLLECTOR_AND_ACCEPTED_EVIDENCE_UNCHANGED=YES
SOURCE_PACKAGE=REVIEW_READY
CI_RELEASE=NOT_EXECUTED
PHASE2_NEW_RUN_APPROVED=NO
NETPOL_APPROVED_FOR_APPLY=NO
OWNER_HELPERS=NOT_EXECUTED
PRODUCTION_MIGRATION_DEPLOYMENT=NOT_EXECUTED
P8C=NOT_FINAL_ACCEPTED
P8D–P8G/P9=NOT_AUTHORIZED
```
STOP для Architect review.
