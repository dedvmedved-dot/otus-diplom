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
