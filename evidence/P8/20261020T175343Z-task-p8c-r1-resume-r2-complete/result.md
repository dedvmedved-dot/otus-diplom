TASK: P8C-R1 RESUME-R2 CORRECTNESS (complete reviewable package)
INITIAL_MAIN_SHA: 4ed6a83616d78511c21b1d54c0bafcfc4d6d5c55
SOURCE_SHA: 871315928f07dd209fc1377451e02931582b8ffc
R2-01: CLOSED (helpers create-only + fail-closed + mock 7/7)
R2-02: CLOSED (transport guard + positive/negative tests)
R2-03: CLOSED (frontend new API; browser DOM smoke = CI)
R2-04: CLOSED (cursor binding + events SQL pagination + continuation)
R2-05: CLOSED (dedup/idempotent/lag/fallback/status-transition + DB integration)
R2-06: PREPARED (workflow template full R3; run/verify = CI)
R2-07: PREPARED (flow matrix + exact manifests; live apply deferred)
R2-08: CLOSED source-level (11 handler contract + helper mock + DB integration + transport)
WORKFLOW_TEMPLATE_REVIEW_READY: YES (pending CI run/verify)
OWNER_HELPERS_REVIEW_READY: YES (mock tests 7/7)
NETPOL_PLAN_REVIEW_READY: YES (pending live apply gate)
HERMES_RESULT: PASS (source corrective package only; NOT runtime/FINAL ACCEPTED)
P8C: NOT_FINAL_ACCEPTED
P8D-P8G/P9: NOT_AUTHORIZED
