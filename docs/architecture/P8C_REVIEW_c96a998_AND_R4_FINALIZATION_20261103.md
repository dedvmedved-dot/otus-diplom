# Architect review c96a998 — acceptance boundaries and final finite source correction

Date: 2026-11-03.
Reviewed main: c96a9988ef68be5ecfd7e8e65f39e40b14193ba9.
Parent: fd2ed87eabe9214464ab8c14baf04ab41fe7944a.
PRIMARY HERMES only. Hermes2 is not involved.

## 1. Verified result

Connector verified main, parent and the eleven-file diff. Candidate YAML/app/collector/RBAC/
deployment/Gateway and old evidence are unchanged. All twelve retrieved Git blobs verified locally.
The four source SHA-256 values match both the manifest and the frozen scan-input list.

E=CLOSED_WITH_STATED_SCOPE: independently reran the supplied grep heuristic over precisely those
four files, grep 3.11, exit 1, empty stdout/stderr. This supersedes the earlier execution ERROR;
it is not a scan of all evidence or proof against every possible secret form.

Author Go transcript: 3 functions / 97 subtests PASS. Architect verified transcript counts,
not a second Go execution (Go unavailable; Python 3.12.14 evidence checks executed, exit 0).
No live/SSH/registry/CI/production activity was performed.

F2=SUBSTANTIVELY_CLOSED: cluster-wide read scope, GET-only named permissions, representative SAR
rows, missing PKI/secret ownership, rollout/rollback and Gateway hard-window correction restored.
F4=DESIGN_AND_TRACEABILITY_CLOSED: bootstrap choice and source/CI proof mapping restored.
The small exact-text corrections in §4 below are part of this review decision, not new design work.

F1=PARTIAL; F3=PARTIAL. Overall SOURCE_PACKAGE=PARTIAL, not FINAL ACCEPTED.
Candidate NP-01..04 semantics, 9/9 inventory, offline design, identity/S1, app and prior DB/backup
tests remain CLOSED and are not to be rerun or redesigned.

## 2. F1: exact accepted contract, not global allowed-port sets

Source: portal/networkpolicy/flows_test.go, blob 521e28acb585fbd78f70ee975bec126781bb6082.

The new ingress checks validate empty/nil/named/endPort forms but do not bind numeric ports and
protocols to an accepted peer/rule. allowedSelectorPorts is global: adding TCP5432 to the DNS peer
passes that set. allowedIP is also global: an API rule can be added to migrator or default-deny.
Empty selector objects differ from a completely empty peer and are not rejected here.
Removing all ingress rules is not detected. These are omissions from the already requested exact
per-policy/per-direction contract, not new requirements on the production YAML.

Reviewer supplies:
- exact_rule_regression_test.go: ten addressed cases; first eight are statically identified gaps,
  last two retain nil/named-port controls. SOURCE_SUPPLIED / NOT_EXECUTED by Architect.
- accepted-policy-contract.json: six frozen source-approved objects (identity + exact spec),
  bound to unchanged YAML blob 15f0b3245586bf5086e5a24ed02b0460121f7712.

Use this finite contract as the expected test fixture. It is extracted once from the immutable,
previously accepted candidate and reviewed here, not generated from the candidate during testing.
Copy it unchanged into portal/networkpolicy/testdata/accepted-policy-contract.json.
Compare all six identities and complete specs against it; reject missing/extra objects, rules,
selectors, expressions, peers, ports, protocols and policy types. JSON/map key order is irrelevant.
For this frozen candidate, preserving array order in comparison is acceptable; normalization must
not discard any field. Decode expected and candidate into the same typed representation so that
absent/default TCP and nil/empty representations are handled consistently and explicitly.
Do not auto-regenerate the expected fixture when candidate changes.

