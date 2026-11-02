# Replay (offline)

Source under review: 4913f07abd2914dbfa24f39526e05bbc9f0f4ca1.
Exact source blobs/SHA256 in source-blobs.json and verification.json.

In new scratch directory, recreate repo/portal/networkpolicy with followup.py,
followup_test.py, supplemental.py, supplemental_test.py, derived-i1-fixture.json,
followup-typed-contract.json from this SHA. Put calico-v3.32.0.yaml at
repo/ansible/playbooks/files/ from the same SHA. Copy the previous supplied
podlist_boundary_regression_test.py from evidence/P8/20261102-p8c-rv02-980cee5-review/
into repo/portal/networkpolicy/. Copy this review's item_diag_regression_test.py there.
Place source-blobs.json and verify.py at scratch root. Python test dependency: PyYAML.

From repo/portal/networkpolicy run:
python3 followup_test.py
python3 supplemental_test.py
python3 podlist_boundary_regression_test.py

Recorded fresh results: 143/143, 36/36, 6/6; exit0 each. Exact commands, Python, UTC
and cwd in execution.json. ResourceWarnings in legacy harness not treated as blockers.

From scratch root: python3 verify.py
This verifies exact blobs, runs residual regression (expected exit1, 6 failing subcases
on 4913f07), and uses an in-memory diagnostic-only adapter to prove None-to-empty-object
normalization closes all 14 subcases. No runtime source changed. The candidate is review
code only, not an accepted implementation. It also verifies MI-01 input immutability.
No SSH/live/registry or accepted platform tests were run.

Scope: MI-01 closed. MI-02 fail-closed/value-free behavior passes; only the precision
of STATUS when optional status is absent/null remains. This is not an identity bypass.
Exact historical live-failing Pod field remains unknown.
