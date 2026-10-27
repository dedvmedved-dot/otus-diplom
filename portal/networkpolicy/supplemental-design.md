# P8C RV-02 — supplemental collector design (R4-B, bounded)

Date: 2026-10-27. Architect documentary reconciliation after 7970620.
OFFLINE source design; PHASE2_LIVE_READS_APPROVED=NO.
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

Required/optional behavior is defined by the reviewed code at
b623afb2fa9fd624e3e1ff418adeb9c71b1074df (supplemental.py blob
ad2edaa92de59f657599190842fa7fe68373b582), not by a guessed universal schema:
- Scalar helpers reject wrong types; `allow_none=True` explicitly permits absent/null.
  `_nonempty` also checks empty strings; its own allow_none argument still matters.
- `_dict_req` requires an object; `_dict` maps absent/null to an empty object.
  `_str_list`, `_ports_typed` and `_container_ports` map absent/null to an empty list.
- `project_discovery` requires APIResourceList, groupVersion and a resources list;
  resource name/kind/namespaced have typed checks; verbs normalizes through
  `_str_list`. D1 then enforces DISCOVERY_EXPECT; D2 classifies unsupported kinds.
- `project_pod_identity` requires Pod/v1, name, requested namespace and spec object.
  Init/regular container lists are optional; present containers require names.
  Image/imageID/restartPolicy are nullable strings; imageID is joined from status.
  Present container ports require integer 1..65535. I1 additionally applies the
  exact admission contract; S1/S2 only collect identity.
- `project_objectstore` requires named portal identity, spec and configuration.
  Endpoint origins are normalized by `origin_only`; missing/invalid origins become
  null, not proof that no live endpoint exists. Present S3 refs require name; key
  is nullable in this bounded projection. Only reference names/keys are emitted.
- `project_cluster` requires named portal identity and spec; absent plugins become
  an empty list. Present plugins require string name; isWALArchiver,
  barmanObjectName and imageName are nullable typed values.
- `project_calico_policy` requires exact kind/API/scope and spec; NP_SPEC_ALLOWED,
  GNP_SPEC_ALLOWED and nested RULE/ENTITY/HTTP/HTTP_PATH/ICMP/SA/SERVICES_ALLOWED
  are the finite semantic contracts. Unknown semantic fields cause UNSUPPORTED.
  Known metadata/performanceHints are dropped. Nullable scalars and absent lists
  normalize only as implemented by the named helpers; this is not full CRD validation.
- `project_felix` requires FelixConfiguration/v1, name default and spec;
  bpfEnabled is nullable bool, nftablesMode nullable enum Disabled/Enabled/Auto,
  iptablesBackend/nodeSelector nullable strings. It does not calculate effective mode.

Dispositions: missing required field, malformed JSON/type or wrong identity binding
gives PARSE_ERROR and empty output. UnsupportedField gives UNSUPPORTED without raw
object output. UnsupportedDiscovery and UnsupportedIdentity retain only the completed
safe projection. Unsupported I1 blocks C3/C4/C5 with zero calls. Subprocess failures
retain distinct TIMEOUT/FORBIDDEN/API_NOT_SERVED/CONNECTION/GET_FAILED categories;
unmet dependencies produce BLOCKED_NOT_EXECUTED. Any failure/unsupported/blocked row
makes the aggregate result nonzero. Raw stdout/stderr and arbitrary exception text
are never written. Read argv is fixed by READ_CONTRACT; no new read is authorized.

## 2. Digest identity (supported comparison mode)
Supported image references: `quay.io/calico/node@sha256:f4fafd8…` (repository pin,
`ansible/playbooks/files/calico-v3.32.0.yaml`) and tag `quay.io/calico/node:v3.32.0`.
Runtime `imageID` must match `(containerd|docker-pullable|docker)://sha256:<pinned>`
by textual equality. Unsupported representations (repository-qualified imageID, bare
`quay.io/calico/node@sha256:`, arbitrary/unbound/child digests) → UNSUPPORTED with safe
projected identity retained, C3/C4/C5 blocked. Malformed JSON/types → PARSE_ERROR.
Live verification of a platform-child digest relationship is UNKNOWN and out of scope.

## 3. Felix precedence and host/global/tier scope

