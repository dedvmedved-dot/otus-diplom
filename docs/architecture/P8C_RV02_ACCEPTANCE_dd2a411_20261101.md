# P8C-R1 RV-02 — acceptance of follow-up source dd2a411

Дата: 2026-11-01 (Europe/Moscow). Independent Architect / GitHub Connector review.
Executor for any later task: primary Hermes; Hermes2 excluded.

## Decision

```text
RECOVERY_MAIN_SHA=dd2a4115e6d4c7799a4acf5156a42ab0590ceea8
REVIEWED_SOURCE_SHA=05d61ac74e88256adee455dcefd2d9c33335b6b3
FOLLOWUP_SOURCE=ACCEPTED / CONNECTOR_VERIFIED / OFFLINE_VERIFIED
B1= CLOSED / INDEPENDENTLY_VERIFIED
B2= CLOSED / INDEPENDENTLY_VERIFIED
R1/R2/R3/R4= CLOSED (follow-up source scope)
AUTHOR_SUITE_REPLAY=99/99 PASS
SUPPLEMENTAL_REGRESSION=36/36 PASS
PREVIOUS_REVIEWER_REGRESSION=7/7 PASS
BOUNDED_PROJECTION_REGRESSION=4/4 methods PASS (all five list kinds)
INDEPENDENT_MATRIX=151/151 matched; 0 failures
PHASE2_NEW_RUN_APPROVED=NO
OWNER_PHASE2_HANDOFF_ALLOWED=NO
ONE_RUN_BUDGET=CONSUMED
NETPOL_APPROVED_FOR_APPLY=NO
FLOW_MATRIX_COMPLETE=NO
ACCESS_COMPLIANCE=NOT_FULLY_EVIDENCED
P8C=NOT_FINAL_ACCEPTED
P8D–P8G/P9=NOT_AUTHORIZED
```

This accepts the current follow-up collector SOURCE package, not live inventory closure,
effective policy coverage, platform readiness, or P8C final acceptance.
No remaining corrective source task is issued for this reviewed block.

## Source-of-truth audit

Connector main equals dd2a411. Compare3be8d67..dd2a411: ahead2/behind0, expected
source05d61ac -> evidence dd2a411. Exactly six changed paths: followup.py,
followup_test.py and four NEW author evidence files.
Source05d61ac parent=3be8d6746b0e4aad3880128230e453da628b4934.
Evidence commit parent=05d61ac; source..evidence changes only those four evidence files.
Reviewed main tree=4ec8ef0124b885169f89195ce0be6eb7679a12de.
No unexpected history/source changes; historical evidence unchanged.

Exact bytes read through Connector and executed offline:
- followup.py: blob8f2d7f6d0d3d033810046d93b33448f465ab57f6;
  SHA256 f48cfc825f25a002cac6afcc63da9f7d5800a3a92b5bc231eeb456b7d6328b98.
- followup_test.py: blob85ba87f1841a90a17b54e9bf0c5e758ed73ec633;
  SHA256 e0d7172b6ba3b731d4371c7289f4f14a84cc47a0a8687c42436fc07b6081ede1.
- supplemental.py unchanged: blob1b613fbd1e35a109072d2843d6e5f3a3fd47b3d6;
  SHA256 ddd9a4dc17bca97d6b36ae6b4d501e1722c5d38d6e5ac8c7b051698fa0b15491.
- base inventory.py unchanged: blob5f0e2450358bfd9b08b542f013be5a914b9195a4;
  SHA256 7806f494bcee93f31eb2cb0348d2cd8f7cbbf5743261336226a251643d8988a2.
- derived-i1-fixture.json unchanged: blob4dca83405d37d72d551007930e742e8d4b102b9b;
  SHA256 633e2a5690c40cb4eb460153e14348a36287e9e76ee3dda2a83a0c4c994acd25.
Typed contract, S1 identity extension and Portal source unchanged.

## Findings and evidence

B1: remaining budget is computed before item work. Only page_items[:remaining] is
shape-checked, projected and strict-serialized. Projected accumulator never exceeds500.
Overflow suffix is unprocessed/UNKNOWN. Over-cap takes precedence over page-overlong;
valid prefix remains PARTIAL. A malformed/unsupported item INSIDE the retained prefix
still invalidates the affected output and stops that read. No new HTTP byte-size cap
is claimed: JSON decoding still receives the returned response.

B2: validated increments after each successful item projection AND strict serialization.
A later malformed item preserves successful-work count while affected output is empty.
Tests inspect actual projector invocations, counters, output and continuation calls.

All five paginated kinds (F-CNP/F-NP/F-GNP/F-HEP/F-TIER) covered. Reviewer matrix now
151/151, including previously failing five bounded-suffix cases. Exit0 from reproduce.py
alone is not the verdict: every expected_safety_assertion_pass was checked.
Accepted context/discovery, version uniqueness, coherent journal, unsupported diagnostic,
schema normalizer, actual archived fixture and no-leak behavior remain passing.

Evidence root:
evidence/P8/20261101-p8c-rv02-dd2a411-review/

See coverage-matrix.md for requirement -> code -> test -> evidence. This review supplies
the consolidated final matrix and independently captured commands/UTC/exits; no historical
author transcript is rewritten. Author result records its own UTC/Python/command; reviewer
does not invent missing per-command author metadata. Reviewer execution.json is authoritative
for THIS independent replay (Python3.12.14). All collector subprocesses mocked; zero
cluster/SSH/registry operations.

## Next boundary

Source correction is complete. Do not request another source-rework cycle or rerun accepted
tests without a new defect/source change. Next project step is a SEPARATE, narrowly scoped
Architect live gate for the pinned follow-up package, only after access prerequisites
are evidenced. It must identify exact script/dependency bytes, approved context/read set,
one-run budget, host-key trust and safe authorized credentials, output contract and return
evidence. This document does NOT grant that gate.

Do not transfer/run the collector, contact cluster/nodes, apply policies, publish/dispatch
workflows, use workflow token, run real Owner helpers, production migrations/deployment.
No repeat base inventory, native PG17, Portal, registry chain or backup/restore/PITR/failover/P7.
Maintain live UNKNOWNs until authorized evidence establishes them.
