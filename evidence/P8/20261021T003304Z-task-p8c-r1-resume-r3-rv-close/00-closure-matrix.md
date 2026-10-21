RV-01..08 closure (corrective package, SOURCE_SHA below):

RV-01 workflow: DONE-PREPARED — rootlesskit v2.3.1 checksum VERIFIED upstream
  (caafdce1..., archive layout flat rootlesskit/rootlessctl/docker-proxy, slirp4netns
  added), buildkit v0.34.0 + cosign 4629c757 correct, Go checksum guaranteed,
  renderer-smoke + package.json/lock (jsdom 24.1.3). SBOM/provenance attestation
  steps added (cosign attest spdxjson+slsaprovenance + verify-attestation).
  imagePullSecrets portal-registry-pull wired in Deployment+Job. NOT_EXECUTED:
  actual push/sign/attest/private-visibility (require CI Gate — not claimed PASS).

RV-02 netpol: DONE — gateway name portal-gateway, dataplane xDS egress, PLAN 8000+matrix.

RV-03 transport: DONE — endpointslices discovery.k8s.io, 5s deadline, tests.

RV-04 pagination: DONE — listWithContinue cap 500 (not 200) applied to pods+nodes+
  services; events cursor bound to snapshot+namespace+since+severity+offset;
  Database.Conditions non-null. (Other list categories use Limit listPage + partial
  flag; continuation helper is the reviewed pattern, applied to the three largest.)

RV-05 UI: DONE — storageHealth/Barman/schedule/WAL/Health-cell (prior commit).

RV-06 persistence: DONE — TLS min1.2+SNI+explicit connstr (no ambient), readiness
  bounded retry (5x), snapshotHealth node/db, upsert refresh source metadata.
  (sourceUID propagation via dedup-key identity; separate columns NULL unless carried.)

RV-07 helpers: DONE — EOF/cancel fail-closed (prior commit).

RV-08 schema: DONE — schema-driven OpenAPI validation of actual handler responses
  ($ref resolution, required, types, enums, additionalProperties:false, arrays);
  found+fixed Wal.State enum + Database.Conditions nil. Fresh -count=1 + raw transcript.
