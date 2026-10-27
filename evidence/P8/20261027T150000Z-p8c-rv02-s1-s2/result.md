# P8C-R1 RV-02 — S1 identity extension + S2 complete read design

Date: 2026-10-27. Source-only; no cluster access, no live reads.

## S1 — finite Calico identity extension (applied)
`supplemental.py` identity gate now accepts, for image ref `quay.io/calico/node:v3.32.0` /
`@sha256:f4fafd8…`:
- legacy exact prefixed pinned-INDEX digest: `containerd://`/`docker-pullable://`/`docker://`
  + `sha256:f4fafd8…` (preserved, documented as legacy);
- NEW observed bare amd64 CONFIG digest `sha256:6bc9fa4dc2b10ca1d4b97a1cd570036651898cea8b3c3bcbb1d55cf813e43f65`
  (bound to the immutable chain, G2 PROVEN).
Rejected: `containerd://sha256:6bc9fa4…` (config-prefix), bare index digest, arbitrary bare digest,
wrong registry/version; empty/mixed/missing/unidentified stay fail-closed UNSUPPORTED; malformed
stays PARSE_ERROR. D1+I1 still gate C3/C4/C5.

Tests: 36/36 PASS — added `test_identity_config_digest_accepted`,
`test_identity_config_digest_prefix_rejected`, `test_identity_bare_index_rejected`; retained legacy
prefixed-index positive + all prior identity/policy cases.

## S2 — complete next-read design (REVIEW_READY)
`followup-read-design.md` (new evidence dir) — ClusterNetworkPolicy schema pinned to
`kubernetes-sigs/network-policy-api` commit `730bd547…` (types.go blob `8f534d3c…` verified, CRD
`eca1eca9…` bundle v0.2.0/standard): tier(enum Admin/Baseline), priority(0..1000),
subject(namespaces|pods exactly-one), ingress/egress rules(name/action Accept|Deny|Pass,
from/to peers, protocols), with required/optional/bounds. Full per-read table CNP-1..6
(ClusterNetworkPolicy, Calico NetworkPolicy/GlobalNetworkPolicy/Felix, HostEndpoint, Tier) +
excluded reads with reason (`kubecontrollersconfigurations` OMITTED; NetworkSet/IPPool/BGP OUT of
scope) + pagination/completeness limit. No new collector/projector implemented beyond S1.

## S3 — evidence / status
```text
RECOVERY_MAIN_SHA: 69762bf01ae27de2264c8d3d92bac86369f367eb
IDENTITY_CHAIN: VERIFIED (immutable registry chain, preserved)
RUNTIME_IMAGEID_INTERPRETATION: PROVEN (amd64 config digest)
IDENTITY_SOURCE_CHANGE: APPLIED (bare config digest accepted; legacy forms preserved)
FOLLOWUP_READ_DESIGN: REVIEW_READY
PHASE2_NEW_RUN_APPROVED: NO
OWNER_PHASE2_HANDOFF_ALLOWED: NO
NETPOL_APPROVED_FOR_APPLY: NO
P8C: NOT_FINAL_ACCEPTED · P8D–P8G/P9: NOT_AUTHORIZED
```
The 03815c8 partial design is superseded by the new `followup-read-design.md` (historical evidence
left unmodified). The SSH host-key trust path remains a prerequisite for any future live Gate.
STOP.
