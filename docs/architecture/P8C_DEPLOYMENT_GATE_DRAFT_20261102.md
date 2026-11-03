# P8C Deployment Gate — DRAFT (NOT_AUTHORIZED_FOR_EXECUTION)

Дата: 2026-11-03. Исполнитель подготовки: PRIMARY HERMES. Status: DRAFT.

```text
DEPLOYMENT_GATE=NOT_AUTHORIZED_FOR_EXECUTION
NETPOL_APPROVED_FOR_APPLY=NO · PRODUCTION_MIGRATION_DEPLOYMENT=NOT_AUTHORIZED
```

## DEP-01 — prerequisites, порядок S0–S4, rollback (восстановлено)

Prerequisites (до S1): accepted candidate SHA; current baseline/S3/WAL proof (PR-3/6 + HC-ARCH-STATE +
RD-01 pg_stat_archiver); accepted CI run + verified source/image digest + private pull readiness;
Owner-provisioned auth/pull credentials; разрешённые объекты ниже.

```text
S0  baseline (условный): spec.instances=3, status.instances=3, status.readyInstances=3, Ready=True.
S1  apply p8c-cnpg-existing-flows (полный CNPG allowlist).
S2a apply baseline-default-deny-all;  S2b apply baseline-allow-dns-egress.
S3  apply p8c-portal-flows + p8c-migrator-flows (политики ДО workloads) → Deployment/Job;
    migrator ДО application readiness; migration → application readiness; один verified digest.
S4  apply p8c-portal-dataplane-flows → Gateway ПОСЛЕДНИМ. Экспозиция: риск начинается с создания
    Gateway; Programmed/LB IP не гарантия отсутствия внешнего доступа; cleanup generated Service/Pods
    (обе owning labels) проверяется ДО снятия dataplane egress.
Rollback: только вновь созданные объекты по UID-precondition, no-overwrite; S4→S3→S2b→S2a→S1→S0;
default-deny/allow-dns снимать ДО existing-flows; migration без destructive down-SQL; CNPG не трогать;
NetPol rollback не удаляет existing workloads.
```

## DEP-02 — объектный inventory (реальные path/blob; NEW / PLANNED-generated / existing-check)

| Kind | name / ns | path:blob | actor | класс |
|---|---|---|---|---|
| ServiceAccount | portal-reader / portal | portal/manifests/rbac.yaml:036e90b40a44701c04b145af4c987ae962648477 | operator | NEW |
| ServiceAccount | portal-migrator / portal | rbac.yaml (тот же) | operator | NEW |
| ClusterRole | portal-platform-reader | rbac.yaml | operator | NEW |
| ClusterRoleBinding | portal-platform-reader | rbac.yaml | operator | NEW |
| Role | portal-db-reader / portal | rbac.yaml | operator | NEW |
| RoleBinding | portal-db-reader / portal | rbac.yaml | operator | NEW |
| Role | portal-ingress-reader / portal | rbac.yaml | operator | NEW |
| RoleBinding | portal-ingress-reader / portal | rbac.yaml | operator | NEW |
| Role | portal-velero-reader / velero | rbac.yaml | operator | NEW |
| RoleBinding | portal-velero-reader / velero | rbac.yaml | operator | NEW |
| Issuer | portal-ui-bootstrap / portal | portal/manifests/gateway.yaml:1e1f48a3c6d03c4558f4b4c3cca24bc12c22b763 | operator | NEW |
| Certificate | portal-ui-root / portal (secretName portal-ui-ca) | gateway.yaml | operator | NEW |
| Issuer | portal-ui-ca / portal | gateway.yaml | operator | NEW |
| Certificate | portal-ui-server / portal (secretName portal-ui-tls, SAN portal.demo-pak.test) | gateway.yaml | operator | NEW |
| Secret | portal-ui-ca / portal | generated (cert-manager) | cert-manager | PLANNED-generated |
| Secret | portal-ui-tls / portal | generated (cert-manager) | cert-manager | PLANNED-generated |
| Secret | portal-db-ca / portal (DB CA) | CNPG (P8_PORTAL_DB_CONTRACT.md) | CNPG | existing-check |
| Secret | portal-db-app / portal (password) | CNPG (secretKeyRef) | CNPG | existing-check |
| Secret | portal-ui-auth / portal | Owner-provisioned (не CNPG, не доказан existing) | Owner | existing-check |
| Secret | portal-registry-pull / portal | Owner-provisioned (не CNPG) | Owner | existing-check |
| Service | portal / portal (ClusterIP 80→8080) | portal/manifests/deployment.yaml:2cb27165330fe4b6772af3a06a1940d661efc72f | operator | NEW |
| Service | portal-db-metrics / portal (9187, sel cnpg.io/cluster=portal-db) | deployment.yaml | operator | NEW |
| Job | portal-migrate-0001 / portal | deployment.yaml | operator | NEW |
| Deployment | portal / portal (replicas 1) | deployment.yaml | operator | NEW |
| Gateway | portal-gateway / portal | gateway.yaml | operator | NEW |
| HTTPRoute | portal / portal | gateway.yaml | operator | NEW |
| NetworkPolicy ×6 | p8c-cnpg-existing-flows, baseline-default-deny-all, baseline-allow-dns-egress, p8c-portal-flows, p8c-migrator-flows (portal); p8c-portal-dataplane-flows (envoy-gateway-system) | portal/manifests/networkpolicy.yaml:15f0b3245586bf5086e5a24ed02b0460121f7712 | operator | NEW |

