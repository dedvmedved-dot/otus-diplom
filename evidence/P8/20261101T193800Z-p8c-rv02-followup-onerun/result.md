# P8C-RV02-FOLLOWUP-ONE-RUN-20261101 — live run evidence

Date: 2026-11-01 (UTC). Executor: PRIMARY HERMES. One pinned follow-up run on node-01 only.

## Gate and source binding
```text
GATE_ID=P8C-RV02-FOLLOWUP-ONE-RUN-20261101
GATE_SHA=fbaa9a4ccde70fd27e581d253e9de7661d299cf4
ACCEPTED_SOURCE_SHA=05d61ac74e88256adee455dcefd2d9c33335b6b3
EXECUTOR=PRIMARY_HERMES
SSH_TARGET=root@192.168.194.38 (node-01)
HOST_KEY_TRUST=ACCEPTED_OWNER_OUT_OF_BAND_ATTESTATION (ED25519 SHA256:4Janc/G5wzV6Yfi8gPTz55u/81atXF1xzjkDIISJjvc)
SAFE_AUTH_METHOD=id_ed25519 (hermes@vps1) key-only; no password fallback used
```

## Pinned file hashes (extracted from ACCEPTED_SOURCE_SHA, verified local + node)
```text
followup.py:      blob 8f2d7f6d0d3d033810046d93b33448f465ab57f6  sha256 f48cfc825f25a002cac6afcc63da9f7d5800a3a92b5bc231eeb456b7d6328b98
supplemental.py:  blob 1b613fbd1e35a109072d2843d6e5f3a3fd47b3d6  sha256 ddd9a4dc17bca97d6b36ae6b4d501e1722c5d38d6e5ac8c7b051698fa0b15491
```
Both re-checked with `sha256sum --check` on node-01 immediately before execution (both "ЦЕЛ"/OK).

## Preflight (key-only SSH, node-01)
```text
hostname -s = node-01 · id -un = root · python3 = 3.11.2 · admin.conf READABLE
kubectl client v1.36.2 / server v1.36.2 (context kubernetes-admin@pak-portal)
```
All preflight checks passed; transfer into fresh private dir /tmp/p8c-followup-6s9gOD (mode 700,
files mode 600), node-side SHA256 re-verified.

## Run
```text
START_UTC=2026-11-01T19:38:13Z
END_UTC=2026-11-01T19:38:14Z
EXIT_CODE=1
command: python3 -B followup.py --context kubernetes-admin@pak-portal --output <bundle>/followup-output
KUBECONFIG=/etc/kubernetes/admin.conf (node-local, not copied)
```

## Per-record dispositions (9 records)
| ID | exit | category | complete | blocked_by |
|---|---|---|---|---|
| F-D1 | 0 | OK | — | — |
| F-I1 | 0 | PARSE_ERROR | false | — |
| F-CS | 0 | UNSUPPORTED | — | — |
| F-CNP | null | BLOCKED_NOT_EXECUTED | — | F-CS |
| F-NP | null | BLOCKED_NOT_EXECUTED | — | F-I1 |
| F-GNP | null | BLOCKED_NOT_EXECUTED | — | F-I1 |
| F-FELIX | null | BLOCKED_NOT_EXECUTED | — | F-I1 |
| F-HEP | null | BLOCKED_NOT_EXECUTED | — | F-I1 |
| F-TIER | null | BLOCKED_NOT_EXECUTED | — | F-I1 |

## Observed facts (not conclusions)
1. **F-D1 OK** — `crd.projectcalico.org/v1` serves 23 resources, including the five required by
   the collector (felixconfigurations, hostendpoints, globalnetworkpolicies, networkpolicies,
   tiers) plus networksets, globalnetworksets, ippools, ipamblocks, bgppeers, bgpconfigurations,
   blockaffinities, bgpfilters, caliconodestatuses, clusterinformations, ipamconfigs,
   ipamhandles, ipreservations, kubecontrollersconfigurations, staged* variants.
2. **F-I1 PARSE_ERROR** — `kubectl get pods -n kube-system -l k8s-app=calico-node -o json`
   returned exit 0 but the collector's typed projection/identity parse failed (PARSE_ERROR,
   empty output). This is a factual disposition and blocks F-NP/F-GNP/F-FELIX/F-HEP/F-TIER.
   (Historical phase-2 I1 was UNSUPPORTED; the current read now returns PARSE_ERROR.)
3. **F-CS UNSUPPORTED** — ClusterNetworkPolicy CRD `v1alpha2` served=true but its projected
   schema SHA256 `ff433d3463dfa2264a7a3ff6201baabf1ec789e98664aff3401a7ef79ae7ce5e` differs from
   the pinned `CNP_SPEC_SHA256=770130a412fd6fab2f02d953edf35f8cc68bf4379db8307e2185937c1e699568`
   → `compatible=false`, blocking F-CNP.

## Remaining UNKNOWN (unchanged)
No effective-policy-union, per-node CNI mode, policy-object presence/absence, tier/HostEndpoint
membership or traffic/directed-flow conclusion is drawn from this run. I1 and CNP schema remain
unresolved as above.

## Returned artifacts + hashes
```text
followup.jsonl  sha256 d977af0cab4d434cf6cdfc1080c8e81abbb620ff5bf98cce025457b8bab78675
run-meta.txt    sha256 ad356bb25850e902d7fade466be753768f8848ef386f25069374e816f2327efe
SHA256SUMS.result (node-generated)
```
Secret scan: none found (resource names/kinds/verbs and CRD metadata/schema hash only; no
kubeconfig, tokens, keys, or raw Kubernetes objects).

## Budget / status
```text
NEW_GATE_RUN_BUDGET=CONSUMED
PHASE2_NEW_RUN_APPROVED=NO (this one run only)
NETPOL_APPROVED_FOR_APPLY=NO
P8C=NOT_FINAL_ACCEPTED
P8D–P8G/P9=NOT_AUTHORIZED
```
STOP for Architect review. No rerun (exit 1 / PARTIAL does not authorize another attempt).
