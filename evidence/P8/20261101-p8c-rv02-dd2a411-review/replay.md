# Independent offline replay

Reviewed source05d61ac74e88256adee455dcefd2d9c33335b6b3, evidence dd2a4115e6d4c7799a4acf5156a42ab0590ceea8.
Fetch exact source files via GitHub Connector at that ref into an isolated directory:
portal/networkpolicy/{followup.py,followup_test.py,supplemental.py,supplemental_test.py,inventory.py,followup-typed-contract.json,derived-i1-fixture.json}.
Add this directory's reproduce.py, regression_test.py, bounded_projection_test.py, verify.py.
Run python3 verify.py. Every collector kubectl/subprocess operation is mocked by these tests.
No live collector invocation, SSH, registry, Portal or PG17 test.

verify.py records commands, actual UTC start/end and child exits in execution.json.
Its recording exit0 is not the verdict: check each child exit0 AND
reproduce-summary.json.failed=0 AND every observations.json case expected_safety_assertion_pass=true.
Expected counts:99/36/7/4; observation matrix151/151.
Previous reviewer test files copied byte-for-byte; reproduce.py changes only reviewed_sha metadata.
No historical evidence modified. See coverage-matrix.md and acceptance document.
