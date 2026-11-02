# P8C RV-02 — acceptance of c872eed and next offline reconciliation
Date: 2026-11-02 (Europe/Moscow).
Executor of next task: PRIMARY HERMES; Hermes2 excluded.

## Decision
Reviewed main: c872eed41a49e5923e91d260e4dcb3b12a1f903b.
Parent / consumed gate: 740a62026532505256a9754437da13fe4a5ed5c2.
Accepted runtime source: eed114e2201f75c3235b33779780038f1e8822df.
Evidence: evidence/P8/20261102T094000Z-p8c-rv02-podlist-onerun/.
Independent review: evidence/P8/20261102-p8c-rv02-c872eed-review/.

FOLLOWUP_LIVE_ARTIFACT=ACCEPTED_WITH_LIMITS / CONNECTOR_VERIFIED.
AUTHORIZED_READ_SET_COMPLETE=YES (9/9 successful records, 9 collector calls, EXIT=0).
CALICO_IDENTITY=OBSERVED_AND_ACCEPTED (three pods at collection time).
SOURCE_REWORK_REQUIRED=NO; COLLECTOR_RERUN_REQUIRED=NO.
FLOW_MATRIX_COMPLETE=NO; EFFECTIVE_POLICY_UNION=UNKNOWN.
NEW_GATE_RUN_BUDGET=CONSUMED.
PHASE2_NEW_RUN_APPROVED=NO; OWNER_PHASE2_HANDOFF_ALLOWED=NO.
NETPOL_APPROVED_FOR_APPLY=NO.
CI_RELEASE / WORKFLOW_PUBLICATION_DISPATCH / OWNER_HELPERS / PRODUCTION_MIGRATION_DEPLOYMENT=NOT_AUTHORIZED.
P8C=NOT_FINAL_ACCEPTED; P8D–P8G/P9=NOT_AUTHORIZED.

## Independent verification
Connector confirmed a single fast-forward commit from the gate: nine new evidence files and
an append to gaps.md; no application/collector/policy/source or historical evidence changes.
Locally checked exact Connector bytes, without cluster or SSH access:
- 8/8 SHA256SUMS.evidence entries and 5/5 SHA256SUMS.result entries match.
  Script hashes were checked against the accepted source fetched by Connector.
- followup.jsonl SHA256 = 6dd94032934cdb43e984b7cceec26edefb3e7e4b1c48b522118b1424e63b3676.
- Ordered nine record IDs, fixed argv/context/timeout, chronological timestamps and actual exits.
- Five list journals each contain one successful page; received/validated counts agree with outputs,
  complete=true and no continuation. Four other reads give nine calls total.
- Raw category=null with exit=0 means OK in this collector. Empty-list output is an empty string,
  as implemented in the accepted source, corroborated by received=validated=0; it is not missing evidence.
- Aggregate run metadata: 2026-11-02T09:35:24Z to 09:35:25Z, EXIT_CODE=0.
- 68 artifact consistency checks passed. These are evidence checks, not new platform tests.

## Accepted observations and their limits
| Record | Accepted fact at collection time | Limit |
|---|---|---|
| F-D1 | 23 Calico API resource descriptors | Includes a status subresource; not 23 distinct CRDs or proof of policy effects |
| F-I1 | Three kube-system calico-node Pods, exact v3.32.0 image and bound bare config digest | Confirms accepted identity, not per-node dataplane configuration |
| F-CS | compatible=true, spec hash ff433d3463dfa2264a7a3ff6201baabf1ec789e98664aff3401a7ef79ae7ce5e | Schema compatibility only |
| F-CNP/F-NP/F-GNP/F-HEP | Complete empty lists for the exact recorded GVRs | Calico NP is not networking.k8s.io NetworkPolicy; older base inventory is a different timestamp |
| F-FELIX | default nftablesMode=Auto; other projected mode fields null | No proof of effective nftables/eBPF/iptables mode or absence of overrides |
| F-TIER | default:1000000/Deny, kube-admin:1000/Pass, kube-baseline:10000000/Pass | Configuration order/defaultAction observed; endpoint applicability and traffic outcome not established |

The corrected bundle now succeeds live. Do not retroactively claim that omitted TypeMeta was
the exact historical failing field: that raw field was never retained. MI-01 is an accepted
offline-proven defect correction consistent with the successful run; historical LIVE_FAILING_FIELD
remains UNKNOWN. Current F-I1 is resolved.

Preflight contains seven per-check UTC/exit records and reported outputs. The version check is
summarized, not the complete version JSON / exact argv; host-key and key-only authentication are
operator-attested in result.md, not independently replayed. Local hash-check is a formatted
record; remote hash-check retains actual sha256sum output. These limits do not require another
run or invalidate the internally consistent returned artifact. Do not manufacture missing logs.
The limited credential-pattern scan found no matching credential content; this is not a universal
proof of absence. Run once is accepted as operator-attested and consistent with returned records;
the artifact alone cannot prove absence of any unreported activity.

## Status correction (no historical evidence edits)
Hermes used FLOW_MATRIX_COMPLETE=YES to mean nine reads succeeded. These are distinct conditions.
Use AUTHORIZED_READ_SET_COMPLETE=YES and FLOW_MATRIX_COMPLETE=NO until the fourteen-flow design
and its material uncertainties are resolved. The current flow matrix still has unresolved
API DNAT, Barman/S3 direction/routing and planned ingress entries. This review supersedes the
status wording in historical result.md; that file and its checksums remain byte-identical.

## Next task: P8C-RV02-OFFLINE-ROLLOUT-DECISION
Authorized now: bounded offline design/reconciliation only, using existing repository evidence
and pinned official source already present. No new live queries or collector development.

1. Recover actual main through Connector and read this decision, flow-matrix.md, gaps.md,
   PLAN.md and accepted source contracts. Preserve all accepted source and evidence.
2. Produce one decision package covering all 14 FLOW-IDs. For each: source/destination selectors,
   namespace, direction/protocol/port, existing evidence with record/time, planned versus existing
   workload, candidate rule reference, and whether an UNKNOWN actually blocks safe rollout.
   Separate existing CNPG/Barman preservation from new Portal/migrator/Envoy flows.
3. Resolve documentary questions from version-pinned repository sources where possible.
   Do not demand proof of every dataplane detail merely because it is UNKNOWN: explain its
   concrete effect on proposed selectors, ports, API DNAT, S3 allowlist or isolation.
   Where indispensable live information remains, propose the smallest exact read set with
   fields/projection/source-version/scope/limits/error handling and affected FLOW-ID. Proposal only;
   do not build another general-purpose collector or execute reads. Explain why existing evidence
   cannot answer it. Do not infer observed traffic from declared ports.
4. Prepare a reviewable rollout plan and checklist of prerequisites: supply-chain/auth readiness,
   complete existing-flow allowances before any CNPG isolation, order of policy/workload creation,
   health checks, rollback by newly-created object identity and explicit STOP conditions.
   Do not modify policy YAML or grant apply. List stale facts needing a later rollout precheck
   without rerunning accepted backup/restore/PITR/failover tests.
5. Publish only new decision/evidence and necessary current documentation, fast-forward with
   fresh-head check, no force, no historical evidence edits; exact readback. Report requirement
   to fact/source to decision to remaining gate. Stop after the complete offline package or a
   concrete external blocker once independent work is finished. No intermediate request to continue.

Output: one finite offline decision package, not another collector correction cycle.
Source suites, PG17/platform tests, registry queries, SSH, Kubernetes calls, source rework,
CI/workflow/token, provisioning helpers, NetworkPolicy mutation and production actions are excluded.
