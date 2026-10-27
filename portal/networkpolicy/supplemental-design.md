# P8C RV-02 — supplemental collector design (R4-B, bounded)

Date: 2026-10-27. OFFLINE source design; PHASE2_LIVE_READS_APPROVED=NO.
References: `manifests/barman-cloud/v0.13.0/plugin-barman-cloud-v0.13.0-release.yaml`,
`manifests/barman-cloud/v0.13.0/objectstore-portal-db.yaml`,
`manifests/cnpg/v1.30.1/portal-db-cluster.yaml`,
`ansible/playbooks/files/calico-v3.32.0.yaml` (blob 21ea9b4b16…), base inventory
`evidence/P8/20261026T173244Z-p8c-rv02-live-inventory/inventory.jsonl`.

## 1. Full per-read contract
Each read uses `kubectl --context <ctx> --request-timeout=15s` + argv below. Fixed
`--raw` paths pin the requested API version (no `-o json`, no preferred-version
lookup). Dependencies block dependent reads (BLOCKED_NOT_EXECUTED) when unmet.

| ID | argv tail | Scope | Deps | Shape | Output (typed) | FLOW-ID |
|---|---|---|---|---|---|---|
| D1 | `get --raw /apis/crd.projectcalico.org/v1` | — | — | single | APIResourceList: groupVersion + resources(name,kind,namespaced,verbs) | CNI/policy |
| D2 | `get --raw /apis/policy.networking.k8s.io/v1alpha2` | — | — | single | APIResourceList (unsupported kinds → UNSUPPORTED) | BASELINE |
| I1 | `get pods -n kube-system -l k8s-app=calico-node -o json` | kube-system | — | list | pod containers name/image/imageID/ports/restartPolicy (identity verdict) | CNI identity |
| C1 | `get --raw /apis/barmancloud.cnpg.io/v1/namespaces/portal/objectstores/portal-db-backup` | portal/portal-db-backup | — | single | ObjectStore spec.configuration endpointURL/destinationPath (origin) + secret-ref name/key | BAR/S3 |
| C2 | `get --raw /apis/postgresql.cnpg.io/v1/namespaces/portal/clusters/portal-db` | portal/portal-db | — | single | Cluster spec.plugins[].{name,isWALArchiver,barmanObjectName} + imageName | BAR |
| C3 | `get --raw /apis/crd.projectcalico.org/v1/networkpolicies` | all-ns | D1,I1 | list | NetworkPolicy typed spec (NP_SPEC_ALLOWED) | BASELINE |
| C4 | `get --raw /apis/crd.projectcalico.org/v1/globalnetworkpolicies` | cluster | D1,I1 | list | GlobalNetworkPolicy typed spec (GNP_SPEC_ALLOWED) | BASELINE |
| C5 | `get --raw /apis/crd.projectcalico.org/v1/felixconfigurations/default` | default | D1,I1 | single | FelixConfiguration bpfEnabled/nftablesMode/iptablesBackend/nodeSelector | CNI mode |
| S1 | `get pods -n portal -l cnpg.io/cluster=portal-db -o json` | portal | — | list | pod init/regular containers (per-instance sidecar identity) | BAR sidecar |
| S2 | `get pods -n cnpg-system -l app=barman-cloud -o json` | cnpg-system | — | list | pod containers (plugin controller identity) | BAR plugin |

Projectors/type helpers: D1/D2 → `project_discovery`; I1/S1/S2 → `project_pod_identity`;
C1 → `project_objectstore`; C2 → `project_cluster`; C3/C4 → `project_calico_policy`;
C5 → `project_felix`. Typed leaves via `_str/_nonempty/_bool/_num/_int_range/_enum/
_str_list/_dict/_dict_req/_proto/_ip_version/_icmp/_http/_ports_typed/_sa/_services`.

Required vs optional: a field is **required** when the helper is called with
`allow_none=False` (or `_dict_req`/`_nonempty`); **optional** when `allow_none=True`.
Required-object nesting uses `_dict_req`; optional object uses `_dict` (absent → `{}`).
Normalization: `origin_only()` strips URL userinfo/path/query from endpointURL and
destinationPath; secret refs project name/key only (never values).

Dispositions (distinct categories): missing required field / malformed JSON or type →
**PARSE_ERROR** (empty output, no raw); unknown semantic key → **UnsupportedField** →
UNSUPPORTED; unsupported policy kind → **UnsupportedDiscovery** → UNSUPPORTED; valid-but-
unbound identity → **UnsupportedIdentity** → UNSUPPORTED (safe projected identity
retained); kubectl non-zero → TIMEOUT / FORBIDDEN / API_NOT_SERVED / CONNECTION /
GET_FAILED via `classify()`. `metadata`/`performanceHints` are known non-semantic and
deliberately dropped.

