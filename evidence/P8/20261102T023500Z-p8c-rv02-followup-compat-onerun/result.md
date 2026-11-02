# P8C-RV02-FOLLOWUP-COMPAT-ONE-RUN-20261102 — live run evidence

Date: 2026-11-02 (UTC). Executor: PRIMARY HERMES. One pinned read-only run on node-01 only.

## Gate / source binding
```text
GATE_ID=P8C-RV02-FOLLOWUP-COMPAT-ONE-RUN-20261102
GATE_SHA=e9553b82964daf10d1835f0bc0ff6b6fea548baa
RECOVERY_MAIN_SHA=e9553b82964daf10d1835f0bc0ff6b6fea548baa
ACCEPTED_SOURCE_SHA=fdfc776570c7f44e559eefcd092e2ca58595ee48
SSH_TARGET=root@192.168.194.38 (node-01)
HOST_KEY (ED25519)=SHA256:4Janc/G5wzV6Yfi8gPTz55u/81atXF1xzjkDIISJjvc (verified against pinned known_hosts)
AUTH=id_ed25519 (hermes@vps1) key-only; no password/sshpass/token fallback
CONTEXT=kubernetes-admin@pak-portal
```

## Pinned files (extracted from ACCEPTED_SOURCE_SHA, blob+SHA256 verified local + node)
```text
followup.py:     blob 6dbfad124a486b0f2d6eccb791777608918fac35  sha256 fc78d03af06f60bbcdde967810ee65a28f37df96a0d85a003807f097fa179e2b
supplemental.py: blob 1b613fbd1e35a109072d2843d6e5f3a3fd47b3d6  sha256 ddd9a4dc17bca97d6b36ae6b4d501e1722c5d38d6e5ac8c7b051698fa0b15491
```
Both re-checked with `sha256sum --check` on node-01 immediately before execution (both "ЦЕЛ"/OK).

## Preflight (key-only SSH)
```text
hostname -s = node-01 · id -un = root · python3 = 3.11.2 · admin.conf READABLE
kubectl client v1.36.2 / server v1.36.2 (context kubernetes-admin@pak-portal)
```

## Run
```text
START_UTC=2026-11-02T02:33:08Z
END_UTC=2026-11-02T02:33:09Z
EXIT_CODE=1
command: python3 -B followup.py --context kubernetes-admin@pak-portal --output <bundle>/followup-output
```

## Per-record dispositions (9 records, 4 actual collector invocations)
| ID | exit | category | complete | diag | blocked_by |
|---|---|---|---|---|---|
| F-D1 | 0 | OK | — | — | — |
| F-I1 | 0 | PARSE_ERROR | false | ITEM | — |
| F-CS | 0 | OK (compatible) | — | — | — |
| F-CNP | 0 | OK | true (0 items) | — | — |
| F-NP | — | BLOCKED_NOT_EXECUTED | — | — | F-I1 |
| F-GNP | — | BLOCKED_NOT_EXECUTED | — | — | F-I1 |
| F-FELIX | — | BLOCKED_NOT_EXECUTED | — | — | F-I1 |
| F-HEP | — | BLOCKED_NOT_EXECUTED | — | — | F-I1 |
| F-TIER | — | BLOCKED_NOT_EXECUTED | — | — | F-I1 |

## Observed facts (not conclusions)
1. **F-D1 OK** — `crd.projectcalico.org/v1` serves 23 API resource descriptors (incl. a status
   subresource), covering networkpolicies, globalnetworkpolicies, felixconfigurations,
   hostendpoints, tiers, networksets, ippools, ipamblocks, bgppeers, etc.
2. **F-CS compatible=true** — live ClusterNetworkPolicy CRD v1alpha2 normalized spec hash
   `ff433d3463dfa2264a7a3ff6201baabf1ec789e98664aff3401a7ef79ae7ce5e` equals the pinned Calico
   manifest value. The prior "schema drift" was a wrong pin, not a live change (LR-02 confirmed).
3. **F-CNP OK, 0 items** — `clusternetworkpolicies` list returns an empty list (received=0,
   validated=0): no ClusterNetworkPolicy objects are deployed in the cluster.
4. **F-I1 PARSE_ERROR (diag=ITEM)** — the raw GET PodList envelope/metadata parsed correctly
   (exit 0), but a calico-node pod item failed the accepted `project_pod_identity` projection,
   so identity is not approved and the five Calico object reads are blocked. This is a factual
   disposition; the accepted image/digest guard was not relaxed and no manual re-read was done.

## Remaining UNKNOWN (unchanged)
No effective-policy-union, per-node CNI mode, or traffic/directed-flow conclusion is drawn.
F-I1 identity and the five Calico object reads (NP/GNP/Felix/HEP/Tier) remain unresolved; the
actual failing pod field is not recovered (raw stdout suppressed by design). No policy objects
of the Calico kinds were read.

## Returned artifacts + hashes
```text
followup.jsonl  sha256 a78150aaef00ab37009674292a2a8bf2a95f21866f81c51d9d2a9322982e761c
run-meta.txt    sha256 380c9bd1c18d5dd0970d16e145d36c3db540186225cfbc35485149ef34131fc7
SHA256SUMS.result (node-generated)
```
Secret scan: none found (API descriptors + CRD metadata/hash + empty list only; no raw objects,
kubeconfig, tokens, keys).

## Budget / status
```text
NEW_GATE_RUN_BUDGET=CONSUMED
PHASE2_NEW_RUN_APPROVED=NO (this one run only)
NETPOL_APPROVED_FOR_APPLY=NO
FLOW_MATRIX_COMPLETE=NO (identity + 5 Calico object reads still blocked)
P8C=NOT_FINAL_ACCEPTED · P8D–P8G/P9=NOT_AUTHORIZED
```
STOP for Architect review. EXIT=1 / PARTIAL / PARSE_ERROR does not authorize a rerun.
