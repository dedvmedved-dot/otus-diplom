# P8C RV-02 — supplemental collector design (R4-B, bounded)

Date: 2026-10-27. OFFLINE source design; PHASE2_LIVE_READS_APPROVED=NO.
References: repository manifests under `manifests/`, Calico pin
`ansible/playbooks/files/calico-v3.32.0.yaml` (blob 21ea9b4b16…), base inventory
`evidence/P8/20261026T173244Z-p8c-rv02-live-inventory/inventory.jsonl`.

## 1. Full per-read contract
Each read uses `kubectl --context <ctx> --request-timeout=15s` + argv below. Fixed
`--raw` paths pin the requested API version (no `-o json`, no preferred-version
lookup). Dependencies block dependent reads (BLOCKED_NOT_EXECUTED) when unmet.

| ID | argv tail | Scope | Deps | Shape | Output fields (typed) | FLOW-ID |
|---|---|---|---|---|---|---|
| D1 | `get --raw /apis/crd.projectcalico.org/v1` | — | — | single | APIResourceList: groupVersion + resources(name,kind,namespaced,verbs) | CNI/policy |
| D2 | `get --raw /apis/policy.networking.k8s.io/v1alpha2` | — | — | single | APIResourceList (unsupported kinds → UNSUPPORTED) | BASELINE |
| I1 | `get pods -n kube-system -l k8s-app=calico-node -o json` | kube-system | — | list | pod containers name/image/imageID/ports/restartPolicy (identity verdict) | CNI identity |
| C1 | `get --raw /apis/barmancloud.cnpg.io/v1/namespaces/portal/objectstores/portal-db-backup` | portal/portal-db-backup | — | single | ObjectStore spec.configuration endpointURL/destinationPath (origin) + secret-ref name/key | BAR/S3 |
| C2 | `get --raw /apis/postgresql.cnpg.io/v1/namespaces/portal/clusters/portal-db` | portal/portal-db | — | single | Cluster spec.plugins[].{name,isWALArchiver,barmanObjectName} + imageName | BAR |
| C3 | `get --raw /apis/crd.projectcalico.org/v1/networkpolicies` | all-ns | D1,I1 | list | NetworkPolicy typed spec (NP_SPEC_ALLOWED) | BASELINE |
| C4 | `get --raw /apis/crd.projectcalico.org/v1/globalnetworkpolicies` | cluster | D1,I1 | list | GlobalNetworkPolicy typed spec (GNP_SPEC_ALLOWED) | BASELINE |
| C5 | `get --raw /apis/crd.projectcalico.org/v1/felixconfigurations/default` | default | D1,I1 | single | FelixConfiguration bpfEnabled/nftablesMode/iptablesBackend/nodeSelector | CNI mode |
| S1 | `get pods -n portal -l cnpg.io/cluster=portal-db -o json` | portal | — | list | pod init/regular containers (native sidecar identity) | BAR sidecar |
| S2 | `get pods -n cnpg-system -l app=barman-cloud -o json` | cnpg-system | — | list | pod containers (barman-cloud plugin identity) | BAR plugin |

Error handling: TIMEOUT / FORBIDDEN / API_NOT_SERVED / CONNECTION / GET_FAILED /
PARSE_ERROR (malformed JSON) / UNSUPPORTED (unknown semantic field or unsupported
policy kind) are distinct categories; raw stdout/stderr never persisted.

## 2. Digest identity (supported comparison mode)
Supported image references: `quay.io/calico/node@sha256:f4fafd8…` (repository pin,
`ansible/playbooks/files/calico-v3.32.0.yaml`) and its tag form
`quay.io/calico/node:v3.32.0`. Runtime `imageID` must match
`(containerd|docker-pullable|docker)://sha256:<pinned-digest>` by textual equality.
Unsupported runtime representations (repository-qualified imageID, bare
`quay.io/calico/node@sha256:`, arbitrary or platform-child digests with no reviewed
relationship) are rejected/blocked — no new accepted format. Live-only verification of
a platform-child digest relationship is UNKNOWN and out of scope; the gate is
conservative (block rather than accept an unverified digest).

## 3. Felix effective-configuration limit
Only the cluster-default `FelixConfiguration/default` is read (C5). Node-specific
FelixConfiguration, per-node config/env overrides and applied precedence are NOT read
in this scope; effective per-node mode is UNKNOWN and never inferred from the default
alone. Fields: bpfEnabled (bool), nftablesMode (Disabled/Enabled/Auto), iptablesBackend
(string), nodeSelector (string). Source: Calico v3.32 FelixConfiguration CRD schema.

## 4. Barman directed-flow (pinned v0.13.0)
Three distinct roles, per `manifests/barman-cloud/v0.13.0/` + CNPG v1.30.1:
- **controller** (cnpg-system `cnpg-controller-manager`) — reconciles Cluster, invokes
  plugin for backup/restore; observed identity R1/R3.
- **instance manager** (in-cluster `cnpg.io/podRole=instance`) — runs backup/WAL jobs
  inside the cluster pod; port 8000 status.
- **native sidecar / plugin** (`barman-cloud.cloudnative-pg.io`, pluginName in R3,
  svc 9090) — referenced via Cluster `spec.plugins[].parameters.barmanObjectName` =
  `portal-db-backup`; the ObjectStore endpoint is `spec.configuration.endpointURL`.
Directed ports are DECLARED, not observed traffic: plugin→DB(5432) vs plugin→S3(443)
vs instance-manager(8000) direction remains UNKNOWN; the 9090 service port alone does
not establish direction.

## 5. API/DNS interpretation (R3 under CNI)
Base inventory R2/R3 observed: API Service `default/kubernetes` 10.96.0.1:443→6443,
EndpointSlice 172.30.140.101/102/103:6443 ready; kube-dns 10.96.0.10:53 (eps
10.244.254.65/.66). Under the Calico CNI (served `crd.projectcalico.org/v1`), the
Service DNAT/endpoint-enforcement path is NOT read in this scope — enforcement/DNAT
remains UNKNOWN. Node podCIDRs (10.244.0/1/2.0/24) ≠ observed pod IPs
(10.244.184/190/254.*), so podCIDR is not an allowlist.

## 6. Monitoring / Gateway / policy kinds
- Monitoring: `monitoring.coreos.com` not served (R11-13 API_NOT_SERVED); no Prometheus
  operator/pod observed → "not found in surveyed sources", full absence UNKNOWN.
- Unimplemented optional policy kinds (e.g. AdminNetworkPolicy) → UNSUPPORTED (bounded
  result, not a demand to implement them).
- Future Gateway/dataplane → PLANNED / NOT_CREATED (GatewayClass `eg` present R6; no
  Gateway R7 / EnvoyProxy R8).