portal-ui-auth и portal-registry-pull — Owner-provisioned, НЕ CNPG-генерируемые и НЕ доказаны existing.
Generated EnvoyProxy Service/Pods — имена заранее не угадывать (selectors/owner UID из §1 design).

## DEP-03 — RBAC matrix (source rbac.yaml)

Cluster-scope (ClusterRole portal-platform-reader → CRB для SA portal-reader) даёт **cluster-wide**
namespaced read (get/list) на: nodes, persistentvolumes, pods, services, persistentvolumeclaims, events
(core); storageclasses (storage.k8s.io); deployments/statefulsets/daemonsets/replicasets (apps);
jobs/cronjobs (batch); endpointslices (discovery.k8s.io); volumesnapshots (snapshot.storage.k8s.io);
nodes/pods (metrics.k8s.io). Это НЕ «только portal+velero».

Named (GET-only, не list): clusters[portal-db], scheduledbackups[portal-db-daily], objectstores
[portal-db-backup] (postgresql.cnpg.io/barmancloud.cnpg.io); gateways[portal-gateway], httproutes[portal]
(gateway.networking.k8s.io). backups (postgresql.cnpg.io) get+list. velero.io backupstoragelocations/
backups/restores get+list (namespace velero).

Denied (не выдаётся): secrets, configmaps, serviceaccounts/token, pods/exec, pods/proxy, create/update/
patch/delete, любые resourceNames вне named set.

**Representative SAR rows (operator, не actual mutation; ≤20 явных случаев):**

| subject | group/resource/subresource | verb | ns/name | expected | timeout | artifact |
|---|---|---|---|---|---|---|
| SA portal-reader | "" / nodes | get | cluster | allow | 15s | sar-node.json |
| SA portal-reader | "" / pods | list | cluster | allow | 15s | sar-pods.json |
| SA portal-reader | postgresql.cnpg.io / clusters | get | portal/portal-db | allow | 15s | sar-cluster.json |
| SA portal-reader | postgresql.cnpg.io / clusters | list | portal | deny | 15s | sar-cluster-list.json |
| SA portal-reader | gateway.networking.k8s.io / gateways | get | portal/portal-gateway | allow | 15s | sar-gw.json |
| SA portal-reader | "" / secrets | get | portal/portal-db-app | deny | 15s | sar-secret.json |
| SA portal-reader | "" / pods/exec | create | portal | deny | 15s | sar-exec.json |
| SA portal-reader | apps / deployments | create | portal | deny | 15s | sar-deploy-create.json |

Это representative runtime checking; полное source-rule сравнение отдельно. SAR-POST — будущая
bounded operator-активность, НЕ разрешение Portal создавать reviews и НЕ destructive mutation test.

## DEP-04 — Migration, TLS, API, events (числа)

- Migration: version=1, checksum=`53e37c762d9efd4f8985ad848d33a6a3604c4554e65accb39429d14d62dfdbe7`;
  proof = Job exit 0 → ledger query `SELECT version, checksum ... ORDER BY version DESC LIMIT 1` →
  VerifySchema (main.go). Не только exit 0.
- DB TLS verify-full: config DBHost/port 5432, sslmode verify-full, sslrootcert /etc/portal/db/ca.crt,
  SNI portal-db-rw.portal.svc, MinVersion TLS1.2, InsecureSkipVerify=false, Fallbacks=0 (poolConfig).
  Proof = успешная миграция/VerifySchema через pool (иначе connect fail). `/readyz` 200 ≠ verify-full
  proof; `ssl=true` ≠ hostname verification. App Ping = store.Ping (3s).
- 11 API (server.go): /api/v1/{health,summary,nodes,workloads,pods,services,storage,backups,database,
  metrics,events} — Basic Auth (401/200), GET/HEAD only. mgmt /livez,/readyz,/startupz на 8081 (НЕ
  открывать через внешний Service; `/healthz` отсутствует).
- Events: timeline_events (dedup_key UNIQUE, TTL 7d, cap 50000, prune ≤1000/statement), observation_batches
  (TTL 7d, cap 20000); readback ListEvents keyset (id DESC, afterID). Без искусственных K8s событий.
- Bounds (accepted plan): request timeout min(15s, remaining W); W=60/30/120s; I=10/5/10s; N≤6;
  **Gateway: W=120s, I=10s, N≤12 в ОДНОМ hard window** (не 12×120s).

## Статус
```text
DEPLOYMENT_GATE_DRAFT=REVIEW_READY (DRAFT)
IMAGE_DIGEST=UNAVAILABLE (до CI release; не fake hex)
PRODUCTION_MIGRATION_DEPLOYMENT=NOT_EXECUTED · NETPOL_APPROVED_FOR_APPLY=NO · P8C=NOT_FINAL_ACCEPTED
```
