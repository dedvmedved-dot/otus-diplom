# Architect review dfb9130 — bounded residual and design decisions

Date: 2026-11-03. Repository: dedvmedved-dot/otus-diplom.
Reviewed main/source: dfb9130a4c1b2ba9278d1feda234cd7e444f6611.
Parent: 6bc54d19d9189e9fba9ba6b837c2012ffbfcc92d.
Executor of the next source-only task: PRIMARY HERMES. Hermes2 is not involved.

## Decision

SOURCE_PACKAGE=PARTIAL / REWORK_REQUIRED. Not a runtime rejection and not permission to execute.
The nine-file diff is within the preparation scope. Candidate YAML, application, collector, RBAC,
deployment and Gateway source were not changed. Accepted inventory 9/9, identity/S1, offline design,
NP-01..04 candidate semantics and the pg_stat_archiver metric-source choice remain CLOSED.

Accepted in this package: API negative tuple coverage for both clients, DNS TCP/UDP negatives,
stage CNPG preservation cases; release expanded URLs and explicit UNVERIFIED status;
migration ledger query and distinction between readiness and TLS evidence.
Author transcript contains 3 top-level PASS and 91 subtest PASS, exit 0.
Architect verified the transcript and source through Connector, not by executing Go.
Go is unavailable in the review environment; Python 3.12.14 static evidence audit executed successfully.
Do not present this as an independent Go run or runtime network-policy validation.

## F1 — structural guard remains incomplete (code)

Source: portal/networkpolicy/flows_test.go, blob 41b91c8be4a6bdbab807f823ee816385f9d1eb64.

validateStructure checks ingress only for an empty From list. It does not inspect ingress ports or
individual ingress peers. Egress allowedIP checks apply only to IPBlock peers; selector-based
egress can carry unexpected port/protocol. Target PodSelector is not validated. Removing one of
the required labels is not covered by the empty-namespace-selector condition.

Concrete static counterexamples to the claimed guard (not independently executed Go reproductions):
- append ingress From:[{}], Ports:[TCP/9999];
- remove Ports from an existing ingress rule;
- add endPort or a named port to an ingress rule;
- append SCTP/9999 to an existing selector-based egress rule;
- widen a non-baseline target PodSelector to {};
- remove a required matchLabel from a DNS/dataplane peer selector.

The DNS mutation currently removes PodSelector from EVERY namespace-scoped egress peer,
not only DNS. This is not the isolated mutation claimed in the report.

Required correction:
1. Validate the finite accepted semantics per policy/direction: target selectors, exact type set,
   peers (namespace AND pod selectors), ports/protocol and per-policy IP tuples. Do not derive the
   expected allowlist from the same mutated YAML. Retain legal empty baseline target selectors.
2. Add named negative fixtures for the six cases above, plus empty ingress peer and nil ingress port.
   Existing six negative cases and functional flow assertions stay.
3. Limit the DNS mutation to the known DNS rule/peer; prove unrelated peers/ports are unchanged.
4. Run only the addressed networkpolicy suite, fresh -count=1, record tested source SHA and exit.
No candidate YAML changes or new policy semantics are authorized.

## F2 — deployment draft contradicts accepted source (documents only)

Draft blob e02ebc58a326cc9bef6e3a5cc477e34514290dab.
RBAC source blob 036e90b40a44701c04b145af4c987ae962648477.

"Any namespace outside portal+velero denied" is false: portal-platform-reader ClusterRoleBinding
grants its namespaced resource reads cluster-wide. The blanket resourceNames-denied claim is
also false for unrestricted get/list resources. Named Cluster/ObjectStore/Gateway/HTTPRoute/
ScheduledBackup permissions are GET only, not LIST.
Correct the expected matrix to the actual accepted manifest; do NOT tighten or broaden RBAC here.

Replace the ambiguous <=20-review statement with <=20 explicit representative SAR case rows:
subject, group/resource/subresource, verb, namespace, name, expected, timeout, artifact.
Identify this as representative runtime checking; full source rule comparison is separate.
Authorization-review POSTs are a future explicitly bounded operator activity, not permission
for the Portal to create reviews or for actual destructive mutation tests.

