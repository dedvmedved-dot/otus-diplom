# Replaying this independent acceptance

Inputs from GitHub Connector:
- portal/networkpolicy/{followup.py,followup_test.py,supplemental.py,supplemental_test.py,followup-typed-contract.json,derived-i1-fixture.json} at fdfc776570c7f44e559eefcd092e2ca58595ee48.
- ansible/playbooks/files/calico-v3.32.0.yaml at dd00e2f36fdae9cb91baab256ecf9ecf2f662249, blob21ea9b4b163305ea479bc7708965104465ffc716, SHA2568d4b2b1bb97a36d7bf196cc84047aafa41fea5152d678a3fe3994604e8ade3c1.
- compatibility_regression_test.py from evidence/P8/20261102-p8c-rv02-f20f57f-review/ at c1644950c618f7ca7221a9500dc3049363d7bfee, unchanged.
- old followup-typed-contract.json at3a0afb45b07daa8ac5e5ceb41563fc518db87dc9.

Layout: review-fdfc776/repo/portal/networkpolicy/ for Python/tests/fixtures;
review-fdfc776/repo/ansible/playbooks/files/calico-v3.32.0.yaml for manifest;
sibling review-3a0afb4/followup-typed-contract.json for old-candidate verification.
Run the three commands in execution.json from repo/portal/networkpolicy/.
Run python3 verify.py from review-fdfc776/; output verification.json.
Full fresh raw suite outputs, UTC and exits are stored in this evidence directory.
Python3.12.14 and PyYAML6.0.3 were already available; no dependency installation performed.
Synthetic subprocess fixtures never connect to the cluster.
During local file staging a truncated transfer and an invalid patch combination were detected
before tests; files were restaged and exact reported SHA256 verified before execution.
These local staging corrections do not alter source and are not test failures.
