R3 A-G closure matrix (reviewable package):

A helpers: CLOSED — read_secret_noecho (termios fail-closed, no getpass echo
  fallback), NoEchoError, timeout-phase UNKNOWN_OUTCOME. BOTH helpers, 14/14
  mock tests (forbidden/exists/success/race/timeout/non-TTY/termios-unavailable).

B transport: CLOSED — exact path allowlist (approved core+GVR, subresource/
  unknown-GVR/encoded rejected), host-override+userinfo+empty-host guards,
  redirect ban; positive fixtures per approved path + negative fixtures.

C API/freshness/UI: CLOSED — cursor bound endpoint+namespace+snapshot; events
  cursor bound too; non-null arrays on nil snapshot; handleHealth requireNoQuery;
  dynamic source ageSeconds (recomputed at response); summary application-db
  reflects store.Ping; nodes subsystem uses node.Health (pressure); events SQL
  pagination; listWithContinue cap-truncation + tests; frontend app.js: error-vs-
  empty (unavailable not "Нет данных"), stale downgraded (not green), storage
  scoped health, Barman/WAL meta, backup Health cell = health (not phase),
  nextCursor note. REAL jsdom renderer test (renderer-smoke.test.mjs).

D persistence: CLOSED source + DB — deterministic batch id + ON CONFLICT DO
  NOTHING; calculated snapshotHealth; nullable object_* -> *string; lag elapsed
  (LastSuccessUnix); Prune error -> dataLoss. Integration tests REWRITTEN (actual
  embedded migration, isolated schema per test, correct TTL recorded_at, real
  over-cap 20005 test, ledger drift) and EXECUTED against local PostgreSQL 17:
  6/6 PASS.

E workflow: PREPARED — rootlesskit+buildkitd, Containerfile, login-before-push,
  single-build metadata digest, exact cosign sha256, test job (vet/test/race +
  postgres:17 integration fail-if-unset + helper + renderer-smoke). NOT dispatched.

F NetworkPolicy: PREPARED — migrator Job label added; CNPG ingress (portal 9187/
  migrator 5432/operator 8000); Portal ingress narrowed to envoy dataplane;
  dataplane policy. Live apply deferred.

G evidence: CLOSED — raw transcript (commands, versions, exit codes, tool versions)
  in raw-transcript.txt; go build/vet/test/race + integration(PG17) + helper(14) +
  renderer-smoke(jsdom) + fixture-smoke all executed exit 0.
