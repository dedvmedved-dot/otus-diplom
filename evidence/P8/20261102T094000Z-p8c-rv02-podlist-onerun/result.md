# P8C-RV02-PODLIST-ONE-RUN-20261102 — live run evidence (EXIT=0)

Date: 2026-11-02 (UTC). Executor: PRIMARY HERMES. One pinned read-only run on node-01 only.
Accepted bundle eed114e (MI-01/MI-02/MI-02A applied); no source rework on the node.

## Gate / source binding
```text
GATE_ID=P8C-RV02-PODLIST-ONE-RUN-20261102
GATE_SHA=740a62026532505256a9754437da13fe4a5ed5c2
RECOVERY_MAIN_SHA=740a62026532505256a9754437da13fe4a5ed5c2
ACCEPTED_SOURCE_SHA=eed114e2201f75c3235b33779780038f1e8822df
SSH_TARGET=root@192.168.194.38 (node-01)
HOST_KEY (ED25519)=SHA256:4Janc/G5wzV6Yfi8gPTz55u/81atXF1xzjkDIISJjvc (verified against pinned known_hosts)
AUTH=id_ed25519 (hermes@vps1) key-only; no password/sshpass/token
CONTEXT=kubernetes-admin@pak-portal
```

## Pinned files (extracted from ACCEPTED_SOURCE_SHA; blob+SHA256 verified local + node)
```text
followup.py:     blob 4917bc9db76748202dfa3e799651474808aaf567  sha256 8e01355087db65d3c124f0a21ac5a4dd89acf0caaabc092836d469169fe57a7b
supplemental.py: blob 1b613fbd1e35a109072d2843d6e5f3a3fd47b3d6  sha256 ddd9a4dc17bca97d6b36ae6b4d501e1722c5d38d6e5ac8c7b051698fa0b15491
```
Local `hash-check-local.txt` + remote `hash-check.txt` (created by the G3 block) both recorded; remote
hash-check exit 0, both files "ЦЕЛ"/OK.

## Preflight (key-only SSH, per-check UTC/exit in preflight.txt)
```text
hostname -s = node-01 · id -un = root · python3 = 3.11.2
command -v python3 = /usr/bin/python3 · command -v kubectl = /usr/bin/kubectl
admin.conf READABLE · kubectl client v1.36.2 / server v1.36.2
```

## Run
```text
START_UTC=2026-11-02T09:35:24Z
END_UTC=2026-11-02T09:35:25Z
EXIT_CODE=0
command: python3 -B followup.py --context kubernetes-admin@pak-portal --output <bundle>/followup-output
```

## Per-record dispositions (9 records, 9 collector invocations, all OK)
| ID | exit | category | complete | diag | itemDiag | result |
|---|---|---|---|---|---|---|
| F-D1 | 0 | OK | — | — | — | 23 API resource descriptors |
| F-I1 | 0 | OK | true | — | — | 3 calico-node pods, identity approved |
| F-CS | 0 | OK | — | — | — | compatible=true (ff433d34…) |
| F-CNP | 0 | OK | true | — | — | 0 items |
| F-NP | 0 | OK | true | — | — | 0 items |
| F-GNP | 0 | OK | true | — | — | 0 items |
| F-FELIX | 0 | OK | — | — | — | default FelixConfiguration (nftablesMode=Auto) |
| F-HEP | 0 | OK | true | — | — | 0 items |
| F-TIER | 0 | OK | true | — | — | 3 items |

## Observed facts (not conclusions)
1. **F-I1 OK** — 3 calico-node pods identified in kube-system: `calico-node-4krkt`,
   `calico-node-lgmtz`, `calico-node-mqrgg`. The accepted typed-PodList TypeMeta adapter (MI-01)
   resolved the previous ITEM failure; identity approved through the unchanged S1 image/digest
   gate, projected to safe metadata/initContainers/containers (name/image/imageID/ports/restartPolicy).
2. **F-CS compatible=true** — live CNP v1alpha2 schema hash equals the pinned Calico manifest
   `ff433d3463dfa2264a7a3ff6201baabf1ec789e98664aff3401a7ef79ae7ce5e`.
3. **F-CNP / F-NP / F-GNP / F-HEP = 0 items** — no ClusterNetworkPolicy, NetworkPolicy,
   GlobalNetworkPolicy or HostEndpoint objects at collection time.
4. **F-FELIX** — default FelixConfiguration: `nftablesMode=Auto` (bpfEnabled/iptablesBackend/
   nodeSelector null). Per-node FelixConfiguration objects were not read.
5. **F-TIER** — 3 Tier objects: `default` (order 1000000, defaultAction=Deny), `kube-admin`
   (order 1000, defaultAction=Pass), `kube-baseline` (order 10000000, defaultAction=Pass).

## Remaining UNKNOWN (unchanged, concrete)
- Effective per-node CNI mode: only the default Felix `nftablesMode=Auto` is observed; per-node
  Felix overrides (nodeSelector/env/config) and node-scoped FelixConfiguration objects were not read.
- Effective policy union / tier ordering / DNAT / enforcement point: 0 NP/GNP/CNP/HEP objects +
  tier defaults are recorded, but tier→endpoint binding and full policy evaluation are not
  established. No traffic/directed-flow conclusion.

## Returned artifacts
```text
followup.jsonl       sha256 6dd94032934cdb43e984b7cceec26edefb3e7e4b1c48b522118b1424e63b3676
run-meta.txt         sha256 e6b77ebee9bdeaab80d9a4d0f6ed67102bf51e99072626ca0317919190ea6525
hash-check.txt       sha256 f3f25067d1bd3da08fcd9afc869968a69594e7d8b7588f030e09f64b5e3bbd6d
SHA256SUMS.result    (node-generated, 5 entries)
preflight.txt / hash-check-local.txt / run-intent.txt (local transcripts)
SHA256SUMS.evidence  (Hermes-side, all returned + local transcripts)
```
Secret scan: none (API descriptors, CRD metadata/hash, empty lists, tier names, projected safe
identity only; no raw objects, kubeconfig, tokens, keys).

## Budget / status
```text
NEW_GATE_RUN_BUDGET=CONSUMED
PHASE2_NEW_RUN_APPROVED=NO (this one run only)
NETPOL_APPROVED_FOR_APPLY=NO
FLOW_MATRIX_COMPLETE=YES (all 9 reads executed and returned valid dispositions; semantic limits above)
P8C=NOT_FINAL_ACCEPTED · P8D–P8G/P9=NOT_AUTHORIZED
```
STOP for Architect review. EXIT=0 does not authorize apply/CI/production; no rerun needed or allowed.