Object inventory omits UI PKI:
gateway.yaml blob 1e1f48a3c6d03c4558f4b4c3cca24bc12c22b763 defines
Issuer portal-ui-bootstrap, Certificate portal-ui-root, Issuer portal-ui-ca,
Certificate portal-ui-server (all portal); generated Secrets portal-ui-ca / portal-ui-tls.
Separate these from existing DB CA Secret portal-db-ca.
Also enumerate portal-ui-auth and portal-registry-pull prerequisites; they are Owner-provisioned,
not CNPG-provisioned or proven existing. Enumerate all six NetworkPolicy names.
Use real path+blob references, not filenames under a "Source blob" header.
Separate source-defined NEW, generated PLANNED, and existing-but-requiring-freshness-check resources.
Do not invent a fixed total while rows group multiple resources.

Restore the lost DEP-01 prerequisites, S0/S1/S2a/S2b/S3/S4 order and UID/no-overwrite rollback,
from c86f39fe6f5eb6edf17b010fdf3a32e16f669469 and the accepted offline design.
Preserve: policies before workloads; migration before app; one verified digest; Gateway last;
exposure risk starts at Gateway creation; generated cleanup before removing dataplane egress;
default-deny/allow-dns removed before existing-flows; no destructive down migration.
Keep the new inventory/proof detail; restoration is additive, not replacement.
Correct "Gateway 120s×12": W=120s, I=10s, N<=12 within one hard window, not twelve 120-second windows.
Existing 11 API, TLS/readiness separation and TTL/cap source facts need no reimplementation.

## D1 / F3 — Architect selects metrics access; repair the remaining budget

DESIGN_CHOICE=OPERATOR_PRIMARY_BOUND_DIRECT_EXPORTER (source-only).
Actor is the authorized operator on node-01, not the Portal application.
Future binding: named portal/portal-db Cluster currentPrimary -> named Pod in portal ->
validate cluster identity/UID/current Pod IP -> fixed HTTP port 9187 and /metrics.
Bracket samples with named Cluster/Pod metadata checks; role, UID, IP, restart/reset change invalidates comparison.
No arbitrary endpoint, redirects, exec, port-forward, SQL, new Service, new collector or Secret read.
HTTP is the source-backed exporter transport; do not imply TLS or weaken the application DB TLS contract.
A connectivity failure is INCONCLUSIVE/STOP, not permission to try alternate access paths.
The Portal DB contract remains canonical Service:5432 + verify-full. It does not prohibit this distinct
operator-only diagnostic Pod-IP:9187 proposal. No application Pod-IP discovery is authorized.

This chooses the mechanism, not its live authorization. Replace ACCESS_METHOD=UNRESOLVED with
DESIGN_SELECTED / EXECUTION_NOT_AUTHORIZED and define the exact projected metadata fields and bounds.

Current draft blob 215c305096340bd3124039065803bd84119b64ab is not fully bounded:
2–3 metrics bodies per each of several stages is incompatible with a global 5 MiB budget;
W=5s is a request timeout, not the promised hard observation deadline;
"retry within W" and "stage duration" do not define a finite overall budget.
Replace with one consistent table:
- stage set and separate baseline/post sample count, per-request and per-window hard deadline;
- numeric sample schedule, no uncounted retries, finite metadata GET count and metrics GET count;
- max body for each response type and arithmetic global byte/request/wall-time totals;
- metadata/time uncertainty and timeout => INCONCLUSIVE/STOP;
- successful archive timestamp must evidence a fresh post-step archive, not merely exceed an old value;
  GET-time is not archive-time; define clock/freshness tolerance and action boundary explicitly.
- retain failed-count/time precedence, reset/role/restart/idle handling and prohibition of artificial WAL.
Do not assert pg_stat_archiver meaningful ONLY on primary: the pinned query also admits archive_mode=always.
Primary-only sampling is the chosen comparison policy, not that universal technical claim.
CNPG ARCH-STATE remains distinct from fresh WAL progress and independent S3 readback.

Keep all bounded PR/HC proposals NOT_AUTHORIZED. No execution wrapper implementation is required by this task.

## D2 / F4 — Architect selects bootstrap design; preserve release traceability

