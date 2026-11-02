# Replay — eed114e acceptance

Source eed114e2201f75c3235b33779780038f1e8822df, parent 648be2ad2702c8525a785345074cfb1da42c409c.
Use isolated checkout/scratch copy preserving repository layout. Dependencies: Python3, PyYAML.
Verify source bytes against verification.json hashes before testing.
From portal/networkpolicy:

    python3 followup_test.py

Copy supplied item_diag_regression_test.py from
 evidence/P8/20261102-p8c-rv02-4913f07-review/
into a scratch copy of portal/networkpolicy (not a production edit), then:

    python3 item_diag_regression_test.py

Recorded: 147 tests PASS and 4 methods/14 subcases PASS, both exit0.
The supplied test blob/SHA-256 are recorded in verification.json.
Real commands, Python version and UTC timestamps are in verification.json.
source.patch is the complete runtime diff from previously reviewed 4913f07.
Supplemental source/tests/fixtures/manifest hashes checked against prior independently
fetched bytes; no change in compare. No supplemental suite rerun and no live/SSH/registry.
