# P8C-R1 RV-02 — follow-up one-time live gate DRAFT

Status: **DRAFT / NOT_AUTHORIZED_FOR_RUN**. This document PREPARES a future narrow live gate;
it does NOT grant it, does not authorize transfer/run, and does not reopen the consumed
one-run budget. Date: 2026-11-01 (UTC).

## 1. Pinned package (from G1 manifest)
See `docs/architecture/P8C_RV02_FOLLOWUP_LIVE_MANIFEST_20261101.md`. Two files extracted from
ACCEPTED_SOURCE_SHA `05d61ac…`, with the blob/SHA-256 controls listed there. Any hash or
context mismatch → STOP before execution. No launcher, no code change.

## 2. Access conditions (G2) — established from existing records only; no new probes

### 2.1 SSH host-key authenticity — BLOCKED_EXTERNAL
Previously the operator session used `ssh-keyscan` + `StrictHostKeyChecking=yes` (trust-on-first-use)
plus a root-only credential file. As already recorded (`ACCESS_COMPLIANCE=NOT_FULLY_EVIDENCED`),
that does not independently authenticate node-01. **Required before any run:** the Owner must
provide an independent, out-of-band trusted host-key fingerprint source (e.g. a fingerprint
recorded at provisioning, from the BMC/ILO console, or another trusted channel), and that
fingerprint must match the node-01 SSH host key. The fingerprints captured by the earlier scan
are NOT an independent proof.

### 2.2 Authorized authentication method — BLOCKED_EXTERNAL
The previously disclosed password must NOT be used, recovered, or requested. **Required before
any run:** the Owner must establish a current authorized credential that was not previously
exposed (e.g. a new key-based or rotated credential) and confirm it out-of-band. The existence
of `/etc/hermes/pak_root_pass.txt` is not proof of a safe credential and its value is not used.

### 2.3 Execution location and kubeconfig
The collector runs on **node-01** (mgmt 192.168.194.38) using the node's existing
`KUBECONFIG=/etc/kubernetes/admin.conf` (context `kubernetes-admin@pak-portal`). The kubeconfig
is NOT copied off the node; its contents are not read or published.

### Consolidated Owner request (no secrets in chat)
> Confirm via a separate trusted channel, before any run authorization: (1) an independent
> trusted source for the node-01 SSH host-key fingerprint (or the fingerprint itself to compare);
> (2) that a current, not-previously-exposed credential is available for operator execution (do
> not send the value here). Until both are evidenced, access remains BLOCKED_EXTERNAL and no run
> is performed.

## 3. One-run boundaries (G3)

### 3.1 Scope
Exactly one run of the pinned `followup.py`, context `kubernetes-admin@pak-portal`, against the
accepted read table. No automatic retry. A fresh, non-existent output directory is used
(the collector fails with `FileExistsError` on an existing directory).

### 3.2 Accepted read table
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

### 3.3 Limits and timeouts
```text
wrapper: kubectl --context kubernetes-admin@pak-portal --request-timeout=15s
subprocess timeout: 20s each
pagination: limit 200 / 200 / 100 · total cap 500 · max 3 pages (continue token URL-encoded, never emitted)
max Kubernetes requests on full dependency pass: 4 non-paginated + 5×3 = 19
```
F-CS schema fingerprint is compared to the embedded `CNP_SPEC_SHA256`; well-formed mismatch →
UNSUPPORTED (blocks F-CNP), malformed → PARSE_ERROR. Unknown semantic fields → UNSUPPORTED;
malformed/nonfinite → PARSE_ERROR; transport failures keep their distinct categories and a
per-page journal. Exit 1, PARTIAL, UNSUPPORTED and BLOCKED_NOT_EXECUTED are preserved as actual
results (they are not "no policy" claims and do not permit a rerun).

### 3.4 Stop conditions (before any subprocess)
- access not evidenced (host-key trust / safe credential) → BLOCKED_EXTERNAL;
- any pinned file hash mismatch → STOP;
- `--context` != `kubernetes-admin@pak-portal` → STOP (collector exits before any call);
- output directory already exists → STOP (`FileExistsError`).

### 3.5 Return package
- sanitized collector result (`followup.jsonl`);
- SHA-256 of the result and of each pinned file;
- actual UTC start/end and exit code;
- executor + environment identification WITHOUT secrets;
- summary of categories and blocked dependencies.

### 3.6 Additional node commands (for separate agreement — NOT expanded now)
`hostname -s`, `python3 --version`, `kubectl version -o json` (identity/version preflight only).
No other command is added by this draft.

## 4. Mandatory status (unchanged)
```text
PHASE2_NEW_RUN_APPROVED=NO
OWNER_PHASE2_HANDOFF_ALLOWED=NO
NETPOL_APPROVED_FOR_APPLY=NO
P8C=NOT_FINAL_ACCEPTED
P8D–P8G/P9=NOT_AUTHORIZED
```
