# Independent source review replay

Reviewed main bcda2f78e20a5f83a05f021c5bb4726202f6ca0e; source
3139e08e4243868d5de2aa9f52d054e424e0a653. Inputs fetched through GitHub Connector.
No cluster access. No registry chain re-download.

Stage in a fresh local directory:
- supplemental.py and supplemental_test.py from reviewed main portal/networkpolicy/;
- old.py from portal/networkpolicy/supplemental.py at 69762bf01ae27de2264c8d3d92bac86369f367eb;
- live.jsonl from evidence/P8/20261027T140000Z-p8c-rv02-phase2-live/result/supplemental.jsonl;
- cnp.yaml from kubernetes-sigs/network-policy-api commit 730bd5474d82a2cf82be8b0c6c2a5515598cc44e,
  config/crd/standard/policy.networking.k8s.io_clusternetworkpolicies.yaml;
- calico.yaml from ansible/playbooks/files/calico-v3.32.0.yaml at reviewed main;
- reproduce.py and extract_contract.py from this review evidence.

Actual commands (executed from workspace with that directory named review-bcda2f7):
python3 review-bcda2f7/supplemental_test.py -v
python3 review-bcda2f7/reproduce.py
python3 review-bcda2f7/extract_contract.py
All exit 0. The suite reports 36 tests. All collector subprocess.run calls are mocked.
No prior PG17/Portal/backup tests were run. The reproducer validates old/new AST scope,
stored projected identities, 28 finite cases and dependent mock calls.

Extraction emits typed-contract.json and hashes in schema-check.json. The exact emitted
JSON is committed as portal/networkpolicy/followup-typed-contract.json.
This is a source-schema artifact, not a snapshot of installed live CRDs.
The corrected design is Architect-authored; new collector implementation is NOT_EXECUTED.

Reviewer environment: Python 3.12.14; PyYAML 6.0.3.
