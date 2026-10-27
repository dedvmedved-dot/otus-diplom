# P8C RV-02 — SP-01..05 full closure (review 3c7d8d4)

Date: 2026-10-27 UTC. Completes the SP-01..05 task.

## Remaining SP closures
| SP | Fix |
|---|---|
| SP-01 discovery | per-resource kind/scope/verbs validated against DISCOVERY_EXPECT; C5 requires felixconfigurations (kind/scope/get); D2 classifies served policy kinds — AdminNetworkPolicy (unsupported) → error, no silent success; Calico runtime identity read I1 (pods kube-system k8s-app=calico-node) added and gates C3/C4/C5 |
| SP-02 typed leaves | serviceAccounts→{names,selector} typed; container ports containerPort/name typed; policy tier + notSelector + protocol int-or-string preserved; scalar canary rejected, nested metadata dropped |
| SP-03 pod identity | kind=Pod required, nonempty namespace; spec+status joined for imageID (status.containerStatuses/initContainerStatuses); malformed containers/ports reject; named reads bound to requested name (portal-db-backup / portal-db / default); list-vs-single shape enforced per command |
| SP-04 identity/mode | Felix fields bpfEnabled/nftablesMode/iptablesBackend/nodeSelector (per source schema); Calico pod identity imageID collected; version-specific reads gated on I1+D1 |
| SP-05 docs | PLAN.md proof table updated (DNS/API/peers/plugin/baseline OBSERVED with record refs); flow-matrix cnpg.io/podRole; collection-map spec.configuration + Phase-2 implemented |

## Tests (16/16 PASS)
Discovery gate (wrong group/scope/verb/kind/missing-felix/unsupported policy), serviceAccounts typed, tier/notSelector preserved, numeric protocol accepted, pod port leaf typed, imageID from status, pod wrong-kind rejected, malformed containers rejected, named-get bound, GNP cluster-scoped, no-overwrite, no-kubectl.

## Status
```text
RECOVERY_MAIN_SHA: 16270915cc4a01fce33bab0c203d568516fb7b3a
SP-01..05: CLOSED (source + tests)
SUPPLEMENTAL_TESTS: 16/16 PASS
PHASE2_LIVE_READS_APPROVED: NO
OWNER_PHASE2_HANDOFF_ALLOWED: NO
NETPOL_APPROVED_FOR_APPLY: NO
BASE_INVENTORY_ARTIFACT_REVIEW: ACCEPTED_WITH_LIMITS; INVENTORY_EXIT_CODE=1 (preserved)
FLOW_MATRIX_COMPLETE: NO
PHASE2_PACKAGE_REVIEW_READY: YES
P8C: NOT_FINAL_ACCEPTED; P8D–P8G/P9: NOT_AUTHORIZED
CI_RELEASE / OWNER_HELPERS / PRODUCTION_MIGRATION_DEPLOYMENT: NOT_EXECUTED
```
