# P8C RV-02 — live inventory ingest, integrity verification, reconciliation

Date: 2026-10-26 UTC. Operator evidence ingested from GitHub main.

## G0 — recovery
```text
RECOVERY_MAIN_SHA: 137bb29d64ae8571484043fc26ba3cd2cda16234  (origin/main, ff)
Operator commit: 137bb29d (3ae321a..137bb29) — evidence/P8/20261026T173244Z-p8c-rv02-live-inventory/{inventory.jsonl,result.md}
```

## Integrity verification (actual)
| Check | Result |
|---|---|
| inventory.jsonl SHA-256 == bc692fc8…44f41 | ✅ MATCH |
| Script SHA-256 == 7806f494…88a2 (pinned) | ✅ MATCH |
| Script git blob == 5f0e2450… (source 9a98b385) | ✅ MATCH |
| JSONL valid (every line parses) | ✅ 15/15 |
| Records: 12 exit=0 (category null) + 3 API_NOT_SERVED (exit=1) | ✅ CONFIRMED (0 other) |
| EXIT=1 (3 API_NOT_SERVED preserved, NOT relabeled PASS) | ✅ CONFIRMED |
| Timestamps | START 2026-10-26T17:32:44.6Z → END 17:32:47.5Z |
| Context / client / server | kubernetes-admin@pak-portal / v1.36.2 / v1.36.2 |
| argv composition | 15 commands all `kubectl --context … --request-timeout=15s get …`; `--raw` on discovery |
| Secret scan (content, not keyword-grep) | token=/password=/Bearer=/userinfo-URL=/private-key/AKIA → 0 matches |

## Reconciliation — 14 FLOW-IDs against observations
| FLOW-ID | Observed (record) | Result |
|---|---|---|
| REP-5432 | portal-db-1/2/3 pods `cnpg.io/cluster=portal-db, podRole=instance` port 5432; svc portal-db-r/ro/rw→5432 (R1,R2) | CONFIRMED (config) |
| IM-8000 | instance pods port 8000 `status` (R1) | CONFIRMED (config) |
| OP-IM-8000 | cnpg-controller-manager (cnpg-system) + instance 8000 (R1) | CONFIRMED (identity+port; dir=VERSIONED_DESIGN) |
| BAR-5432 | barman-cloud pod+svc cnpg-system TCP 9090 (R1,R2); cluster backup conditions True (R9) | PARTIAL — plugin=9090, but plugin→DB/S3 direction UNKNOWN |
| MON-9187 | monitoring.coreos.com NOT served (R11-13); no Prometheus/Grafana pod; only metrics-server (R1,R2); cluster monitoring=false (R9) | NOT FOUND in surveyed sources (9187 exposed, no scraper) |
| DNS-53 | kube-dns 10.96.0.10, UDP+TCP 53 (R2) | CONFIRMED |
| API-6443 | default/kubernetes 10.96.0.1:443→6443 (R2); node IPs 172.30.140.10x (R15) | PARTIAL — Service confirmed; DNAT/CNI point UNKNOWN |
| S3-443 | ObjectStore portal-db-backup: endpointURL/destinationPath/s3CredentialsName all null (R10); cluster barmanObjectStoreName null (R9) | UNKNOWN — inline backup endpoint not projected |
| APP-DB-5432 | no pak-portal pods (Portal not deployed) (R1) | PLANNED (NOT_CREATED) |
| APP-MET-9187 | same | PLANNED (NOT_CREATED) |
| MIG-DB-5432 | no migrator pod | PLANNED (NOT_CREATED) |
| ENV-XDS-18000 | envoy-gateway control-plane pod+svc grpc 18000 (R1,R2); GatewayClass "eg" (R6); NO Gateway/EnvoyProxy (R7,R8) | PLANNED — dataplane NOT_CREATED; control-plane 18000 confirmed |
| ENV-BACK-8080 | Portal + dataplane not created | PLANNED (NOT_CREATED) |
| ENV-LISTENER | dataplane not created | PLANNED (NOT_CREATED) |

## 8 gaps — status after observation
1. BAR-5432 → STILL UNKNOWN (plugin direction + inline S3 endpoint; Phase-2 read needed).
2. API-6443 → PARTIAL (Service 10.96.0.1:443→6443; DNAT/CNI enforcement UNKNOWN).
3. MON-9187 → "not found in surveyed sources" (no Prometheus Operator/Prometheus; metrics-server only).
4. DNS-53 → RESOLVED (kube-dns 10.96.0.10:53 UDP+TCP).
5. S3-443 → STILL UNKNOWN (endpoint null in projection; inline backup config not captured).
6. ENV-* → RESOLVED as NOT_CREATED (control-plane only; GatewayClass "eg"; no dataplane).
7. BASELINE → RESOLVED (networkpolicies=[] → union EMPTY; namespaces catalogued).
8. CNI semantics → PARTIAL (Calico identified via `crd.projectcalico.org`; mode/policies/DNAT UNKNOWN).

## Phase-2 reads (prepared for separate Architect review — NOT executed)
See `portal/networkpolicy/collection-map.md` (two-phase plan). Concretely, after
discovery identifies Calico + inline CNPG backup:
1. Calico version + policies: `get --raw /apis/crd.projectcalico.org/v1` →
   `get networkpolicies.crd.projectcalico.org -A -o json` (project selector/rules
   only) + node Calico status (mode iptables/eBPF), non-secret.
2. CNPG inline backup endpoint: read `Cluster portal-db` `spec.backup.barmanObjectStore`
   with a NEW projection (sanitize endpointURL → origin only; s3Credentials → secretRef
   NAME only; no inline credentials). ObjectStore `portal-db-backup` full `spec.data`
   same projection. barman-cloud Deployment container spec (ports only).
3. API DNAT: `default/kubernetes` EndpointSlice addresses (already R3) + Calico DNAT
   mode confirmation (non-secret).

## Status fields
```text
RV02_BASE_INVENTORY: PARTIAL (12 OK + 3 API_NOT_SERVED, EXIT=1 preserved)
NETPOL_LIVE_INVENTORY: EXECUTED (base read-only; PARTIAL)
INVENTORY_EXIT_CODE: 1
FLOW_MATRIX_COMPLETE: NO (some rows resolved, others UNKNOWN/PLANNED)
REMAINING_UNKNOWNS: Barman plugin direction + S3 inline endpoint, API DNAT/CNI
  enforcement point, monitoring scrape identity (not-found, not proven-absent), CNI mode
PHASE2_READS_REVIEW_REQUIRED: YES (Calico, CNPG inline backup, API DNAT)
NETPOL_APPROVED_FOR_APPLY: NO
P8C: NOT_FINAL_ACCEPTED
P8D–P8G/P9: NOT_AUTHORIZED
CI_RELEASE / OWNER_HELPERS / PRODUCTION_MIGRATION_DEPLOYMENT: NOT_EXECUTED
```
