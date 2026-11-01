# Replay / source provenance

All inputs fetched via GitHub Connector at 3a0afb45b07daa8ac5e5ceb41563fc518db87dc9:
- portal/networkpolicy/{followup.py,supplemental.py,followup_test.py,followup-typed-contract.json}
- ansible/playbooks/files/calico-v3.32.0.yaml
- evidence/P8/20261101T193800Z-p8c-rv02-followup-onerun/{followup.jsonl,run-meta.txt,SHA256SUMS.result}
Put those basenames with reproduce.py in a new offline directory. Also fetch official Kubernetes
v1.36.2 staging/src/k8s.io/kubectl/pkg/cmd/get/get.go as kubectl-get.go (blob4a84ec23a6ea02235fb3282b76abbed6083bc9ff).
Run: python3 reproduce.py
Actual run: exit0; stdout equals verification.json. Python3.12.14, PyYAML6.0.3.
All subprocess.run calls inside imported test harness are mocked; no kubectl/SSH/cluster activity.
No complete accepted suite rerun; only address-specific reproduction.
An initial ad hoc schema-inspection shell command had an unmatched parenthesis and exited1
before executing Python logic; it was corrected. The saved reproduction executed exit0.
The synthetic List fixture is derived from the official kubectl printGeneric code, not live raw stdout.
