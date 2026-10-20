R2-01..08 closure matrix (reviewable package, source SHA below):

R2-01 Owner helpers: CLOSED — kubectl create (atomic no-overwrite), fail-closed
  (nonzero get -> STOP before write), TTY required, auth-only dockerconfig,
  subprocess timeout. Mock tests test_helpers.py: 7/7 PASS (valid/wrong-len/
  bad-alphabet/forbidden/existing/success/race-no-overwrite).

R2-02 transport guard: CLOSED — canonical URL parse (no https://host:port vs
  host:port mismatch), path allowlist (proxy/log/exec/attach/portforward/
  secrets/token), no redirects. transport_test.go: positive allowed GET +
  wrong host/scheme/method/path/redirect.

R2-03 frontend: CLOSED — app.js maps data.items/overall/structured warnings/
  backup domains/Barman/events; no hardcoded healthy; null/empty/error/stale
  visible; recent-events + pg-backup-meta on overview. Browser DOM smoke is a
  CI item (fixture API + jsdom), not run locally (no headless browser).

R2-04 contract/freshness/pagination: CLOSED — cursor bound to (snapshot +
  namespace filter + endpoint) with CURSOR_EXPIRED on mismatch; events
  pagination pushed to SQL (namespace + LIMIT/OFFSET, no hidden row loss);
  continuation helper listWithContinue applied to pods; non-null sources/
  warnings arrays; Subsystem.observedAt from snapshot time.

R2-05 persistence: CLOSED — dedup key includes event UID + involvedObject UID
  (recreated object not merged); UpsertEvent idempotent (source count, not +1);
  truthful LagSeconds/DataLoss on all write/cleanup paths; /events memory
  fallback (storage=memory-fallback); portal-status transition event on write
  failure; DB integration test (integration_test.go, -tags integration,
  postgres:17 CI service) covers dedup-idempotent/UID-recreate/prune-TTL/
  migration-noop-mismatch.

R2-06 workflow template: PREPARED — ubuntu-24.04 (pinned), rootless BuildKit
  0.34.0, immutable digest push, final-image SBOM + Trivy scan, Cosign 3.1.3
  keyless sign+verify exact D2 identity/issuer, provenance source SHA/build time.
  Run+verify = CI (Owner publishes + dispatches after review).

R2-07 NetworkPolicy: PREPARED — verified flow matrix (CNPG instance-manager
  port 8000 confirmed, not 8008; labels cnpg.io/podRole=instance; API 6443 at
  172.30.140.101-103; DNS 10.96.0.10; S3 172.30.143.10:443) + exact manifests
  portal/manifests/networkpolicy.yaml (p8c-cnpg-existing-flows first, baseline,
  portal/migrator flows). Live apply deferred (D1 gate).

R2-08 evidence/tests: CLOSED (source-level) — 11 handler contract tests
  (contract_test.go: all 11 endpoints 200 + envelope fields + data shapes +
  400/401/404/405 errors); transport positive/negative; helper mock 7/7; DB
  integration (CI); browser DOM smoke = CI item.
