TASK: P8C-R1 RESUME-R3 CLOSURE EXECUTION (complete reviewable package)
INITIAL_MAIN_SHA: e2cfd530dbd7379ac1a7aa1866d08aed345f39ee
SOURCE_SHA: ffed5d83feffaa91c75bb42cce0b3d48f936078c
A helpers: CLOSED (no-echo fail-closed + UNKNOWN_OUTCOME + both-suite 14/14)
B transport: CLOSED (exact allowlist + guards + fixtures)
C API/freshness/UI: CLOSED (cursor/nil-arrays/requireNoQuery/dynamic-age/db-health/
  nodes-pressure/frontend error+stale+Barman+nextCursor + jsdom renderer test)
D persistence: CLOSED (stable id/health/nullable scan/lag/prune + integration 6/6 on local PG17)
E workflow: PREPARED (rootless/Containerfile/login-order/digest/cosign/test-jobs); NOT dispatched
F netpol: PREPARED (migrator label/CNPG ingress/portal ingress narrow/dataplane); live apply deferred
G evidence: CLOSED (raw transcript + race + integration(PG17) + helper + renderer(jsdom))
WORKFLOW_TEMPLATE_APPROVED_FOR_OWNER: NO (pending Architect review)
OWNER_HELPERS_APPROVED_FOR_REAL_CREDENTIALS: NO (pending Architect review)
NETPOL_APPROVED_FOR_APPLY: NO (pending Architect review)
HERMES_RESULT: PASS (source corrective package; NOT runtime/FINAL ACCEPTED)
P8C: NOT_FINAL_ACCEPTED
P8D-P8G/P9: NOT_AUTHORIZED
