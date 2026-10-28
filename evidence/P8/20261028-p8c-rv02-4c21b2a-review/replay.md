# Review replay 4c21b2a

Inputs fetched through GitHub Connector at 4c21b2a388dfd3d91415335a028f322886d7372e:
portal/networkpolicy/followup.py, followup_test.py, supplemental.py,
followup-typed-contract.json. Stage their exact bytes with reproduce.py and
schema_normalization_reference.py from this evidence in a fresh directory.

Commands actually executed (directory was review-4c21b2a):
python3 review-4c21b2a/followup_test.py -v
python3 review-4c21b2a/reproduce.py
python3 review-4c21b2a/schema_normalization_reference.py
All exit0. Python 3.12.14. Author suite 37 tests passes. The probe command records
47 observations and successfully reproduces defects; it is NOT a correctness PASS.
All calls are mocked. No cluster/SSH/registry access or prior accepted suites rerun.

Review hypotheses are shown in observations.json with category/exit/complete/calls/
selected projected samples. Malformed scalar fixtures crash the collector in several
cases; the reviewer harness catches that outer exception and reports its class.
No raw error or secret content is used. Synthetic token values are mock-only, not live
continuation tokens. Nonfinite sample numbers are represented as marker objects.

Schema normalization reference is an offline illustration of the Architect correction,
not a deployed collector or exhaustive generic JSON Schema validator.
Full SHA256/git blobs for fetched code/contract are in observations.json.
Source diff: two commits from 6272877, only two source and two new evidence files.
supplemental.py is unchanged; accepted S1/registry-chain decisions remain closed.
