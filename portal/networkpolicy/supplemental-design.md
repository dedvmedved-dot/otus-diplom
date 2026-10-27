# P8C RV-02 — supplemental collector design (R4)

Date: 2026-10-27. OFFLINE source design; PHASE2_LIVE_READS_APPROVED=NO.

## API-version pinning (per read)
Each config read is bound to a reviewed apiVersion enforced by the projector's
`_require(apiVersion=...)` (reject on mismatch). Discovery validates the served
groupVersion before dependent reads.

| Read | Resource (GVR) | Pinned apiVersion | Enforced by |
|---|---|---|---|
| C1 | objectstores.barmancloud.cnpg.io | barmancloud.cnpg.io/v1 | project_objectstore |
| C2 | clusters.postgresql.cnpg.io | postgresql.cnpg.io/v1 | project_cluster |
| C3 | networkpolicies.crd.projectcalico.org | crd.projectcalico.org/v1 | project_calico_policy |
| C4 | globalnetworkpolicies.crd.projectcalico.org | crd.projectcalico.org/v1 | project_calico_policy |
| C5 | felixconfigurations.crd.projectcalico.org | crd.projectcalico.org/v1 | project_felix |
| I1/S1/S2 | pods (core) | v1 | project_pod_identity |

## Felix effective-configuration limit
Only the cluster-default FelixConfiguration (`default`) is read (C5). Node-specific
FelixConfiguration, environment overrides and per-node config are NOT read in this
scope; effective per-node mode is therefore UNKNOWN and is not inferred from the
default alone. Fields: bpfEnabled / nftablesMode / iptablesBackend / nodeSelector.

## Calico runtime identity — digest comparison limit
The runtime `imageID` digest is compared to the repository-pinned manifest digest by
textual equality (`containerd://sha256:<pinned>`). This is a source-identity check, not
a proof of runtime provenance: for a multi-platform manifest-list the live imageID may
be a platform-child digest that differs from the pinned manifest-list digest. Such a
child digest is NOT accepted (no textual match, no independent platform verification
available offline) — the gate is intentionally conservative and blocks rather than
accepting an unverified relationship. Live-only verification of platform-child digests
is out of scope and remains UNKNOWN.

## Barman directed-flow limit
The plugin reference (`spec.plugins[].parameters.barmanObjectName=portal-db-backup`) and
the ObjectStore endpoint (`spec.configuration.endpointURL`, origin-only) are collected,
but configuration/declared ports are not observed traffic. The plugin's direction
(plugin→DB 5432 vs plugin→S3 443 vs instance-manager sidecar) remains UNKNOWN and is not
asserted from the declared 9090 service port.