Exact-version primary source:
[Calico v3.32.0 config_params.go](https://github.com/projectcalico/calico/blob/eb1cf57823a1dd8d25c48b82fd023ea9e3e17996/felix/config/config_params.go),
blob 72676f76f3bdd5f592e29313c712b159db0bcd2e, Source/SourcesInDescendingOrder/resolve.
The configured priority is environment, configuration file, per-host datastore,
selector-scoped datastore, global datastore, then built-in defaults. InternalOverride
is an additional highest-priority implementation mechanism, not a new user read.
The resolver also respects local-only parameters; a datastore value cannot override
that restriction.

The repository Calico manifest, blob 21ea9b4b163305ea479bc7708965104465ffc716,
FelixConfiguration schema `spec.nodeSelector.description`, establishes:
- `default` is global and cannot use nodeSelector.
- `node.<nodename>` is per-node and cannot use nodeSelector.
- Other names can use nodeSelector. If several selectors match, the oldest matching
  object is selected, with a warning. This selector conflict rule is distinct from
  the configuration source priority above.

C5 reads only default. It does not read per-node/selector-scoped configurations,
Felix configuration files, process environment or internal overrides. Therefore the
effective per-node mode remains UNKNOWN. The earlier generic annotation-override
claim is withdrawn: no such precedence source was established for this contract.
The projector retaining a nullable nodeSelector does not make that field valid on
a real default object; this collector is not an admission validator.

C3 projects namespaced policies; C4 projects GlobalNetworkPolicy and its supported
host-related flags, selectors and tier reference. Neither read collects HostEndpoint
or Tier objects, resolves selector membership or evaluates a policy engine.
Consequently global-policy configuration is observable, but host-policy applicability,
tier ordering and EFFECTIVE_POLICY_UNION remain UNKNOWN. These are explicit coverage
limits; adding HostEndpoint/Tier/config/env reads is not authorized.

## 4. Barman directed-flow (pinned v0.13.0)
Primary design reference: [Barman plugin 0.13.0 concepts](https://cloudnative-pg.io/plugin-barman-cloud/docs/0.13.0/concepts/),
section Backup of a Postgres Cluster: backup/WAL execution is in the per-instance
sidecar on the primary or selected standby. Configuration mapping is documented in
[0.13.0 usage](https://cloudnative-pg.io/plugin-barman-cloud/docs/0.13.0/usage/).
Repository references: release manifest blob 4fa292cd8f89808d96f6d90af826afd31afa29ec,
ObjectStore blob 07709428317922b7789a7b6c22bf9b88b5dc9a03, Cluster blob
e60a92353194fda60f34dacb56273ed7048af14c. These are source configuration, not new live reads.
Four distinct components:

- **CNPG controller/operator** (cnpg-system `cnpg-controller-manager`) — reconciles the
  Cluster CR; invokes the plugin. Observed identity R1.
- **Plugin controller/service** (cnpg-system `barman-cloud` Deployment/Service) — the
  plugin's RPC server. Source: `plugin-barman-cloud-v0.13.0-release.yaml` — Service
  `barman-cloud` port 9090 with annotation `cnpg.io/pluginPort: "9090"`, container arg
  `--server-address=:9090`. This 9090 endpoint is the plugin's server surface invoked by
  CNPG, NOT a per-instance sidecar and NOT a DB/S3 data path. The release manifest establishes TCP9090 and TLS server/client certificate arguments;
  it does not by itself identify the RPC framing. Wire protocol is UNRESOLVED in this
  bounded evidence and must not be mislabeled as an HTTP webhook. Observed service
  identity does not prove current peer traffic.
- **Per-instance Barman sidecar** — executes backup/WAL operations inside each PostgreSQL
  pod (primary or selected standby) as an init/sidecar container. Collected by S1
  (`pods -n portal -l cnpg.io/cluster=portal-db`) initContainers/containers identity;
  live identity UNKNOWN (Phase-2 not run).
- **CNPG instance manager** (in-pod, `cnpg.io/podRole=instance`, port 8000 status) —
  manages the local PostgreSQL instance. Observed R1 (port 8000).

Directed design separates the CNPG operator-to-plugin control endpoint TCP9090
from per-instance backup/WAL work and object-store communication. The sidecar shares
a Pod network namespace with PostgreSQL; no new inter-Pod TCP5432 permission follows
merely from that relationship. Its exact local database/instance-manager IPC transport
is not captured by the approved reads and remains UNRESOLVED.

The source ObjectStore declares HTTPS endpoint `s3-backup.demo-pak.test` with no
explicit port (source design uses the HTTPS default); this is not live routing/IP or
packet evidence. Live endpoint origin still requires C1 because base R10 used the
wrong projection path. No live S3 port/IP allowlist is approved. R1/R2/R3 capture
identities and declared ports only; actual directed traffic remains UNKNOWN.

## 5. API/DNS interpretation (R3 under CNI)

Base inventory R2/R3: API Service 10.96.0.1:443, endpoints
172.30.140.101/102/103:6443; DNS Service 10.96.0.10:53, endpoints
10.244.254.65/.66. The API endpoints are node addresses, not assumed Pod IPs.

[Kubernetes 1.36 virtual IP documentation](https://v1-36.docs.kubernetes.io/docs/reference/networking/virtual-ips/)
describes Service forwarding by kube-proxy or its replacement to endpoint addresses.
[Kubernetes 1.36 NetworkPolicy documentation](https://v1-36.docs.kubernetes.io/docs/concepts/services-networking/network-policies/)
leaves address-rewrite order relative to policy processing implementation-dependent.
Thus both Service and endpoint facts are retained; neither alone proves which
destination an ipBlock rule sees. Served Calico CRDs are not proof of active
iptables/eBPF/nftables mode, proxy replacement or enforcement order.
C5 observes only global defaults; section 3 explains why effective settings are
unresolved. Actual DNAT/enforcement remains UNKNOWN and must be resolved before apply.
Node podCIDRs 10.244.0/1/2.0/24 differ from observed Pod IP ranges
10.244.184/190/254.*; they are not a validated egress allowlist.

## 6. Monitoring / Gateway / policy kinds
- Monitoring: `monitoring.coreos.com` not served (R11-13 API_NOT_SERVED); no Prometheus
  operator/pod observed → "not found in surveyed sources", full absence UNKNOWN.
- Unimplemented optional policy kinds (e.g. AdminNetworkPolicy) → UNSUPPORTED (bounded
  result, not a demand to implement them).
- Future Gateway/dataplane → PLANNED / NOT_CREATED (GatewayClass `eg` present R6; no
  Gateway R7 / EnvoyProxy R8).
