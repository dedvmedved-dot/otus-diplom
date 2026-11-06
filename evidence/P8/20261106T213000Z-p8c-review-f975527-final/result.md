# P8C — final source package for review f975527 — result

FINAL_SOURCE_SHA=9a4ed77d3131d0b2078b6917e1a7d4419ec02b65
PRIOR_REWORK=94877dc511c3998bd80bb2e780729367b1abd2e0 (evidence 6a0ad93)
BASE_REVIEW_SHA=f9755275004977eb54f49e44ae0d215670c32151
FAST_FORWARD=YES (6a0ad93..9a4ed77, no force/rebase/amend)
REVIEWED_SOURCE (per review)=a443b5caa56d7de18dd78a2ea407b5e76763f36d

## Verdict
SOURCE_WORK=COMPLETE (full f975527 contract: A1/A2/A3 + B + suite/manifest/runbook)
SOURCE_ACCEPTANCE=AWAITING_ARCHITECT (independent re-check on 9a4ed77)
CI_RELEASE / LIVE_READINESS / PRODUCTION / WORKFLOW_PUBLICATION_DISPATCH = NOT_EXECUTED
P8C=NOT_FINAL_ACCEPTED
P8D–P8G / P9 = NOT_AUTHORIZED

## Full closure matrix (requirement -> code -> test -> result)

### A1 budgets/transport
- remaining body/time enforced INSIDE each I/O: `run_read` lowers the kubectl cap to
  `min(cap, remaining_body)`; `run_kubectl_raw`/`default_http_get`/WAL slots re-check the
  remaining body/time before each read/sleep. Attempt charged before the transport call.
  -> test_remaining_body_byte_is_enforced_inside_io, test_remaining_elapsed_second_...,
     test_timeout_partial_stdout_is_accounted, test_eof_after_deadline_is_not_accepted (PASS).
- partial/timeout/error bytes accounted: `run_kubectl_raw` charges the buffered bytes on
  timeout (with a short real grace read) before raising; EOF after deadline rejected.
- durable + concurrency-safe accounting: `write_budget` takes `fcntl.flock` around the
  read-modify-write, MAX-merges each monotonic field with the on-disk value (no lost update,
  no decrease), and fsyncs file + directory before `os.replace` (crash durability).
  -> concurrency check (threaded writers, final=max, no decrease) PASS.

### A2 health windows/freshness + typed reads
- failure precedence (FAIL never erased by a later sweep); transient INCONCLUSIVE retried
  after a bounded 10s interval (limited by remaining time); freshness gate at verdict
  (every mandatory observation age ≤ 30s else FAIL).
  -> test_first_health_failure_is_not_erased_by_final_sweep, test_health_retry_obeys_interval,
     test_portal_observation_fresh_at_s4_verdict (PASS).
- shared DB/ARCH GET preserved (same path, single read via _READ_CACHE).
- exact GVR binding: every predicate checks kind AND apiVersion (HC-DB/ARCH-STATE
  Cluster@postgresql.cnpg.io/v1; PR-3/HC-DNS EndpointSliceList@discovery.k8s.io/v1; PR-5
  ServiceList@v1; HC-OP PodList@v1; HC-PORTAL Deployment@apps/v1; HC-GW Gateway@
  gateway.networking.k8s.io/v1; PR-6 nine exact (kind,apiVersion) pairs with typed items +
  max_items). -> test_pr5_rejects_wrong_service_namespace, test_pr6_namespace_items_are_validated,
     test_pr6_list_cap_enforced, test_nested_malformed_health_returns_typed_verdict (PASS).
- value-free diagnostics: no raw condition value / field name / unknown key is echoed
  (felix field-drift message no longer includes the key).

### A3 WAL identity + operation boundary
- instanceRole=primary checked on BOTH bracket sides (before + after pod).
- baseline stores pod UID + observed time and re-checks the UID on read.
- operation_end_utc must bind a verified action_receipt (source_sha+package_sha256+
  operation_end_utc), not an arbitrary number ≥ issued_at.
- clock_evidence.gate_sha256 binds to gate_identity_sha256(gate) (source/package/issued_at/
  expiry/mode/context), not the package hash.

### B release/seed routes
- release Future execution gate requires a typed gate document (missing -> nonzero).
- first-creation checks the gate's OWN repository/package/workflow fields.
- scan-image binds exact image@digest (substring IMAGE insufficient).
- seed Record step tolerates absent APP_IMAGE_DIGEST (first bootstrap).
- release cleanup `always()` + bounded `timeout 5` buildctl readiness (both templates);
  seed uploads the full proof package (registry/private/build/association evidence).
- fake-tool route E2E (test_route_e2e.py, 4): REUSE/STOP -> 0 build/push; CREATE_ALLOWED ->
  precheck+build+postproof+cleanup; release gate required + full route order + cleanup(always).

### Suite / manifest / runbook
- corrected authority-fixture (exhausted budget via budget_path(gate)) in active copies.
- digest test uses a real file (valid -> exact digest + exit 0; invalid -> nonzero).
- offline pin verification (cached bytes + prior evidence, no upstream download).
- runbook + matrix synced to the actual execution.

## Offline suite (single launcher, final source SHA 9a4ed77)
23 readiness + 25 residual-working + 3 qualification + 4 release + 7 release-negative
+ 4 route E2E + 28 regression + 14 scheduler-authority + 15 contract-authority
+ 34 completion-authority + 20 residual-contract = 177 methods, plus qualification CLI
(qualified:true), offline pin verification (10/10), bash -n + py_compile.

Result: SUITE RESULT: PASS (launcher exit 0). Counts are reference; the criterion is
execution of the whole agreed contract above.

## External prerequisites (NOT_EXECUTED; future execution gate)
Real clock evidence, CI runtime, private GHCR registry visibility, cosign/syft/trivy crypto
execution, live E2E S0->S4, workflow publication/dispatch, production apply/migration.

Evidence: raw-transcript.txt, secret-scan.txt (no matches), source-manifest.txt.
