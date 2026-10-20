# Architect review: cb8fbac

Date: 2026-10-20 (Europe/Moscow).
REVIEW_TARGET_MAIN: cb8fbacd4cf036a4f7ec43fcb734f7dd751fd7ed
SOURCE_SHA: 871315928f07dd209fc1377451e02931582b8ffc
TREE: bc4484630fb85be798253f24c02a6ce6bacebd2b
DECISION: REWORK_REQUIRED
P8C: IN_PROGRESS / NOT_FINAL_ACCEPTED

## Recovery

GitHub Connector independently read main, recursive tree, recent commits, comparison from f824a22770f5f9bece43fa1ebdef39578b6f4f43 and comparison source8713159→cb8fbac.
Four commits ahead, zero behind; changes limited to Portal and four new evidence files. Source→head adds only evidence. HEAD rechecked unchanged before publication. Historical P8A/P8B acceptance not reopened. No live platform query or mutation by Architect.

## Disposition

| Requirement | Independent disposition |
|---|---|
| R2-01 helpers | PARTIAL: create-only improvement; GetPassWarning continues to write, registry tests missing |
| R2-02 transport | PARTIAL: authority bug fixed; path denylist instead of required allowlist, other guard/deadline gaps |
| R2-03 UI | PARTIAL: new data.items supported; unavailable/stale/pagination/Barman gaps |
| R2-04 API | NOT CLOSED: cursor lacks endpoint, incoherent snapshots, incomplete continuation/freshness/startup arrays |
| R2-05 persistence | NOT CLOSED: NULL readback, duplicate batches, lag/cleanup/status/DB validation gaps; integration tests unexecuted and defective |
| R2-06 workflow | NOT APPROVED: rootful daemon, push before login, missing Containerfile option, invalid literal Cosign version input, digest/provenance/artifact/test gaps |
| R2-07 NetworkPolicy | NOT APPROVED: actual Job not selected; missing DB/metrics/operator ingress; broad Portal ingress; dataplane policy absent; PLAN still8008 |
| R2-08 evidence | INSUFFICIENT: 5 summary lines, no schema-validation suite/raw Go outputs, absent browser/DB CI execution |

WORKFLOW_TEMPLATE_APPROVED_FOR_OWNER=NO
OWNER_HELPERS_APPROVED_FOR_REAL_CREDENTIALS=NO
NETPOL_APPROVED_FOR_APPLY=NO

## Executed locally

Python 3.12.14; Node v24.19.0; PyYAML6.0.3.
1. python3 portal/tools/test_helpers.py → exit0, 7/7 PASS (only UI helper tests).
2. python3 reproduce.py CHECKOUT_ROOT → exit0; recorded observed defects in reproduction-results.json. Exit0 means harness completed, not product PASS.
Both Python helpers ran with synthetic values, real stdlib fallback_getpass and mocked subprocess; no kubectl command reached any cluster. Both emitted2 GetPassWarning and attempted mocked get/create, exit0.
Static YAML check finds migration Job labels={}, selector mismatch, no CNPG ingress from migrator5432/Portal9187, unrestricted cross-namespace Pod ingress8080, no dataplane policy.
Actual app.js renderers executed in Node VM with synthetic DOM/fetch: failed Pods API→"Нет данных"; unavailable healthy snapshot→green status + "нет предупреждений". This is NOT browser/runtime UI evidence.

No Go toolchain in Architect environment; Go build/test/race not rerun here. PostgreSQL integration tests, real browser, CI dispatch, image push/sign, Owner helpers with real secrets, NetworkPolicy apply, migrations, deployment NOT_EXECUTED. Static defects sufficient to reject closure; do not mislabel unexecuted tests as failed runs.

## Required work

See docs/tasks/TASK_P8C_R1_RESUME_R3_CLOSURE_EXECUTION.md for concrete residual fixes, validation and STOP gate. Continue source work autonomously without Owner credentials. No acceptance based solely on checklist text. Keep prior evidence immutable; new corrective evidence only.

## Primary references checked

- https://docs.python.org/3/library/getpass.html — echo-free failure can fall back with GetPassWarning.
- https://kubernetes.io/docs/concepts/services-networking/network-policies/ — policy permissions are additive; both relevant ingress/egress must allow a flow.
- https://github.com/moby/buildkit/blob/master/docs/rootless.md — rootless execution model.
- Exact Connector-read repository paths/blobs: source-index.json.

P8D–P8G/P9 NOT_AUTHORIZED. No backup/latest-restore/PITR/failover/failure tests repeated. No secrets requested/read/copied. Only Architect docs/evidence added by this review.
