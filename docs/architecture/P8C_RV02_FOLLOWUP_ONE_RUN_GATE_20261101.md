# P8C-R1 RV-02 — FOLLOW-UP LIVE RUN GATE (one run)

Date:2026-11-01 (Europe/Moscow). Executor: PRIMARY HERMES ONLY; Hermes2 excluded.
Repository:dedvmedved-dot/otus-diplom. GitHub main is sole Source of Truth.

## Decision and precedence

```text
GATE_ID=P8C-RV02-FOLLOWUP-ONE-RUN-20261101
RECOVERY_MAIN_SHA=915f2c640cb3f0024c7631b6c9284ca0eea99cd7
ACCEPTED_SOURCE_SHA=05d61ac74e88256adee455dcefd2d9c33335b6b3
HOST_KEY_TRUST=ACCEPTED_OWNER_OUT_OF_BAND_ATTESTATION
SAFE_AUTH_METHOD=ACCEPTED_OWNER_REPORTED_AUTHORIZED_SSH_KEY
EXECUTOR=PRIMARY_HERMES
SSH_TARGET=root@192.168.194.38 (node-01)
PHASE2_NEW_RUN_APPROVED=YES / ONE_PINNED_FOLLOWUP_RUN_ONLY
OWNER_PHASE2_HANDOFF_ALLOWED=YES / PRIMARY_HERMES_ONLY
NEW_GATE_RUN_BUDGET=1 (not started by Architect)
PREVIOUS_GATE_RUN_BUDGET=CONSUMED / NOT_REOPENED
NETPOL_APPROVED_FOR_APPLY=NO
P8C=NOT_FINAL_ACCEPTED
P8D–P8G/P9=NOT_AUTHORIZED
```

This published gate explicitly supersedes the NO statuses of earlier preparation/host-key
documents ONLY for the transfer, preflight and single follow-up run specified here.
The previous draft remains historical preparation; it grants no additional authority.
No further Owner confirmation is needed to execute within this gate after successful preflight.

Bases: source acceptance a293e96cbec87917e8b767cf5debd098574da211; preparation review
fc584690a2b47b7c42933c3722ceec424f4f90bf; Owner host-key acceptance915f2c6;
evidence/P8/20261101-p8c-rv02-key-auth-owner-report/owner-report.md.
Access acceptance relies on explicit Owner/forwarded operator reports. Architect did not
independently log into the hosts or verify authentication. Pin checks remain mandatory.

## G0 — recovery, package and gate accounting

Fetch actual remote main, read this gate, verify source acceptance and absence of conflicting
new decisions. Unexpected concurrent source/gate changes or dirty conflicting work ->STOP,
no reset/force. Record full GATE_SHA (the commit introducing this file), recovery main and source.
Confirm this new gate has not already been consumed; no parallel operator/Hermes2 run.

Extract ONLY these files from accepted source05d61ac, not mutable working-tree bytes:

| File under portal/networkpolicy/ | Git blob | SHA-256 |
|---|---|---|
| followup.py | 8f2d7f6d0d3d033810046d93b33448f465ab57f6 | f48cfc825f25a002cac6afcc63da9f7d5800a3a92b5bc231eeb456b7d6328b98 |
| supplemental.py | 1b613fbd1e35a109072d2843d6e5f3a3fd47b3d6 | ddd9a4dc17bca97d6b36ae6b4d501e1722c5d38d6e5ac8c7b051698fa0b15491 |

Two files are sufficient; no test fixture or schema data file runtime dependency.
Do not change code, accepted tests, identity contract, schemas, policy manifests or runtime.

Use extraction/hash blocks from
docs/architecture/P8C_RV02_FOLLOWUP_LIVE_MANIFEST_20261101.md
at915f2c640cb3f0024c7631b6c9284ca0eea99cd7 (blob1041ab7bc72f5696691a6d2b4b743638500fc4f0).
Local staging directory must be new/private; verify both SHA256 AND git blob values.
Do not rerun accepted source/PG17/Portal/registry-chain test suites.

## G1 — SSH identity and authentication boundary

