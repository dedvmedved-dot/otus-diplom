RV-618d677 closure (SOURCE_SHA below). Corrective package, not a full claim.

RV-01 (workflow template):
- helper test cwd-independent via __file__ (works from repo root AND portal/).
  Verified: python3 tools/test_helpers.py from portal cwd -> 14/14 exit 0.
- provenance predicate now top-level SLSA predicate (builder/buildType/
  invocation); cosign GenerateStatement wraps into Statement.
- REMAINING: Go toolchain verified-bytes->build identity; registry subject
  verification; minimal release permissions (test job packages/id-token write);
  private-visibility fail-closed gate; rootless ready-wait fail-on-no-worker.
  CI push/sign/attest = NOT_EXECUTED.

RV-02 (NetPol inventory): NOT_CLOSED this pass (needs cnpg-system namespace
  reconciliation + owning-namespace check + monitoring-flow inventory + offline
  selector tests). Live apply=NO.

RV-03 (transport): DONE — deadlineBody keeps per-request deadline alive through
  body read (cancel on EOF/error/Close); real httptest TLS tests: delayed body
  <deadline reads OK, >deadline read fails, parent cancel aborts, no leak.

RV-04 (continuation + paging): PARTIAL — since unified to source_time (SQL now
  filters source_time, matching memory fallback); truncated propagated for
  EndpointSlices/Velero BSL/metrics node+pod -> Partial. REMAINING: stable
  PostgreSQL pagination under concurrent upsert/insert (ORDER BY ingested_at
  OFFSET counterexample) — needs keyset/bounded-view; per-category 201/501 +
  next-page failure on actual collectors.

RV-05 (dataflow + UI): PARTIAL — Barman sample (collectBarmanMetrics) and WAL
  state/ContinuousArchiving (collectDatabase) now copied into
  Backups.Postgresql in finalize (single point after wg.Wait, no race); Velero
  health aggregates BSL/backups/restores (failed object => not healthy);
  metrics window parsed as duration string. REMAINING: app.js UI setOverall
  critical+stale class, stale overview green cards, nextCursor navigation.

RV-06 (persistence/schema): PARTIAL — lag negative sentinel now reported null
  (OpenAPI number|null min0); VerifySchema checks timeline_events id + object_*
  columns. REMAINING: type/constraint checks (SELECT col LIMIT0 skips type);
  transitions queue not production-read/recovered; TestPersistenceRecovery is
  manual not persistOnce; TLS no-PG*-overrides proof.

RV-07 (helpers): source EOF/control fail-closed retained; 14 mocks pass from
  both cwds. REMAINING: probe-timeout/missing-kubectl/denied-create/registry
  race + credential non-disclosure assertions (no real credentials).

RV-08 (validator): PARTIAL — number min/max added; anyOf checked before null
  gate; unresolved/unsupported $ref now error. REMAINING: format/pattern/length;
  TestSchemaDrivenErrorResponses (error/startup/stale/partial fixtures).
