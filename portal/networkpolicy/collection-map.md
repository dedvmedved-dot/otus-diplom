# P8C RV-02 — supplemental collection map (obligation → command → field → proof/limit)

Each obligation below maps to a specific safe `kubectl get`/`--raw` read in
`inventory.py`, the projected field(s) it produces, and the proof type / limit.
No exec, traffic tests, namespace scans, generic ConfigMap dumps or secrets.

| Obligation (gaps.md) | Command (inventory.py) | Projected field(s) | Proof type / limit |
|---|---|---|---|
| Namespace labels (namespaceSelector) | `get namespaces -o jsonpath` | `.metadata.name`, `.metadata.labels` | OBSERVED_CONFIG; labels only, no annotations |
| Existing NetworkPolicy union | `get networkpolicies -A -o json` (projected) | podSelector/policyTypes/ingress/egress (peer selectors + ipBlock + ports) | OBSERVED_CONFIG; arbitrary spec/status dropped |
| CNPG portal-db peers/operator | `get clusters.postgresql.cnpg.io -A -o json` (projected) | instances, storageSize, barmanObjectStoreName, monitoring, phase, readyInstances, conditions | OBSERVED_CONFIG + OBSERVED_STATUS; no bootstrap/env/secret data |
| Barman plugin endpoint/port | `get objectstores.barmancloud.cnpg.io -A -o json` (projected) | destinationPath, endpointURL (sanitized), s3CredentialsName | OBSERVED_CONFIG; endpoint only, no credentials; plugin SERVICE/DB direction still UNKNOWN |
| Monitoring scrape identity | `get servicemonitors -A` + `get podmonitors -A` + `--raw /apis/monitoring.coreos.com/v1` | selectors, namespaceSelector, endpoint ports/paths | OBSERVED_CONFIG; absence only if API discovery + no CRs observed |
| CNI/proxy mode + DNAT enforcement | `get nodes -o jsonpath` (annotations) + `--raw /apis` | node CNI annotation keys + served API groups | OBSERVED_CONFIG (limited); DNAT enforcement point stays UNKNOWN without CNI non-secret config |
| DNS kube-dns | `get services -A` + `get endpointslices -A` | kube-system/kube-dns Service + EndpointSlices | OBSERVED_CONFIG |
| Kubernetes API destinations | `get services -A` (default/kubernetes) + `get endpointslices -A` | default/kubernetes ClusterIP + endpoint addresses | OBSERVED_CONFIG; DNAT path stays UNKNOWN |
| S3 routing | `get objectstores -A` (endpointURL) | sanitized host:port | OBSERVED_CONFIG; actual CNPG→S3 routing stays UNKNOWN |
| Envoy GatewayClass/ownership | `get gatewayclasses` + `get gateways -A` + `get envoyproxies -A` (projected) | controllerName, gatewayClassName, listeners, dataplane conditions, owning labels | OBSERVED_CONFIG + OBSERVED_STATUS; dataplane may be NOT_CREATED_EXPECTED |

## Explicit limits
- `inventory.py` output is sanitized PROJECTED facts — it does not and cannot
  prove packet DNAT, observed traffic, or CNI enforcement. Those remain UNKNOWN
  without the operator's non-secret CNI configuration + read-only path evidence.
- Future Portal objects (Gateway/dataplane/Portal pods) are PLANNED; not created.
- A single inventory.jsonl resolves config/status facts only; it does not close
  any UNKNOWN row by itself — each row closes on review of its specific record.

## Two-phase discovery → approved projection plan (INV-04 remainder)

Phase 1 (base, already in inventory.py) discovers WHICH optional/versioned APIs
are served. Phase 2 is a separate targeted read whose projection schema is
reviewed against the DISCOVERED version BEFORE it runs — never guessed.

| Domain | Phase-1 discovery | Phase-2 targeted read (conditional) | Non-secret projected fields | STOP condition |
|---|---|---|---|---|
| CNI/proxy mode | `--raw /apis` (served groups) + node annotations are NOT collected; `get nodes` name/addresses/podCIDRs only | CNI config only via the CNI's OWN read-only status/ConfigMap allowlist AFTER provider is identified (e.g. Calico `ippools`/`nodes` status, Cilium `ciliumnodes` status); kube-proxy mode via `get ds kube-proxy -n kube-system -o jsonpath` name/labels only (no args/config dump) | provider kind, proxy mode (iptables/ipvs), dataplane mode, non-secret status fields | unknown provider → STOP, record UNKNOWN |
| CNI-specific policy | `--raw /apis` presence of `projectcalico.org/v3` / `cilium.io/v2` | list the CNI policy CRD (`networkpolicies`/`ciliumnetworkpolicies`) projected to selector/rules only (same allowlist as k8s NetworkPolicy) | selector, ingress/egress peers+ports | CRD absent → API_NOT_SERVED recorded, not failure |
| Barman plugin mapping | `get clusters.postgresql.cnpg.io -A` (projected: barmanObjectStoreName + spec.backup) | `get objectstores.barmancloud.cnpg.io -A` (projected) + the cluster→objectstore name link; plugin Deployment/Service in cnpg-system (`get deploy barman-cloud -n cnpg-system` + `get svc`) | objectStore name, endpointURL/destinationPath (sanitized), plugin pod labels/ports, Service selector+targetPort | link not established by name match → UNKNOWN, do NOT assume legacy 5432 |
| Monitoring scrape identity | `get servicemonitors`/`get podmonitors` + `--raw /apis/monitoring.coreos.com/v1` | if CRDs absent, check alternative scrapers: Prometheus operator pod namespace/labels (`get pods -A` projected labels) + any `prometheus` CR | selector/namespaceSelector/port/path, Prometheus pod identity | no scraper found → "monitoring absent" ONLY with this scoped proof |
| Gateway/Envoy param refs | `get gatewayclasses` (controllerName) + `get envoyproxies` (conditions) | GatewayClass.spec.parametersRef (name/namespace/kind only — no embedded config) + EnvoyProxy.spec (only provider/telemetry/logging toggles, NO bootstrap YAML) | parametersRef name/namespace/kind, safe boolean/level fields | embedded bootstrap/config → omit, do not dump |

Every Phase-2 read is a fixed GET/LIST with a pre-reviewed field allowlist; a
field whose safe schema is unknown until discovery requires a SEPARATE targeted
read definition + review after discovery (an executable dependency, never a
permission to dump arbitrary config).

