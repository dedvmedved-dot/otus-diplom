RV-01..08 closure matrix (corrective package):

RV-01 workflow: PARTIAL — BuildKit URL v0.34.0/buildkit-v0.34.0 (correct asset),
  cosign digest 4629c757... (official), Go checksum guaranteed (fail if absent),
  renderer-smoke in test job, package.json+lock (jsdom 24.1.3 pinned, node_modules
  gitignored). REMAINING: provenance/SBOM attestation, private visibility proof,
  rootlesskit checksum (upstream SHA unverified by Architect).

RV-02 NetworkPolicy: DONE — gateway name portal-gateway (matches gateway.yaml),
  dataplane xDS egress (control-plane 18000), PLAN.md 8000 (verified) + flow matrix.

RV-03 transport: DONE — endpointslices moved to discovery.k8s.io/v1 (actual typed
  client path), per-request 5s deadline, positive+negative test fixtures updated.

RV-04 pagination: PARTIAL — Database.Conditions non-null (schema array). REMAINING:
  continuation for all list categories (not just pods), coherent single snapshot
  per response, events cursor since/severity binding, health degradation by age.

RV-05 UI: DONE — storageHealth unknown (not healthy), Barman firstRecoverability-
  PointTimestamp, observed schedule/target precedence, lastFailed null -> "—",
  WAL state + continuousArchiving, backup Health cell = health value.

RV-06 persistence: PARTIAL — snapshotHealth includes node/db health, upsert ON
  CONFLICT refreshes source metadata (uid/rv/time/severity/message). REMAINING:
  readiness bounded retry, TLS minimum hardening, sourceUID/resourceVersion
  propagation, status-transition queue, failure/recovery tests.

RV-07 helpers: DONE — EOF/cancel (Ctrl-C/D) fail-closed before write; terminal
  state restored; both helpers; 14/14 tests still PASS.

RV-08 schema: PARTIAL — real jsdom renderer (correct Barman field asserted),
  fresh -count=1 for all Go tests + integration, SOURCE_SHA + tool versions in
  raw transcript. REMAINING: OpenAPI schema-driven validation of actual handler
  responses (types/enums/additionalProperties).
