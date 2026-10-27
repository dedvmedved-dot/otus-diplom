# P8C-R1 RV-02 — follow-up read design (G3, source-only candidate)

Date: 2026-10-27. This is a CANDIDATE future Gate, NOT an authorization. No live reads,
no collector, no apply. Each row: requirement → existing fact → UNKNOWN → new read →
argv/GVR → safe typed fields → version pin → deps → output/error → FLOW-ID.

## A. Calico policy reads (C3/C4/C5) after identity binding
- **Requirement**: effective Calico NetworkPolicy/GlobalNetworkPolicy/Felix for the portal flows.
- **Existing fact**: D1 serves `networkpolicies`/`globalnetworkpolicies`/`felixconfigurations` (v1);
  I1 runtime imageID `sha256:6bc9fa4…` = amd64 config digest of pinned manifest-list (G2 PROVEN).
- **UNKNOWN**: actual policy objects + effective mode (blocked by identity gate).
- **New read**: C3/C4/C5 with the SAME argv (already in READ_CONTRACT), gated on a corrected
  identity verdict (candidate contract below), not on manifest-list digest equality.
- **Candidate identity contract (for Architect review, NOT implemented)**:
  - image reference: `quay.io/calico/node@sha256:f4fafd8…` OR `quay.io/calico/node:v3.32.0`;
  - runtime imageID: accept bare `sha256:6bc9fa4dc2b10ca1d4b97a1cd570036651898cea8b3c3bcbb1d55cf813e43f65`
    (amd64 config digest) or `containerd://…`/`docker-pullable://…` prefixed form;
  - the config digest is pre-computed from the pinned manifest-list (offline), NOT looked up at
    runtime and NOT the mutable tag.
- **Note**: imageID `6bc9fa4…` ≠ manifest-list digest; the prior `endswith(PINNED_DIGEST)` +
  `IMAGE_ID_RE` reject it for the wrong reason. No code change is made in this package.

## B. ClusterNetworkPolicy (policy.networking.k8s.io/v1alpha2)
- **Requirement**: account for the actually-served ClusterNetworkPolicy kind (D2 discovery), not
  AdminNetworkPolicy.
- **Existing fact**: D2 serves `clusternetworkpolicies` + `/status` (cluster-scoped).
- **UNKNOWN**: official schema/semantics for K8s v1.36.2, whether any object exists, whether the
  dataplane enforces it.
- **New read (future)**: `get --raw /apis/policy.networking.k8s.io/v1alpha2/clusternetworkpolicies`
  (list) + a NEW projector bound to the official v1alpha2 schema; do NOT reuse the AdminNetworkPolicy
  fixture. Fields to be defined from the official OpenAPI for v1.36.2 (targeted projection, no raw).
- **Version pin**: official `k8s.io/api` / `sigs.k8s.io/network-policy-api` v1alpha2 source for v1.36.2.

## C. HostEndpoint / Tier / other D1 policy inputs
- **Requirement**: bounded scope for target portal/CNPG flows.
- **Existing fact**: D1 serves `hostendpoints`, `tiers`, `ippools`, `networksets`,
  `globalnetworksets`, `staged*` etc.
- **UNKNOWN**: whether any HostEndpoint/Tier applies to the portal/CNPG flows; effective precedence.
- **New read (future)**: `get --raw /apis/crd.projectcalico.org/v1/hostendpoints` and `/tiers`
  (cluster-scoped), typed selector/labels/order projection; evaluate applicability to node-01/02/03
  and portal/CNPG namespaces. Do NOT promise full EFFECTIVE_POLICY_UNION from a partial resource set.
- **Limit**: even with C3/C4/C5 + HostEndpoint/Tier, DNAT/enforcement + actual traffic remain UNKNOWN.

## D. DNAT / enforcement + Barman directed-flow
- **Requirement**: service DNAT enforcement point + Barman direction.
- **Existing fact**: API Service 10.96.0.1:443→6443 + eps (base R2/R3); Calico v1 served; S1/S2
  sidecar/controller identity (Phase-2).
- **UNKNOWN**: dataplane mode (iptables/eBPF), kube-proxy presence, actual DNAT path; sidecar→DB vs
  sidecar→S3 direction.
- **New read (future, only if a safe source exists)**: Calico `felixconfigurations/default` (already
  C5) + `kubecontrollersconfigurations` + node-specific overrides; NO exec/log/env/args/packet
  tests/SSH diagnostics are authorized. If the fact cannot be obtained safely in this scope →
  UNKNOWN with a precise blocker, no repeated inventory loop.

## FLOW-ID mapping
C3/C4/C5 → BASELINE; ClusterNetworkPolicy → BASELINE; HostEndpoint/Tier → BASELINE/CNI;
Felix/kube-controllers → CNI mode; DNAT → API-6443/DNS-53; Barman direction → BAR-5432/S3-443.
