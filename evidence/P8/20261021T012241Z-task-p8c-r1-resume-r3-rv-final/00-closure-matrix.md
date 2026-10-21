RV final closure (SOURCE_SHA below):

1) All list categories: DONE — listWithContinue (page 200, cap 500) now wraps
   EVERY List call: pods, nodes, services, endpointslices, workloads
   (deployment/sts/ds/rs/job/cronjob), storage (pvc/pv/sc/volumesnapshot),
   backups (velero bsl/backups/restores, cnpg backups), metrics (node/pod),
   events. Boundary tests 201 (full, not truncated) + 501 (capped at 500,
   truncated) + next-page error + single-page + full-cycle.

2) Schema structure check: DONE — store.VerifySchema checks all expected
   application-table columns; readiness (validateMigration) now requires
   ledger version/checksum AND VerifySchema. Negative integration test:
   DROP timeline_events with intact ledger -> VerifySchema fails.

3) Persistence failure/recovery: DONE — persistence_test.go covers initial lag
   -1 (never succeeded), elapsed lag, recovery (failed->recovered), transition
   queue overflow (bounded MaxTransitions=64), snapshotHealth node/db/partial/
   nil. sourceUID/resourceVersion propagated (json:"-" internal fields).

4) Coherent snapshot: events handler reads snapshot once via s.snapshot() for
   envelope; per-response cursor binds snapshot+namespace+since+severity+backend.

5) Workflow: provenance predicate + verify both attestations + Go toolchain
   verify in release (prior commits). CI release NOT_EXECUTED (Gate).
