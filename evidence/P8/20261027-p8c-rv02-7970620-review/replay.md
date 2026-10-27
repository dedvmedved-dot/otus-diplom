# Replay documentary checks (offline only)

Accepted documentary tree: 73e92361594ce760f79e0f6af27cbf353ae73a2a.
The check does not execute supplemental.py, tests or kubectl.

Create a temporary replay directory with:
- check_docs.py from this evidence directory.
- portal/networkpolicy/{supplemental.py,supplemental_test.py,supplemental-design.md,coverage-matrix.md,PLAN.md,flow-matrix.md,gaps.md,collection-map.md} from the accepted documentary tree.
- reference/execution.json and reference/observations.json from
  evidence/P8/20261027-p8c-rv02-7584df5-review/ (unchanged historical evidence).
- reference/calico-config.go from projectcalico/calico commit
  eb1cf57823a1dd8d25c48b82fd023ea9e3e17996, felix/config/config_params.go,
  git blob 72676f76f3bdd5f592e29313c712b159db0bcd2e.

Run python3 check_docs.py from any working directory. It resolves inputs relative
to its own location and writes doc-check.json with the replay timestamp.
Expected exit: 0. Do not overwrite the published historical check output.
Primary-source and documentary interpretation checks listed in doc-check.json are
manual checks; the script does not claim to mechanically validate prose semantics.
No credentials, cluster access, live reads or new test execution are needed.