Use existing authorized VPN route to192.168.194.38. No subnet scan, BMC fallback, other-node
connection, password fallback or credential provisioning.
Expected node-01 server ED25519:
SHA256:4Janc/G5wzV6Yfi8gPTz55u/81atXF1xzjkDIISJjvc

Locally select the already-authorized id_ed25519 key (hermes@vps1) by its actual path.
Do not print/read/export its contents, private key passphrase or password files. If the key is
not available through the reported safe mechanism, STOP; do not recover old credentials.

Prepare a dedicated known_hosts file containing only the node-01 ED25519 public entry.
Prefer the existing entry; independently compute its SHA256 fingerprint with ssh-keygen and
require exact equality to the trusted value above. If no entry is available, one bounded
ssh-keyscan -T5 -t ed25519 192.168.194.38 is allowed solely to obtain public key bytes:
accept them only AFTER exact fingerprint comparison, never on TOFU. Mismatch/ambiguity ->STOP.
Pin the resulting file for every SSH/SCP operation.

Mandatory SSH/SCP settings (same for transfer, run and return):
BatchMode=yes; IdentitiesOnly=yes; explicit -i authorized-key-path;
PreferredAuthentications=publickey; PasswordAuthentication=no;
KbdInteractiveAuthentication=no; StrictHostKeyChecking=yes;
HostKeyAlgorithms=ssh-ed25519; UserKnownHostsFile=verified-dedicated-file;
GlobalKnownHostsFile=/dev/null; UpdateHostKeys=no; ForwardAgent=no;
ClearAllForwardings=yes; ControlPath=none; ConnectionAttempts=1; ConnectTimeout=10.
No disabling host checks or use of another key/account/target to bypass failure.
Root is allowed for this bounded operator activity, not as a privilege grant to Portal.

## G2 — authorized preflight and transfer

Through the pinned key-only connection to node-01, permitted preflight commands:
- hostname -s: must equal node-01;
- id -un: must equal root;
- date -u +%Y-%m-%dT%H:%M:%SZ;
- python3 --version: existing accepted Python3.11.x;
- command -v python3 / command -v kubectl; test readability of admin.conf, without displaying it;
- KUBECONFIG=/etc/kubernetes/admin.conf kubectl --context kubernetes-admin@pak-portal
  --request-timeout=15s version -o json: one invocation; client/server expected v1.36.2.

The version invocation is additional to the collector's maximum19 subprocess calls.
Unexpected host/user/context/version, unreadable kubeconfig, auth failure or timeout ->STOP.
Do not diagnose by expanding to arbitrary reads, package installation or service changes.

Allowed filesystem preparation: mktemp -d under /tmp with a p8c-followup prefix, umask077,
directory mode700; copy the two pinned files via SCP into that new directory, mode600.
Local shell builtins, chmod limited to these new files/directories, sha256sum, date and
metadata/result-file creation are authorized. Existing system files are not modified.
Do not copy kubeconfig off node-01. Do not clone a repository/install dependencies on the node.
Set P8C_APPROVED_BUNDLE_DIR to the absolute new directory. Recheck both SHA256 values on node.
All later writes/returns are confined to this run's directory and local evidence staging.

## G3 — one exact collector execution

Run the node-side Bash block from the pinned manifest named in G0, with:
KUBECONFIG=/etc/kubernetes/admin.conf;
python3 -B followup.py --context kubernetes-admin@pak-portal --output NEW_DIRECTORY/followup-output.
The block performs hash/hostname/output guards, captures UTC start/end/exit and checksum files.
Require a fresh directory with no followup-output, run-meta.txt or SHA256SUMS.result.
No code patch, supplemental.py standalone run, added resource query or identity relaxation.

