# P8C RV-02 — gaps (live-only facts pending read-only inventory)

These are the specific facts that cannot be derived from versioned source and
require the authorized read-only inventory run. Each is keyed to the flow-matrix
FLOW-ID. No traffic/failure tests, no tcpdump, no new privileges.

1. BAR-5432 — Barman plugin: actual namespace (source says cnpg-system, Deployment
   `barman-cloud`, selector `app=barman-cloud`, container TCP9090). The declared
   TCP9090 does NOT establish the plugin→DB direction or DB5432. Need: cnpg-system
   Pods labels/ports, the plugin Service/EndpointSlice, and the plugin's actual
   reconcile/backup path.

2. API-6443 — `default/kubernetes` Service + EndpointSlices, actual API Node
   addresses, CNI mode + service DNAT enforcement point. The candidate
   `172.30.140.0/24:6443` is NOT approved; a `/32` is not substituted blindly.

3. MON-9187 — served `servicemonitors.monitoring.coreos.com` / `podmonitors` +
   actual selectors/namespaces/ports + scrape workload identity (Prometheus Pod
   namespace/labels). Absence is NOT established by CRD discovery alone; check
   alternative scrapers in existing config.

4. DNS-53 — `kube-dns` Service + EndpointSlices + CoreDNS Pod labels, TCP/UDP 53.
   NodeLocalDNS/hostNetwork only if actually detected.

5. S3-443 — sanitized canonical ObjectStore endpoint (host/port, no credentials),
   protocol + permitted routing facts. Velero/Barman credentials/backup paths kept
   separate.

6. ENV-* — GatewayClass / Gateway / EnvoyProxy / dataplane namespace + labels
   (owning-gateway-name AND owning-gateway-namespace). Objects not created →
   NOT_CREATED_EXPECTED; future dependencies are PLANNED from controller baseline +
   versioned candidate manifests.

7. BASELINE — existing NetworkPolicy union cluster-wide + all portal namespace
   workload identities (labels) that a namespace-wide default-deny would isolate.

8. CNI semantics — actual CNI + proxy/replacement mode + enforcement point
   relative to DNAT (read-only, non-secret fields only). Offline Go tests model
   standard Kubernetes NetworkPolicy semantics and are NOT CNI/runtime validation.

Blocked: no authorized kubectl context/kubeconfig reachable from the Hermes host
(see access-path.md). Operator handoff in operator-handoff.md.