Keep the behavioral both-sides tests: fixture equality is an additional change guard, not a substitute.
Integrate and execute the ten supplied regression cases plus the existing suite.
The DNS mutation is now scoped correctly. Existing positive xDS/CNPG checks establish reachability,
not byte equality: compare non-DNS peers/ports before/after mutation to substantiate "unchanged".
Do not change candidate YAML. This fixed expected contract closes the scope; no generalized policy
validator or exhaustive Kubernetes schema implementation is requested.

## 3. F3: normative observation budget chosen by Architect (DRAFT ONLY)

Draft blob 9216ebe41b65a1e5e73d841432f2a1646e37982a says each sample is bracketed with metadata reads,
but budgets only Cluster+Pod BEFORE metrics and ends at the metric response. Bracketing requires
Cluster+Pod AFTER as well. One sample/stage also leaves baseline/post-step freshness ambiguous.
"last_archived_time in (baseline, now]" does not define the operation-completion boundary.
The 180-second claim excludes rollout actions yet reads as total elapsed rollout time.

Replace that table with the following fixed proposal; do not invent new access paths or execute it.

Actor/access remains OPERATOR_PRIMARY_BOUND_DIRECT_EXPORTER on the accepted node-01 key-only path.
For each sample:
1. named portal/portal-db Cluster GET -> currentPrimary, Cluster UID;
2. named currentPrimary Pod GET in portal -> Pod UID/IP, owner binding to that Cluster,
   container name/restartCount/running.startedAt;
3. HTTP GET fixed Pod IP:9187/metrics, no redirects;
4. GET the SAME named Pod and compare identity/IP/container restart/start fields;
5. GET the SAME Cluster and compare UID/currentPrimary.
No fallback to another Pod, dynamic retry, exec, port-forward, SQL or Secret reads.
Do not infer primary from cnpg.io/podRole=instance (it does not distinguish primary).
Validate raw response size BEFORE persisting any projected data; raw objects never enter evidence.
Metadata projection is limited to the fields above plus object name/namespace and required cluster labels.
Counters, timestamps and reset markers come from the accepted pg_stat_archiver series.

| Bound | Normative DRAFT value |
|---|---|
| Observation windows | S0, S1, S2a, S2b, S3, S4: at most 6 |
| Sample slots in each window | start at offsets 0, 300, 600 seconds; at most 3 |
| Per sample | 4 metadata GET + 1 metrics GET = 5 requests |
| Per request | timeout <=5s and remaining deadline; one attempt, no retry |
| Per sample deadline | <=30s; serialized requests fit within 25s nominal maximum |
| Per window hard deadline | 660s from first slot, monotonic clock |
| Metadata body cap | 256 KiB each, before projection |
| Metric body cap | 1 MiB |
| Per sample body cap | 2 MiB total |
| Per window cap | 15 requests / 6 MiB |
| All six windows cap | 90 requests / 36 MiB / 3960s observation time |
| Total rollout elapsed | observation cap PLUS separately bounded action time; not claimed to be 3960s |
| Abort conditions | timeout, malformed/nonfinite, missing series, role/UID/IP/restart/reset change => INCONCLUSIVE/STOP |
| Retry distinction | later planned slots only for valid but idle samples; transport/parse failure does not retry |

S0 first valid sample establishes baseline; a later valid slot must demonstrate fresh natural progress.
No next operation begins until the current observation window passes. For each post-operation window,
retain the last accepted pre-operation sample (same Cluster/Pod identity) and record operation-end UTC.
Compare failed_count/last_failed_time/reset markers against that retained baseline: failure growth
wins over any archive growth. Then require archived_count growth AND a fresh last_archived_time.
Idle is permitted only until the remaining planned slots are exhausted, then INCONCLUSIVE/STOP.
Never force WAL switch, writes, backup or other artificial traffic.