| ID | Literal argv tail | Kind/shape | Dependencies |
|---|---|---|---|
| F-D1 | `get --raw /apis/crd.projectcalico.org/v1` | discovery (APIResourceList) | — |
| F-I1 | `get pods -n kube-system -l k8s-app=calico-node -o json` | PodList/v1 | — |
| F-CS | `get --raw /apis/apiextensions.k8s.io/v1/customresourcedefinitions/clusternetworkpolicies.policy.networking.k8s.io` | CRD (single) | — |
| F-CNP | `get --raw /apis/policy.networking.k8s.io/v1alpha2/clusternetworkpolicies` | list, paginated | F-CS |
| F-NP | `get --raw /apis/crd.projectcalico.org/v1/networkpolicies` | list, paginated | D1:networkpolicies, F-I1 |
| F-GNP | `get --raw /apis/crd.projectcalico.org/v1/globalnetworkpolicies` | list, paginated | D1:globalnetworkpolicies, F-I1 |
| F-FELIX | `get --raw /apis/crd.projectcalico.org/v1/felixconfigurations/default` | single | D1:felixconfigurations, F-I1 |
| F-HEP | `get --raw /apis/crd.projectcalico.org/v1/hostendpoints` | list, paginated | D1:hostendpoints, F-I1 |
| F-TIER | `get --raw /apis/crd.projectcalico.org/v1/tiers` | list, paginated | D1:tiers, F-I1 |


Five paginated lists use200/200/100, total cap500 and maximum3pages each.
Maximum19 collector-issued kubectl invocations; each request timeout15s/subprocess20s.
This is not an exact wire HTTP-request bound (kubectl discovery/client exchanges may add HTTP).
Accepted dependency gates and structured dispositions are not bypassed.

Budget is consumed when the collector process is started, even if it fails early.
Exit1, PARTIAL, UNSUPPORTED, BLOCKED_NOT_EXECUTED, malformed result or interruption does NOT
authorize a rerun. On uncertain remote outcome report UNKNOWN_OUTCOME; do not repeat the command.
Independent reads within that ONE process follow accepted code behavior; do not manually
continue blocked reads. On preflight failure report NOT_STARTED and STOP pending review.

## G4 — return, reconcile and publish

Return only:
- followup-output/followup.jsonl (if created);
- run-meta.txt;
- SHA256SUMS.result;
- sanitized preflight/hash verification and operator/gate/source identification metadata.

Retrieve existing result files without re-executing the collector. Verify hashes after return.
If interruption prevents ordinary metadata completion, preserve available artifacts and state
the limits; do not invent exit/time or modify original returned bytes.
Do not return raw Kubernetes objects, kubeconfig, keys, passwords, unfiltered stderr or env.
Check content for secret values; secret-reference names/keys are not credential values.
If unsafe content is found, keep it private and report the issue; publish only a sanitized
derivative with explicit provenance and hash, never silently overwrite the original.

Record full source/blob/file SHA256 and output SHA256; start/endUTC; actual exit; executor;
host/context/client/server; per-record category/complete/page journal; consumed gate budget.
Separate observed facts, absence in a surveyed source, unsupported/unread and UNKNOWN.
Base inventory and earlier partial runs remain historical, not replaced.

Reconcile the returned evidence against14FLOW-IDs and existing gaps using record references.
Update current flow-matrix/gaps if supported; do not force FLOW_MATRIX_COMPLETE=YES.
No traffic/directed-flow, effective per-node CNI mode or effective-policy-union conclusion
solely from declared ports, default Felix or a policy list. Preserve unresolved dependencies.
Prepare an offline candidate or conclusions only within existing scope; no policy apply.

Publish NEW evidence and necessary current reconciliation docs to main fast-forward, no force,
no historical-evidence edits. Source code and policies remain unchanged.
Report final remote SHA, GATE_SHA, source/hash bindings, all dispositions, remaining UNKNOWNs,
NEW_GATE_RUN_BUDGET=CONSUMED (or NOT_STARTED with reason), and STOP for Architect review.
Intermediate evidence work needs no additional continue request.

## Exclusions

No further node-02/03 access, key installation/removal, password rotation or SSH configuration
changes. Reports of previous key setup there do not enlarge this gate.
The old password/file is not approved as a fallback or certified safe by this gate.
No NetworkPolicy apply/rollback, arbitrary Kubernetes mutation, pod exec/log/proxy, Secret or
ConfigMap dump, CI/workflow publication/dispatch/token, real Owner helpers, production migration/
deployment, P8D–P8G/P9, repeat backup/restore/PITR/failover/P7/PG17/Portal or registry-chain tests.
