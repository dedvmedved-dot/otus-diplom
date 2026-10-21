RV remainder closure (corrective package, SOURCE_SHA below):

1) All list categories: PARTIAL — listWithContinue (cap 500) applied to pods/
   nodes/services; listPage/listCap constants; continuation_test.go boundary
   (single page / full cycle / error). REMAINING: applying the helper to the
   remaining 14 list calls (workloads/storage/metrics/velero/events) + 201/501
   boundary fixtures across each.

2) Events: DONE — JSON cursor (RFC3339-safe, no ':' delimiter conflict),
   binds snapshot+namespace+since+severity+backend+offset; backend-mode
   validation (postgresql vs memory-fallback -> CURSOR_EXPIRED on change);
   round-trip test with non-empty RFC3339 since + memory-fallback second-page
   test (200+50 of 250). Unified encode/decode for DB and fallback paths.

3) Persistence: DONE — sourceUID/resourceVersion propagated (model json:"-"
   internal fields -> collectEvents -> persistOnce -> store columns); bounded
   status-transition queue (maxTransitions=64) with ok/failed/recovered;
   initial lag sentinel -1 (never succeeded); upsert refreshes source metadata.
   REMAINING: explicit application-schema structure validation query + dedicated
   failure/recovery tests (transition dedup, source-count refresh) beyond the
   6 existing DB tests.

4) OpenAPI: DONE — schema validator now supports $ref/object/array/string/
   integer/number/boolean, required, enum, additionalProperties:false, nullable,
   type:"null", anyOf, integer min/max; validates all 11 handler responses +
   error responses; negative fixtures prove the validator rejects malformed/null
   responses and accepts valid ones.

5) Workflow: DONE — SLSA provenance predicate (subject/digest/buildType/
   invocation), cosign attest spdxjson + slsaprovenance + verify-attestation for
   BOTH, Go toolchain SHA verify in release job, SBOM+provenance+metadata
   artifacts. NOT_EXECUTED: actual CI push/sign/attest (requires CI Gate).
