RV-618d677 remainder closure (SOURCE_SHA below). Cumulative with prior packages.

RV-04 (stable paging): DONE — ListEvents now keyset paginated (id < afterID,
ORDER BY id DESC) on the stable bigserial identity; concurrent insert+upsert
regression (TestIntegrationListEventsKeysetStableUnderInsert) proves page2 does
not duplicate/skip when a new row is inserted and an old row's ingested_at
changes between pages. since unified to source_time. Truncated propagated for
EndpointSlices/Velero BSL/metrics node+pod.

RV-06 (schema types/constraints): DONE — VerifySchema now checks information_
schema column data_type (id bigint, dedup_key varchar, source_time/ingested_at
timestamptz, occurrence_count bigint) + UNIQUE constraint on dedup_key. Negative
missing-column test retained.

RV-01 (workflow): PARTIAL+ — job-scoped minimal permissions (test job contents:
read only; release job adds packages+id-token write); rootless buildkitd ready
wait fails closed with diagnostic log tail. REMAINING: Go toolchain verified
bytes->build identity; registry subject verification; private-visibility
fail-closed gate (Owner prerequisite). CI release NOT_EXECUTED.

RV-08 (validator): PARTIAL+ — added string format(date-time)/pattern/minLength/
maxLength; number min/max; anyOf before null gate; unresolved $ref errors.
REMAINING: TestSchemaDrivenErrorResponses (actual error/startup/stale/partial
response fixtures against error schema).

RV-05 (UI): NOT_CLOSED this pass — app.js setOverall critical+stale, stale
overview green cards, nextCursor navigation remain.

RV-07 (helper assertions): NOT_CLOSED — probe-timeout/missing-kubectl/denied-
create/registry race + credential non-disclosure fixtures remain.

RV-02 (NetPol inventory): NOT_CLOSED — cnpg-system namespace reconciliation,
owning-gateway-namespace check, monitoring-flow inventory, offline selector
tests remain.
