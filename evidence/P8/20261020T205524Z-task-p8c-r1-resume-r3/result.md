TASK: P8C-R1 RESUME-R3 CLOSURE EXECUTION (corrective package)
INITIAL_MAIN_SHA: e2cfd530dbd7379ac1a7aa1866d08aed345f39ee
SOURCE_SHA: ff0a04412458955f9d97de1d4694cdf0579a935a
A helpers: DONE (no-echo fail-closed + UNKNOWN_OUTCOME + both-suite 14/14)
B transport: DONE (exact allowlist + host/userinfo guards + fixtures)
C API/freshness/UI: PARTIAL (cursor endpoint/nil-arrays/requireNoQuery/pagination/continuation DONE;
  dynamic ageSeconds + summary application-db + nodes pressure + frontend renderers REMAIN)
D persistence: DONE source (stable id/health/nullable scan/lag elapsed/prune error); integration EXEC = CI
E workflow: PREPARED (rootless/Containerfile/login-order/digest/cosign/test-jobs); NOT dispatched
F netpol: PREPARED (migrator label/CNPG ingress/portal ingress narrow/dataplane); live apply deferred
G evidence: PARTIAL (raw transcripts + race + helper + fixture run; DB/browser runtime = CI)
WORKFLOW_TEMPLATE_APPROVED_FOR_OWNER: NO (pending Architect review)
OWNER_HELPERS_APPROVED_FOR_REAL_CREDENTIALS: NO (pending Architect review)
NETPOL_APPROVED_FOR_APPLY: NO (pending Architect review)
HERMES_RESULT: BLOCKED (source corrective progress; C/G remain partial)
P8C: NOT_FINAL_ACCEPTED
P8D-P8G/P9: NOT_AUTHORIZED
