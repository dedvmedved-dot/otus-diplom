# P8C RV-02 — supplemental collection map (obligation → command → field → proof/limit)

Each obligation below maps to a specific safe `kubectl get`/`--raw` read in
the base or supplemental collector as explicitly identified, the projected field(s) it produces, and the proof type / limit.
No exec, traffic tests, namespace scans, generic ConfigMap dumps or secrets.

## Base collection (actually executed by inventory.py)

| Obligation (gaps.md) | Command (inventory.py) | Projected field(s) | Proof type / limit |
|---|---|---|---|
| Namespace labels (namespaceSelector) | `get namespaces -o jsonpath` | `.metadata.name`, `.metadata.labels` | OBSERVED_CONFIG; labels only, no annotations |
| Existing NetworkPolicy union | `get networkpolicies -A -o json` (projected) | podSelector/policyTypes/ingress/egress (peers, selectors, ipBlock, ports+endPort) | OBSERVED_CONFIG; kind validated NetworkPolicy; arbitrary spec/status dropped |
| CNPG portal-db peers/operator | `get clusters.postgresql.cnpg.io -A -o json` (projected) | instances, storageSize, walStorageSize, barmanObjectStoreName, monitoring, phase, readyInstances, conditions | OBSERVED_CONFIG + OBSERVED_STATUS; no bootstrap/env/secret data |
| Barman plugin endpoint/port | `get objectstores.barmancloud.cnpg.io -A -o json` (base read `spec.data` — WRONG path; supplemental reads `spec.configuration`) | destinationPath + endpointURL (origin-only), s3Credentials secret-ref | base = NOT_COLLECTED_AT_CORRECT_PATH (R10 all nulls); supplemental spec.configuration correct; plugin→DB direction UNKNOWN |
| Monitoring scrape identity | `get servicemonitors -A` + `get podmonitors -A` + `--raw /apis/monitoring.coreos.com/v1` | selectors, namespaceSelector, endpoint ports/paths | OBSERVED_CONFIG; absence reported as "not found in surveyed sources" |
| Node API/CNI mapping | `get nodes -o jsonpath` (name + `.status.addresses` + `.spec.podCIDRs`) | node name, addresses, podCIDRs | OBSERVED_CONFIG; **NO annotations collected** |
| DNS kube-dns | `get services -A` + `get endpointslices -A` | kube-system/kube-dns Service + EndpointSlices | OBSERVED_CONFIG |
| Kubernetes API destinations | `get services -A` (default/kubernetes) + `get endpointslices -A` | default/kubernetes ClusterIP + endpoint addresses | OBSERVED_CONFIG; DNAT path stays UNKNOWN |
| Envoy GatewayClass/ownership | `get gatewayclasses` + `get gateways -A` + `get envoyproxies -A` (projected) | controllerName, gatewayClassName, listeners, dataplane conditions | OBSERVED_CONFIG + OBSERVED_STATUS; dataplane may be NOT_CREATED_EXPECTED |

## Two-phase discovery → conditional projection plan (live execution NOT approved)

Phase 1 (base, above) discovers WHICH optional/versioned APIs are served. Phase 2
is a SEPARATE targeted read whose projection schema must be defined AND reviewed
against the DISCOVERED version BEFORE it runs — never guessed, never executed now.

## Phase-2 supplemental collector (implemented, OFFLINE-ONLY — NOT approved to run)

The two-phase plan below is now implemented as `supplemental.py` (with
`supplemental_test.py`, accepted 33/33 run reused). PHASE2_LIVE_READS_APPROVED=NO until exact-script
Architect approval. Key corrections vs the earlier NOT_DEFINED plan:
- ObjectStore endpoint is `spec.configuration` (NOT `spec.data`) — projected
  endpointURL/destinationPath origin-only + secret-ref name/key only.
- CNPG plugin mapping is `spec.plugins[].parameters.barmanObjectName` (NOT
  `spec.backup.barmanObjectStore.name`).
- Discovery is a GATE: Calico `crd.projectcalico.org/v1` (D1) must match the
  reviewed groupVersion/resources before Calico policy/mode reads run; otherwise
  dependent reads emit BLOCKED_NOT_EXECUTED (no subprocess call).
- Calico policy/globalpolicy projected selector/order/action/entity(nets,ports)/
  types + host effects only; arbitrary metadata/env dropped; unsupported semantic
  fields are not silently discarded from completeness claims.

| Domain | Discovery read (D#) | Conditional config read (C#/S#) | Projected fields | FLOW-ID |
|---|---|---|---|---|
| CNI/policy (Calico) | P2-D1 `/apis/crd.projectcalico.org/v1` (validated) + P2-I1 calico-node pod identity | P2-C3 NetworkPolicy, P2-C4 GlobalNetworkPolicy, P2-C5 FelixConfiguration | selector/order/action/entity/nets/ports/types + icmp/http/tier + host effects + mode(bpfEnabled/nftablesMode/iptablesBackend) | CNI semantics, BASELINE |
| policy.networking.k8s.io | P2-D2 `/apis/policy.networking.k8s.io/v1alpha2` (validated) | no policy-object read in this contract; nonempty unsupported kinds → UNSUPPORTED | kind-specific | BASELINE |
| Barman plugin mapping | — (bound to reviewed apiVersion) | P2-C1 ObjectStore (spec.configuration), P2-C2 Cluster (spec.plugins) | endpoint origin, secret-ref name/key, plugin name/barmanObjectName/isWALArchiver | BAR-5432, S3-443 |
| Barman sidecar identity | — | P2-S1 pods -n portal -l cnpg.io/cluster=portal-db, P2-S2 pods -n cnpg-system -l app=barman-cloud | initContainers/containers name/image/imageID/ports/restartPolicy (no env/args) | BAR-5432 |
| Monitoring (alternative scrapers) | ServiceMonitor/PodMonitor already checked (base R11-13 = API_NOT_SERVED) | no Prometheus Operator/pod observed; no further read | "not found in surveyed sources" | MON-9187 |
| Gateway/Envoy param refs | `get gatewayclasses` (controllerName) + `get envoyproxies` (conditions) | future design only, NOT one of the ten READ_CONTRACT reads; exact version/fields would require a separate gate | parametersRef name/namespace/kind; EnvoyProxy safe fields TBD per version | embedded bootstrap/config → omitted; NOT executable until defined |

## Explicit limits
- `inventory.py` output is sanitized PROJECTED facts — it does not and cannot
  prove packet DNAT, observed traffic, or CNI enforcement. Those remain UNKNOWN
  without the operator's non-secret CNI configuration + read-only path evidence.
- Future Portal objects (Gateway/dataplane/Portal pods) are PLANNED; not created.
- A single inventory.jsonl resolves config/status facts only; it does not close
  any UNKNOWN row by itself — each row closes on review of its specific record.
- Phase-2 reads are dependencies with an explicit STOP on unknown provider or
  unknown version; they are NOT permissions to dump arbitrary config.

## Source-review reconciliation after 7970620

The exact ten-read contract, dispositions and source-backed interpretation are in
supplemental-design.md. coverage-matrix.md binds actual test IDs and JSON cases to
immutable evidence; no tests were rerun for this documentary correction.
HostEndpoint/Tier, per-node/selector Felix overrides and config/environment are not
collected, so effective policy union/mode remains UNKNOWN. Barman controller TCP9090
is distinct from per-instance backup/WAL sidecars. Source acceptance does not approve
Phase-2 operator handoff, additional reads, policy application or production work.
