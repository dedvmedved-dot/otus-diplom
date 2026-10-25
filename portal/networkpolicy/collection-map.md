# P8C RV-02 — supplemental collection map (obligation → command → field → proof/limit)

Each obligation below maps to a specific safe `kubectl get`/`--raw` read in
`inventory.py`, the projected field(s) it produces, and the proof type / limit.
No exec, traffic tests, namespace scans, generic ConfigMap dumps or secrets.

## Base collection (actually executed by inventory.py)

| Obligation (gaps.md) | Command (inventory.py) | Projected field(s) | Proof type / limit |
|---|---|---|---|
| Namespace labels (namespaceSelector) | `get namespaces -o jsonpath` | `.metadata.name`, `.metadata.labels` | OBSERVED_CONFIG; labels only, no annotations |
| Existing NetworkPolicy union | `get networkpolicies -A -o json` (projected) | podSelector/policyTypes/ingress/egress (peers, selectors, ipBlock, ports+endPort) | OBSERVED_CONFIG; kind validated NetworkPolicy; arbitrary spec/status dropped |
| CNPG portal-db peers/operator | `get clusters.postgresql.cnpg.io -A -o json` (projected) | instances, storageSize, walStorageSize, barmanObjectStoreName, monitoring, phase, readyInstances, conditions | OBSERVED_CONFIG + OBSERVED_STATUS; no bootstrap/env/secret data |
| Barman plugin endpoint/port | `get objectstores.barmancloud.cnpg.io -A -o json` (projected) | destinationPath + endpointURL (origin-only sanitized), s3CredentialsName | OBSERVED_CONFIG; endpoint origin only; plugin→DB direction still UNKNOWN |
| Monitoring scrape identity | `get servicemonitors -A` + `get podmonitors -A` + `--raw /apis/monitoring.coreos.com/v1` | selectors, namespaceSelector, endpoint ports/paths | OBSERVED_CONFIG; absence reported as "not found in surveyed sources" |
| Node API/CNI mapping | `get nodes -o jsonpath` (name + `.status.addresses` + `.spec.podCIDRs`) | node name, addresses, podCIDRs | OBSERVED_CONFIG; **NO annotations collected** |
| DNS kube-dns | `get services -A` + `get endpointslices -A` | kube-system/kube-dns Service + EndpointSlices | OBSERVED_CONFIG |
| Kubernetes API destinations | `get services -A` (default/kubernetes) + `get endpointslices -A` | default/kubernetes ClusterIP + endpoint addresses | OBSERVED_CONFIG; DNAT path stays UNKNOWN |
| Envoy GatewayClass/ownership | `get gatewayclasses` + `get gateways -A` + `get envoyproxies -A` (projected) | controllerName, gatewayClassName, listeners, dataplane conditions | OBSERVED_CONFIG + OBSERVED_STATUS; dataplane may be NOT_CREATED_EXPECTED |

## Two-phase discovery → conditional projection plan (NOT yet executable)

Phase 1 (base, above) discovers WHICH optional/versioned APIs are served. Phase 2
is a SEPARATE targeted read whose projection schema must be defined AND reviewed
against the DISCOVERED version BEFORE it runs — never guessed, never executed now.

| Domain | Phase-1 discovery | Phase-2 (conditional, NOT_DEFINED until version confirmed) | Non-secret projected fields (to be defined) | STOP / status |
|---|---|---|---|---|
| CNI/proxy mode | `--raw /apis` + node name/addresses/podCIDRs (no annotations) | CNI's OWN read-only status/CRD allowlist AFTER provider is identified; kube-proxy DaemonSet name/labels are identity-only and do NOT establish proxy mode | provider kind, proxy mode — fields defined per discovered version | unknown provider → STOP/UNKNOWN; proxy mode NOT inferred from name/labels |
| CNI-specific policy | `--raw /apis` presence of `projectcalico.org/v3` / `cilium.io/v2` | list CNI policy CRD with a version-specific projection | NOT_DEFINED — k8s NetworkPolicy allowlist is NOT assumed identical | CRD absent → API_NOT_SERVED; otherwise a separate projection definition is required |
| Barman plugin mapping | `get clusters…` (barmanObjectStoreName) + `get objectstores…` (projected) | cluster plugin identity/parameters → ObjectStore reference → plugin Service/port, each projected per version | plugin name, ObjectStore ref, Service selector/targetPort | link not established → UNKNOWN; legacy name match is NOT assumed |
| Monitoring (alternative scrapers) | ServiceMonitor/PodMonitor + `--raw /apis` | if CRDs absent, conditional read of Prometheus operator pod identity + any `prometheus` CR | selector/namespace/port/path, Prometheus pod identity | "not found in surveyed sources" is the only absence claim; full absence stays UNKNOWN |
| Gateway/Envoy param refs | `get gatewayclasses` (controllerName) + `get envoyproxies` (conditions) | GatewayClass.parametersRef + EnvoyProxy.spec fields as a conditional read requiring exact version/field definition | parametersRef name/namespace/kind; EnvoyProxy safe fields TBD per version | embedded bootstrap/config → omitted; NOT executable until defined |

## Explicit limits
- `inventory.py` output is sanitized PROJECTED facts — it does not and cannot
  prove packet DNAT, observed traffic, or CNI enforcement. Those remain UNKNOWN
  without the operator's non-secret CNI configuration + read-only path evidence.
- Future Portal objects (Gateway/dataplane/Portal pods) are PLANNED; not created.
- A single inventory.jsonl resolves config/status facts only; it does not close
  any UNKNOWN row by itself — each row closes on review of its specific record.
- Phase-2 reads are dependencies with an explicit STOP on unknown provider or
  unknown version; they are NOT permissions to dump arbitrary config.
