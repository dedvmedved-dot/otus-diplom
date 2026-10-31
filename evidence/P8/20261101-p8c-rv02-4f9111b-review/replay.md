# Replay and reusable regression — 4f9111b

Put exact reviewed source files beside this evidence:
portal/networkpolicy/{followup.py,followup_test.py,supplemental.py,followup-typed-contract.json}
at ref4f9111b2a60945fad08b8f150a6069e6edd405a8.
Verify hashes in observations.json. Collector main MUST run only under the provided
mock harness. No live/SSH/registry operations.

Run: python3 verify.py
Execution.json records actual UTC/Python/process exits.
- author followup_test.py -v:81/81 PASS, exit0.
- reproduce.py:151 assertions,131 matched/20 failed; exit0 only means capture worked.
- regression_test.py:7 methods;6 have32 failing subcases; exit1.
  The one passing method verifies the derived archived identity mapping.
These failures overlap; they are not52 independent defects.

regression_test.py is a reusable correctness test. Its exit must become0 after fixes.
reproduce.py is an observation script; inspect explicit assertion verdicts, not its
exit. Compared with prior review, it accepts fixed human-readable parse causes,
rather than requiring literal PARSE_ERROR in journal.cause.
All collector subprocess.run invocations are mocked; no actual kubectl.

derived-i1-fixture.json is sanitized offline reconstruction, NOT raw captured Pods.
To regenerate, read the original accepted JSONL at the commit/path in its provenance,
save locally as accepted-supplemental.jsonl, then python3 derive_fixture.py.
It checks the original full SHA256 and writes only the mapped fixture. Existing
historical JSONL is not edited or duplicated in this new evidence directory.
The synthetic PodList resourceVersion is a test envelope, never a claim about live RV.

No supplemental/registry-chain/PG17/Portal/backup test rerun. All live gates closed.
