# P8C-RV02 — acceptance of live-compatibility source fdfc776

Date: 2026-11-02 (Europe/Moscow). Architect / independent offline review.
Repository: dedvmedved-dot/otus-diplom. GitHub main is sole Source of Truth.

## Decision

ACCEPTED_SOURCE_SHA=fdfc776570c7f44e559eefcd092e2ca58595ee48
ACTUAL_PARENT_SHA=c1644950c618f7ca7221a9500dc3049363d7bfee
FOLLOWUP_SOURCE_COMPATIBILITY=ACCEPTED / CONNECTOR_AND_OFFLINE_VERIFIED
LC-01=CLOSED
LC-02=CLOSED
LC-03=CLOSED (documentary reconciliation below)
SOURCE_REWORK_REQUIRED=NO
PREVIOUS_ONE_RUN_BUDGET=CONSUMED
PHASE2_NEW_RUN_APPROVED=NO
OWNER_PHASE2_HANDOFF_ALLOWED=NO
NETPOL_APPROVED_FOR_APPLY=NO
CI_RELEASE / OWNER_HELPERS / PRODUCTION_MIGRATION_DEPLOYMENT=NOT_AUTHORIZED
P8C=NOT_FINAL_ACCEPTED
P8D–P8G/P9=NOT_AUTHORIZED

This closes the bounded source-compatibility corrective task. It does not close live network
inventory or authorize SSH, transfer, rerun, policy apply, release, production migration/deploy.
No further source rework is requested for LR-01/02 or LC-01/02/03.
Primary Hermes is the executor for any future separately published gate; Hermes2 is excluded.

## Connector recovery and exact scope

Connector confirms fdfc776 is main, directly descended from c164495 (ahead1/behind0).
Eight changed paths: followup.py, followup_test.py, current read-design/coverage documents and
four NEW evidence files. No historical evidence, supplemental.py/S1, typed contract, application
runtime source, policy manifests or fixtures were modified in this submitted diff.

The operator report incorrectly labels f20f57f as parent and65d4676 as ACTUAL_PARENT.
These are older checkpoints. Correct chain:
65d4676 -> f20f57f -> c164495 -> fdfc776.
This document supplies the correction; original evidence remains unchanged. It does not require
another engineer cycle. Current coverage references and extraction wording are clarified by
Architect in this acceptance commit; executable bytes are unchanged.

## Runtime package pinned for a future gate — NOT_AUTHORIZED_FOR_RUN

Extract both files only from ACCEPTED_SOURCE_SHA above. Only two runtime files are required;
test fixtures, YAML, typed-contract and PyYAML are not runtime dependencies.

| Path under portal/networkpolicy/ | Git blob | SHA256 |
|---|---|---|
| followup.py | 6dbfad124a486b0f2d6eccb791777608918fac35 | fc78d03af06f60bbcdde967810ee65a28f37df96a0d85a003807f097fa179e2b |
| supplemental.py | 1b613fbd1e35a109072d2843d6e5f3a3fd47b3d6 | ddd9a4dc17bca97d6b36ae6b4d501e1722c5d38d6e5ac8c7b051698fa0b15491 |

Additional verified source:
followup_test.py blob84630d557f5cb527c623f28f71dcec9ee5a33ed1,
SHA256c912db861c7dd5b0b8c8b89f4f905e61251585fa258c36d872c9ad7a4d23325c.
followup-typed-contract.json blobcd92740a4b857c6b8c9226eba579e5d9525494d0,
SHA25695d76352cb4235820af2684660379ff0436b624e5ebe4d55401f2a3343b3fd6b.

Old gate fbaa9a4 pinned different followup.py bytes and is consumed. Do not reuse its permission,
its script hashes or its literal old F-I1 command for this new package.

## Independent validation

Python3.12.14 / PyYAML6.0.3; all cluster subprocesses mocked; no live/SSH/registry calls.
Full raw outputs are NEW evidence, with actual UTC/argv/cwd/exit in execution.json.

| Check | Actual result | Evidence |
|---|---|---|
| Author followup suite independently rerun | 122 tests, exit0 | followup_test.txt; execution.json[0] |
| Unchanged supplemental regression suite | 36 tests, exit0 | supplemental_test.txt; execution.json[1] |
| Previously supplied independent regression | 4 methods PASS, all7 prior failure cases now pass, exit0 | compatibility_regression_test.txt; execution.json[2] |
| Additional presence/CIDR boundary observations | 28/28 PASS, exit0 | verify.py; verification.json |
| Exact source hashes | MATCH | verification.json.hashes |
| CNP manifest binding | normalized subtree equality and hash match | verification.json.manifest_schema_match |
| Historical candidate | actual old subtree recomputed770130a4... != currentff433d34... | verification.json.old_candidate_hash |

Suite run window:2026-11-02T01:45:28.719468Z–01:45:30.347393Z.
Additional check timestamps are in verification.json.
ResourceWarning in legacy test harnesses is nonblocking; no assertion failures.
No full Portal/PG17/backup/restore/failover suite was repeated.

### LC-01

Explicit presence check distinguishes absent/empty string from null and invalid types.
Independent main-path matrix: absent and empty permit all5 consumers; null,false,true,0,3,[],
{},nonempty token -> PARSE_ERROR/COMPLETENESS, complete=false, empty output, zero consumers.
Synthetic token canary is absent from all emitted records. No identity contract relaxation.

### LC-02

Strict address/prefix syntax matches the reviewed finite Kubernetes CEL contract:
one slash, numeric ASCII prefix without signs/leading zeros, valid IPv4/IPv6, no zone,
no IPv4-mapped IPv6, prefix bounds0..32/128, schema length<=43.
All six previously false-accepted fixtures are now rejected through F-CNP with empty output.
Positive IPv4/IPv6 host bits remain unchanged in projection, as do /0 and maximal prefixes.
A 43-character valid full IPv6 /128 is accepted; the 49-character valid-address spelling is
rejected by maxLength. Additional signed, out-of-range, Unicode-prefix and IPv4-leading-zero
negatives pass. Existing bounded list/page/journal tests pass.

### LC-03

Current CNP authority is the repository Calico v3.32.0 manifest:
source commitdd00e2f36fdae9cb91baab256ecf9ecf2f662249,
blob21ea9b4b163305ea479bc7708965104465ffc716.
Exact normalized spec hash:
ff433d3463dfa2264a7a3ff6201baabf1ec789e98664aff3401a7ef79ae7ce5e.
Historical network-policy-api770130a4... is not dual-accepted.
Independent verification uses actual manifest bytes and old candidate subtree, not a
self-referential hash constant. The manifest test uses PyYAML in tests only.
The new CNP stored fixture includes description annotations; normalization removes them only
at schema-node positions. No blanket recursive semantic-key deletion is introduced.

## Next stage and retained limits

Next required Architect action is a NEW one-run live gate bound to these two exact files.
Such a gate must explicitly carry forward the trusted node-01 ED25519/key-only access,
the fixed context and no-password/no-other-node constraints. It must pin the NEW F-I1 raw path,
retain one identity request(limit200/no continuation), five paginated policy lists(cap500,
max3 pages200/200/100), request/subprocess timeouts15s/20s and maximum19 collector invocations.
This is preparation information, not a run allowance.

After authorized collection, reconcile actual objects against the14FLOW-ID matrix; distinguish
configuration from effective traffic/policy enforcement. Source acceptance does not establish
per-node CNI mode, effective policy union or Barman traffic direction.
No additional source cleanup or accepted-test repetition is needed before gate preparation
unless new contradictory evidence or source changes appear.
