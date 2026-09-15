# Remediation options (analysis only, NOT executed)

| Candidate | Supported | Minimal | Persistent | Blast radius | Recommended |
|---|---|---|---|---|---|
| NodeConnection same-value re-push (controller-side re-send to satellites) | YES (LINSTOR API/CLI) | YES | depends on trigger | controller->satellite sync for node-01/03 | **YES (primary)** |
| PrefNic = drbd141 (workaround) | YES (node property) | partial | YES but indirect | node-level, all DRBD | fallback only |
| ResourceConnection explicit Paths | YES (per-resource) | no (per-resource) | YES | per-resource | alternative |
| Satellite restart | partial (proven insufficient in P7C) | no | no | runtime | no |
| DRBD path reset (del-path/new-path/adjust) | YES but wrong layer | no | no | runtime | no |
| Upgrade LINSTOR 1.33.2->1.33.3 | plausible | no (upgrade) | YES | whole LINSTOR | consider after evidence |

Recommended: re-push NodeConnection Paths drbd141 to node-01/node-03 satellites
via supported LINSTOR controller API/CLI, with pre/post generated .res evidence
and no quorum/topology change. Requires separate Architect authorization.
LinstorSatelliteConfiguration.spec.interfaces is ABSENT (do not use).