DESIGN_CHOICE=SEPARATE_GITHUB_ACTIONS_PRIVATE_SEED_GATE.
Future primary release keeps private-before. If the exact private package with correct repository
association and access already exists and is evidenced, no seed is needed.
Otherwise design a separate one-shot Owner-authorized bootstrap workflow using its automatically
issued GITHUB_TOKEN, exact repository/package identity and an explicitly identified seed artifact/tag.
The seed is not the Portal release, not an accepted image and not deployable. Record its digest/source,
private visibility and repository association after creation; require private-before again for main release.
Do not equate 404 with proven absence (permissions can hide existence); ambiguous identity/access => STOP.
No broad PAT request or workflow-token use, no public-package workaround.
GitHub documents default initial private visibility and workflow repository association:
https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry
https://docs.github.com/en/packages/learn-github-packages/configuring-a-packages-access-control-and-visibility

This selects the design branch; publication/settings/seed/push/dispatch remain separately gated.
Current task: describe source/identity/artifact/visibility checks and Owner inputs in the DRAFT only.
Do not write/publish/bootstrap a workflow or claim package existence, permissions or pins verified.

Restore the requirement -> step/helper -> offline proof -> CI-only proof table present in
c86f39fe6f5eb6edf17b010fdf3a32e16f669469 §3. It was removed in this revision.
Retain the new literal URLs, identity, artifacts, 20m/30m job budgets and source-change invalidation.
Label source assertions vs CI_NOT_EXECUTED and limits not yet implemented in unchanged template.
For the future gate proposal, specify numeric launch expiry as well as job timeout; it is not issued now.
UNRESOLVED bootstrap/access were permitted questions in the previous task, not misconduct;
this decision resolves their design choice without granting execution.

## E — scan evidence is ERROR, not clean

Author evidence root: evidence/P8/20261103T033000Z-p8c-candidate-and-gates-r2-residual/.
secret-scan.txt blob f362d34c268121c393b277bd854cf25f434cb20c contains:
- "input file is also the output";
- a match against the scan description in source-manifest.json;
- grep_exit=2.
The manifest's exit=1/hits=0 and final clean claim are not supported.
This review establishes a scanner execution/reporting error, not discovery of an actual leaked credential.

Do not rewrite that historical evidence. New evidence must explicitly supersede the clean claim.
Run a bounded scan of an enumerated, frozen input set; write scan output outside that input set.
Record actual scanner/version/complete command/scope/UTC/exit, distinguish ERROR from matches/no matches,
and classify documentary matches without exposing values. Do not use ellipses/<files> in the executed command.
Freeze evidence input files before scanning and record their hashes; exclude the output report explicitly.
Heuristic no-match remains limited evidence, not a proof of universal absence.

## Executable source-only task / completion

TASK=P8C-R1-CANDIDATE-AND-GATES-R3-CORRECTION.
Primary Hermes continues autonomously through F1..F4 and E; no intermediate "continue" required.
Allowed edits: portal/networkpolicy/flows_test.go; the same three gate DRAFT documents;
active task reference in PLAN.md; new evidence only.
No changes to accepted candidate YAML, app, collector, RBAC, deployment/Gateway, release template/helpers,
or historical evidence. No new inventory, PG17, backup/restore/PITR/failover repetitions.

G0: fetch main, verify this review is present and changes since reviewed SHA; clean worktree.
Unexpected unrelated/source-scope change => STOP/report, no memory-based history repair.
G1: finite corrections above; preserve completed work and accepted sections.
G2: addressed Go tests; document source cross-checks; fresh scan with correct error handling.
G3: source commit first, then new evidence commit binding full tested source SHA, paths/blobs/SHA256,
commands/versions/UTC/exit, requirement->code/doc->test/check->evidence matrix.
Final fast-forward only, no force or historical rewrite; verify remote main and clean/ahead/behind.
STOP for independent review after complete package or concrete external blocker after independent work.

Architect review evidence: evidence/P8/20261103-dfb9130-architect-review/.
It contains reproducible static source checks and exact Connector bytes, not a Go execution.

PHASE2_NEW_RUN_APPROVED=NO
NETPOL_APPROVED_FOR_APPLY=NO
CI_RELEASE / WORKFLOW_PUBLICATION / WORKFLOW_DISPATCH = NOT_AUTHORIZED
OWNER_HELPERS=NOT_EXECUTED
PRODUCTION_MIGRATION_DEPLOYMENT=NOT_AUTHORIZED
P8C=NOT_FINAL_ACCEPTED
P8D–P8G/P9=NOT_AUTHORIZED
