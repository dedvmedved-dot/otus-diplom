# P8C-R1 RV-02 — complete next-read design (S2)

Date: 2026-10-27. Source-only candidate Gate, NOT authorization. No live reads/collector/apply.
This supersedes the incomplete plan in 03815c8. The immutable registry chain (G2) is preserved.

## ClusterNetworkPolicy — pinned upstream schema
Repository `kubernetes-sigs/network-policy-api` commit `730bd5474d82a2cf82be8b0c6c2a5515598cc44e`
(bundle v0.2.0, standard channel).
- `apis/v1alpha2/clusternetworkpolicy_types.go` blob `8f534d3c92ce0acdce8560d8190ebb574ee4240b`
  (verified: local fetch blob == pin).
- `config/crd/standard/policy.networking.k8s.io_clusternetworkpolicies.yaml` blob
  `eca1eca97c14f56836aaf8f2394fa03479e01b5f` (header identifies v0.2.0/standard).
Cluster-scoped; served at `/apis/policy.networking.k8s.io/v1alpha2/clusternetworkpolicies`
(observed D2). NOT AdminNetworkPolicy; do not reuse the AdminNetworkPolicy projector.

Schema (typed projection candidate):
| Field | Type | Req/opt | Bounds |
|---|---|---|---|
| spec.tier | enum `Admin`/`Baseline` | required | — |
| spec.priority | int32 | required | 0..1000 (lower = higher precedence) |
| spec.subject | exactly one of `namespaces`(LabelSelector) / `pods`(NamespacedPod) | required | MaxProperties=1 |
| spec.ingress[] | IngressRule | optional | MaxItems 25 |
| spec.egress[] | EgressRule | optional | MaxItems 25 |
| rule.name | string | optional | MaxLength 100 |
| rule.action | enum `Accept`/`Deny`/`Pass` | required | — |
| ingress.from[] / egress.to[] | Peer (exactly one field) | required | MinItems 1, MaxItems 25 |
| rule.protocols[] | Protocol | optional | MinItems 1, MaxItems 25 |

Unsupported semantic handling: unknown spec/rule/peer keys → UNSUPPORTED (fail-closed, no silent
drop). Empty `from`/`to`/invalid enum → PARSE_ERROR. `status` (conditions) is non-semantic
observation — projected name/namespace + spec only.

## Complete per-read table
Every proposed read: ID → requirement → existing fact → argv → shape/scope → typed fields →
version pin → deps → categories/limits → FLOW-ID → remains UNKNOWN.

### CNP-1 — ClusterNetworkPolicy (new read)
- Requirement: account for the actually-served ClusterNetworkPolicy kind (D2).
- Existing fact: D2 discovery serves `clusternetworkpolicies` (+/status), cluster-scoped.
- argv: `kubectl --context kubernetes-admin@pak-portal --request-timeout=15s get --raw /apis/policy.networking.k8s.io/v1alpha2/clusternetworkpolicies`
- shape/scope: list, cluster-scoped.
- typed fields: per table above (tier/priority/subject/ingress/egress with rules).
- version pin: network-policy-api commit 730bd547…; apiVersion `policy.networking.k8s.io/v1alpha2`.
- deps: D2 discovery must serve the kind with `list` verb + namespaced=false (cluster-scope).
- categories: [] OK; malformed → PARSE_ERROR; unknown key → UNSUPPORTED; API_NOT_SERVED/FORBIDDEN/
  TIMEOUT/CONNECTION distinct.
- limit: serving the API ≠ objects exist ≠ dataplane enforces; installation provenance (standard vs
  experimental channel) NOT proven from repo/evidence → a sanitized schema-identity preflight
  (validate apiVersion/kind/scope) is the minimal safe first read.
- FLOW-ID: BASELINE.

### CNP-2 — Calico NetworkPolicy (C3, re-run post identity binding)
- argv: `get --raw /apis/crd.projectcalico.org/v1/networkpolicies` (all-ns list).
- deps: D1 (networkpolicies, kind NetworkPolicy, namespaced, get+list) + I1 identity verdict.
- typed fields: existing `project_calico_policy` (NP_SPEC_ALLOWED). FLOW-ID: BASELINE.

### CNP-3 — Calico GlobalNetworkPolicy (C4)
- argv: `get --raw /apis/crd.projectcalico.org/v1/globalnetworkpolicies`.
- deps: D1 (globalnetworkpolicies, cluster-scope) + I1. FLOW-ID: BASELINE.

### CNP-4 — Calico FelixConfiguration (C5)
- argv: `get --raw /apis/crd.projectcalico.org/v1/felixconfigurations/default`.
- deps: D1 (felixconfigurations) + I1. Fields bpfEnabled/nftablesMode/iptablesBackend/nodeSelector.
- limit: default-only; node-specific/env overrides NOT read → effective per-node mode UNKNOWN.
- FLOW-ID: CNI mode.

### CNP-5 — Calico HostEndpoint (new read, bounded)
- requirement: host endpoint policy inputs relevant to node-01/02/03 (target flows terminate at
  Service/DNAT, not directly at host endpoints).
- argv: `get --raw /apis/crd.projectcalico.org/v1/hostendpoints`.
- typed fields: metadata.name/namespace + spec (node, interfaceName, expectedIPs, profiles[]).
- deps: D1 (hostendpoints, namespaced, get+list).
- justification: INCLUDE only to detect host-endpoint selectors that could apply to the target
  nodes; the target flows are pod-to-Service/pod-to-pod, so host-endpoint applicability is
  secondary — record presence, do not model host semantics fully.
- FLOW-ID: BASELINE/CNI.

### CNP-6 — Calico Tier (new read, bounded)
- argv: `get --raw /apis/crd.projectcalico.org/v1/tiers`.
- typed fields: metadata.name + spec.order.
- deps: D1 (tiers, cluster-scope, get+list).
- justification: tier order is needed to interpret Calico policy precedence; only `spec.order` is
  collected (no nested policy content).
- FLOW-ID: BASELINE.

### Excluded (with reason)
- `kubecontrollersconfigurations` — OMITTED: no versioned evidence it supplies the missing
  Felix/DNAT fact; would be a speculative read. Effective DNAT/mode stays UNKNOWN.
- NetworkSet/GlobalNetworkSet/IPPool/BGP* — OUT of scope for target portal/CNPG pod flows.
- `nodes.crd.projectcalico.org` — runtime mode via node CR not proven; keep default Felix only.

### DNAT / enforcement + Barman direction — no new read
Reuse accepted source/design + live identities (S1/S2/C1/C2 + base R2/R3). Dataplane mode,
kube-proxy presence and sidecar→DB/S3 direction remain UNKNOWN; no exec/log/env/args/packet tests
or SSH diagnostics authorized. Record exact UNKNOWN + implication for any future NetPol apply.

## Pagination / completeness limits
All list reads use `--raw` full-list responses; no `limit`/`continue` paging is implemented, so a
truncated list would be indistinguishable from a complete one. A future read must note this limit;
no claim of a complete EFFECTIVE_POLICY_UNION is made from a partial resource set.
