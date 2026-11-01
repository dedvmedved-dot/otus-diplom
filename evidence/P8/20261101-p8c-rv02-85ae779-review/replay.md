# Offline replay —85ae779

Source ref164b29760c1ef8227de4230083ae9a11d5598e92; reviewed main85ae7794c106cccfd5a01f46632ab1865558f07a.
Place exact portal/networkpolicy/{followup.py,followup_test.py,supplemental.py,
followup-typed-contract.json,derived-i1-fixture.json} beside these evidence scripts.
Check hashes in observations.json. No live collector execution.

Run python3 verify.py. execution.json captures UTC/Python/actual process exits.
- author suite95/95 PASS,exit0;
- previous reviewer regression7/7 PASS,exit0;
- reproduce151 observations146matched/5failed;exit0 only means capture;
- bounded_projection_test.py4methods25failing subcases;exit1 (remaining defect).

The bounds regression must exit0 after correction, as must previous regression7.
Do not weaken assertions or modify historical review artifacts.
All collector requests mocked; synthetic tokens in actual_target_argv are test data.
No cluster/SSH, CI, policy apply, registry download or accepted subsystem test rerun.

Fixture in portal/ is byte-identical to the earlier supplied derived fixture; full
mapping/provenance is inside it. It is not raw captured Pods or fresh live evidence.
