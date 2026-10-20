R2-01..08 disposition (corrective package 9e38be2):

R2-01 Owner helpers: FIXED — create-only (kubectl create, atomic no-overwrite),
fail-closed (nonzero get -> STOP before write), TTY required, subprocess timeout,
auth-only dockerconfig (no fake password, Owner inputs username), no argv/env/temp/log.
  mock tests: NOT_YET (planned R2-08).

R2-02 transport guard: FIXED — parse canonical base URL once (scheme+authority),
no more https://host:port vs host:port mismatch; exact path allowlist forbids
proxy/log/exec/attach/portforward/secrets/token; no redirects. Tests: positive
allowed GET + wrong host/scheme/method/path/redirect (transport_test.go).

R2-03 frontend: FIXED — app.js rewritten to data.items/overall/structured warnings/
backup domains/Barman/events; no hardcoded healthy; null/empty/error/stale visible;
recent events + PG backup meta on overview. Browser smoke: NOT_RUN (no runtime).

R2-04 contract/freshness: PARTIAL — non-null sources/warnings arrays; Subsystem
observedAt from snapshot time (not HTTP time); partial propagation restored.
Remaining: cursor bound to endpoint+filter (currently snapshot-only), full
continuation loop, events pagination on coherent snapshot.

R2-05 persistence: PARTIAL — dedup key includes event UID + involvedObject UID
(no merge on recreated object); UpsertEvent idempotent (source count, not +1);
truthful LagSeconds/DataLoss on all write/cleanup paths.
Remaining: memory fallback, status-transition events, isolated DB integration tests.

R2-06 workflow template: NOT_YET — template not reworked to full R3 (rootless
BuildKit, immutable digest, final OCI SBOM+scan, cosign verify). Kept as template;
Owner publishes via GitHub UI after review (no workflow-scope token needed).

R2-07 NetworkPolicy: NOT_YET — full source->destination:port matrix + exact
manifests not produced (instance-manager port 8000 vs 8008 not verified).

R2-08 evidence/tests: PARTIAL — transport positive/negative tests added; 11
handler contract tests, helper mock tests, DB integration tests still missing.
