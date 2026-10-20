R3 sections A-G disposition (corrective package, SOURCE_SHA below):

A (helpers): DONE — read_secret_noecho via termios, fail-closed (no getpass
  fallback-to-echo); NoEchoError; timeout-phase distinction (timeout-after-create
  -> UNKNOWN_OUTCOME, never "no write attempted"); both helpers; 14/14 mock tests
  (UI + registry: forbidden/exists/success/race/timeout/non-TTY/termios-unavailable).

B (transport): DONE — exact path allowlist (approved core+GVR, subresource/
  unknown-GVR/encoded rejected); host override + userinfo + empty-host guards;
  redirect ban; positive fixtures per approved path + negative fixtures.

C (API coherence): PARTIAL — cursor bound to endpoint+namespace+snapshot (events
  too); non-null arrays on nil snapshot; handleHealth requireNoQuery; events
  SQL pagination; listWithContinue cap-truncation fixed + tests. REMAINING:
  dynamic source ageSeconds, summary application-db truth, nodes pressure,
  frontend nextCursor/error-vs-empty/stale/Barman-WAL renderers (app.js).

D (persistence): DONE (source) — deterministic batch id + ON CONFLICT DO NOTHING;
  calculated snapshotHealth; nullable object_* scan into *string; lag as elapsed
  seconds (LastSuccessUnix); Prune error -> dataLoss. REMAINING: readiness bounded
  retry; actual isolated-DB integration EXECUTION (CI postgres:17, not run here).

E (workflow): PREPARED — rootlesskit+buildkitd (no sudo), Containerfile option,
  login BEFORE build/push, single-build metadata digest, exact cosign sha256,
  test job (go vet/test/race + postgres:17 integration FAIL-if-unset + helper +
  fixture). NOT dispatched (gate).

F (NetworkPolicy): PREPARED — migrator Job label added; CNPG ingress adds portal
  9187/migrator 5432/operator 8000; Portal ingress narrowed to envoy dataplane
  (namespace + owning-gateway-name); dataplane policy added. Live apply deferred.

G (evidence): PARTIAL — raw transcripts below; 11-handler contract + transport
  allowlist + continuation + helper(14) + fixture-shape tests run. REMAINING:
  actual postgres:17 integration run + real DOM/browser renderer run (CI).
