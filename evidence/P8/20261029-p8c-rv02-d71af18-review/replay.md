# Offline replay — d71af18 independent review

Reviewed source: 78268f6f542b6e58685a0802ee40eae368e089c5.
Reviewed evidence/main: d71af18c27059bcd9ce3ae3c2b15686d7df953c6.
All input source fetched using GitHub Connector at that immutable ref.

Place these exact source files from portal/networkpolicy/ alongside this evidence
in an isolated local directory: followup.py, followup_test.py, supplemental.py,
followup-typed-contract.json. Verify their full hashes using observations.json.
Do not execute collector main without mocks or connect to any cluster.

Run:
```sh
python3 verify.py
```

verify.py executes author followup_test.py -v and independent reproduce.py, then
performs schema-normalization assertions. It records UTC/versions/actual process
exit codes in execution.json and captured output files.

reproduce.py runs 151 offline assertions against main() with ALL kubectl subprocess
calls mocked. Its exit0 means observations were captured; inspect the per-case
expected_safety_assertion_pass and reproduce-summary.json. This review observed
92 matching assertions and59 nonmatching assertions; these share root causes and
are not59 independent defects. Successful author68 tests do not override these facts.
The source-only normalizer assertions PASS and accepted source hash remains unchanged.

observations.json contains synthetic fixture outputs/target argv, not live inventory.
Continue values in reviewer actual_target_argv are SYNTHETIC test data for checking
encoding, never cluster tokens. Collector output must redact actual continuation.
Field category=null means OK in this implementation; missing category must not be
confused with a missing/unexecuted record. Large projected lists are represented by
output_count and first output_sample in reviewer evidence only.

No accepted supplemental/S1/registry-chain/PG17/Portal/backup test rerun was required.
No cluster/SSH, runtime, CI, workflow, provisioning, or policy mutation occurred.
This evidence does not establish live readiness or grant any deployment permission.