## 2. Digest identity (supported comparison mode)
Supported image references: `quay.io/calico/node@sha256:f4fafd8…` (repository pin,
`ansible/playbooks/files/calico-v3.32.0.yaml`) and tag `quay.io/calico/node:v3.32.0`.
Runtime `imageID` must match `(containerd|docker-pullable|docker)://sha256:<pinned>`
by textual equality. Unsupported representations (repository-qualified imageID, bare
`quay.io/calico/node@sha256:`, arbitrary/unbound/child digests) → UNSUPPORTED with safe
projected identity retained, C3/C4/C5 blocked. Malformed JSON/types → PARSE_ERROR.
Live verification of a platform-child digest relationship is UNKNOWN and out of scope.

## 3. Felix precedence and host/global/tier scope
Source: `ansible/playbooks/files/calico-v3.32.0.yaml` FelixConfiguration CRD — a
cluster-scoped CR named `default`; schema fields include bpfEnabled, nftablesMode,
iptablesBackend and **nodeSelector**. Precedence model: the cluster-default
`default` resource provides the base configuration; `spec.nodeSelector` scopes a
configuration to matching nodes (node-scoped override), and legacy per-node
annotations may also override. The bounded collector reads **only** the `default`
resource (C5), so node-scoped FelixConfiguration, node annotations, and environment
overrides are NOT read — effective per-node mode and the resulting policy-enforcement
union are UNKNOWN and are not inferred from the default alone. No additional reads are
added; uncollected live configuration is marked UNKNOWN.

## 4. Barman directed-flow (pinned v0.13.0)
Per CNPG barman-cloud plugin docs 0.13.0 (concepts/usage: backup/WAL operations execute
in per-instance sidecars — primary or selected standby) and the repository manifests,
four distinct components:

- **CNPG controller/operator** (cnpg-system `cnpg-controller-manager`) — reconciles the
  Cluster CR; invokes the plugin. Observed identity R1.
- **Plugin controller/service** (cnpg-system `barman-cloud` Deployment/Service) — the
  plugin's RPC server. Source: `plugin-barman-cloud-v0.13.0-release.yaml` — Service
  `barman-cloud` port 9090 with annotation `cnpg.io/pluginPort: "9090"`, container arg
  `--server-address=:9090`. This 9090 endpoint is the plugin's server surface invoked by
  CNPG, NOT a per-instance sidecar and NOT a DB/S3 data path. The exact RPC wire
  protocol is not established from the inventory (only the port + server address are
  observed); it is left UNRESOLVED unless a versioned doc states it.
- **Per-instance Barman sidecar** — executes backup/WAL operations inside each PostgreSQL
  pod (primary or selected standby) as an init/sidecar container. Collected by S1
  (`pods -n portal -l cnpg.io/cluster=portal-db`) initContainers/containers identity;
  live identity UNKNOWN (Phase-2 not run).
- **CNPG instance manager** (in-pod, `cnpg.io/podRole=instance`, port 8000 status) —
  manages the local PostgreSQL instance. Observed R1 (port 8000).

Directed interactions (documented design vs observed): the CNPG controller invokes the
plugin server (9090); the per-instance sidecar reads the ObjectStore
(`spec.configuration.endpointURL`, origin) and the local PostgreSQL instance. Pod-local
communication (sidecar↔postgres within a pod) is distinct from inter-Pod policy flows.
Direction and transport (sidecar→DB 5432 vs sidecar→S3 443 vs instance-manager 8000)
are declared, not observed; S3 is NOT assumed to use 443. Declared ports are not
traffic proof.

## 5. API/DNS interpretation (R3 under CNI)
Base inventory R2/R3 observed: API Service `default/kubernetes` 10.96.0.1:443→6443,
EndpointSlice 172.30.140.101/102/103:6443 ready; kube-dns 10.96.0.10:53 (eps
10.244.254.65/.66). Under the Calico CNI (served `crd.projectcalico.org/v1`), Service
ClusterIP is a virtual address whose DNAT to pod endpoints is implemented by the CNI
dataplane (or kube-proxy). The bounded collector does not read the Calico dataplane
mode (iptables/eBPF) or kube-proxy identity, so the actual DNAT/enforcement path is
UNKNOWN and is not inferred from served CRDs. Node podCIDRs (10.244.0/1/2.0/24) ≠
observed pod IPs (10.244.184/190/254.*), so podCIDR is not an allowlist.

## 6. Monitoring / Gateway / policy kinds
- Monitoring: `monitoring.coreos.com` not served (R11-13 API_NOT_SERVED); no Prometheus
  operator/pod observed → "not found in surveyed sources", full absence UNKNOWN.
- Unimplemented optional policy kinds (e.g. AdminNetworkPolicy) → UNSUPPORTED (bounded
  result, not a demand to implement them).
- Future Gateway/dataplane → PLANNED / NOT_CREATED (GatewayClass `eg` present R6; no
  Gateway R7 / EnvoyProxy R8).
