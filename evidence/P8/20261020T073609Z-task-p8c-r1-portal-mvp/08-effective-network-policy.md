BLOCKER (G3): portal namespace has NO NetworkPolicy.
P4B-NETWORKPOLICY-BASELINE.md requires default-deny ingress+egress BEFORE first
application workload. Task §6: "Если baseline отсутствует в portal, STOP для
отдельного согласования его безопасного введения с полным existing-flow inventory."
Observed: kubectl -n portal get networkpolicy -> No resources found.
Also envoy-gateway-system has no NetworkPolicy.
Cannot introduce namespace-wide default-deny unilaterally (risk to CNPG).