Clock design: the future gate must evidence an absolute exporter/observer UTC skew bound <=5s.
If unknown, the freshness verdict is INCONCLUSIVE; do not silently assume synchronized clocks.
For post-operation PASS: last_archived_time > operation_end_UTC + 5s and <= sample_end_UTC + 5s.
For S0, use first-sample-end UTC instead of operation-end UTC.
This deliberately conservative rule handles second-resolution timestamps and clock uncertainty.
It may end INCONCLUSIVE on an idle system; no promised success or repeated-run entitlement.
Clock evidence collection itself is not authorized here; list it as an explicit future gate prerequisite.

Bracketing detects observed changes, not absolute absence of a transient role change between reads.
Do not claim this is an atomic platform snapshot, full S3 readback or independent DNS proof.
Primary-only is the chosen comparison policy; archive_mode=always note stays.
ContinuousArchiving remains ARCH-STATE, separate from fresh WAL progress.

No execution wrapper code is requested in this task. Only synchronize the DRAFT and document arithmetic.

## 4. Closed design: exact editorial corrections, no new investigation

Deployment:
- restrict "other resourceNames denied" explicitly to the named-GET Role resources; generic
  ClusterRole get/list reads have no name restriction. State named Role scopes portal and velero.
- use full SAR subject system:serviceaccount:portal:portal-reader; the eight rows are representative,
  not exhaustive permission proof. No actual mutations for denied-verb checks.
- restore the literal ledger query:
  SELECT version, checksum FROM portal.schema_migrations ORDER BY version DESC LIMIT 1;
  The new ellipsis is not executable.
- retain all restored object ownership, stage ordering and rollback. No source/RBAC/PKI changes.

Release:
- numeric launch expiry proposal = 24 hours from a FUTURE gate's explicit issued_at UTC;
  invalidate earlier on pinned source/bytes change or consumed run. No gate is issued by this document.
- retain one manual run, no retry, test 20m/release 30m, NOT_IMPLEMENTED_IN_TEMPLATE status.
- private-seed mechanism remains DESIGN_SELECTED, package existence/access/pins not verified here.
No workflow/template/helper/settings/registry changes or new upstream downloads are authorized.

## 5. One finite task for PRIMARY HERMES

TASK=P8C-R1-CANDIDATE-AND-GATES-R4-FINALIZATION.
Allowed source edits: flows_test.go, supplied regression integration and frozen testdata fixture;
the same three gate drafts; active PLAN reference; new evidence.
Do not modify production YAML/app/collector/release code or historical evidence.

G0: recover remote main and this review through source; inspect any later diff before continuing.
Unexpected unrelated/source-scope changes => STOP/report, no history repair.
G1: complete §2–4, preserve accepted work. Do not stop for another "continue" between these items.
G2: fresh addressed Go networkpolicy suite; compare frozen fixture hash and source manifests;
scan the changed files and new frozen evidence input set with output outside it.
Record matches as findings to classify, errors as errors, and never expose credential values.
Do not re-open the accepted four-file scan of c96a998.
G3: source commit first; test/evidence bound to that full source SHA; new evidence commit after.
If the current history combined source/evidence, preserve it; no amend/reset/force to repair old commits.
Include requirement->code/doc->test/check->evidence matrix and real commands/versions/UTC/exits.
Publish fast-forward, verify main readback and clean/ahead/behind; final STOP for independent review.

Acceptance of the source preparation remains distinct from wrapper/template qualification and future
Owner/CI/runtime gates. No claim that this review alone makes deployment executable.

Evidence: evidence/P8/20261103-c96a998-architect-review/.
PHASE2_NEW_RUN_APPROVED=NO
NETPOL_APPROVED_FOR_APPLY=NO
CI_RELEASE / WORKFLOW_PUBLICATION / WORKFLOW_DISPATCH = NOT_AUTHORIZED
OWNER_HELPERS=NOT_EXECUTED
PRODUCTION_MIGRATION_DEPLOYMENT=NOT_AUTHORIZED
P8C=NOT_FINAL_ACCEPTED
P8D–P8G/P9=NOT_AUTHORIZED
