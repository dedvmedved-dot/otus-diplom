# P8C Deployment Gate — DRAFT (NOT_AUTHORIZED_FOR_EXECUTION)

Дата: 2026-11-03. Исполнитель подготовки: PRIMARY HERMES. Status: DRAFT.
Источники: portal/manifests/{networkpolicy,deployment,gateway,rbac}.yaml, P8_PORTAL_DB_CONTRACT.md,
config.go, store.go, migrations.go, server.go, main.go.

```text
DEPLOYMENT_GATE=NOT_AUTHORIZED_FOR_EXECUTION
NETPOL_APPROVED_FOR_APPLY=NO · PRODUCTION_MIGRATION_DEPLOYMENT=NOT_AUTHORIZED
```

## DEP-01 — полный объектный inventory (kind/name/ns/source blob/actor/new)

| Kind | name / ns | Source blob | Actor | new/preexisting |
|---|---|---|---|---|
| ServiceAccount | portal-reader / portal | rbac.yaml | operator | NEW |
| ServiceAccount | portal-migrator / portal | rbac.yaml | operator | NEW |
| ClusterRole | portal-platform-reader | rbac.yaml | operator | NEW |
| ClusterRoleBinding | portal-platform-reader | rbac.yaml | operator | NEW |
| Role | portal-db-reader / portal | rbac.yaml | operator | NEW |
| RoleBinding | portal-db-reader / portal | rbac.yaml | operator | NEW |
| Role | portal-ingress-reader / portal | rbac.yaml | operator | NEW |
| RoleBinding | portal-ingress-reader / portal | rbac.yaml | operator | NEW |
| Role | portal-velero-reader / velero | rbac.yaml | operator | NEW |
| RoleBinding | portal-velero-reader / velero | rbac.yaml | operator | NEW |
| CA/Certificate | CNPG self-signed CA (portal-db); mount /etc/portal/db/ca.crt | P8_PORTAL_DB_CONTRACT.md | CNPG | PREEXISTING |
| Secret ref | portal-db-app (password) + auth verifier (secretKeyRef, never in git) | config.go | CNPG | PREEXISTING |
| Service | portal / portal (ClusterIP 80→8080) | deployment.yaml | operator | NEW |
| Service | portal-db-metrics / portal (ClusterIP 9187, sel cnpg.io/cluster=portal-db) | deployment.yaml | operator | NEW |
| Job | portal-migrate-0001 / portal | deployment.yaml | operator | NEW |
| Deployment | portal / portal (replicas 1) | deployment.yaml | operator | NEW |
| Gateway | portal-gateway / portal | gateway.yaml | operator | NEW |
| HTTPRoute | portal / portal | gateway.yaml | operator | NEW |
| NetworkPolicy ×6 | portal×5 + envoy-gateway-system×1 | networkpolicy.yaml | operator | NEW |

Generated Service/Pods (EnvoyProxy dataplane) — selectors/owner UID из §1 design; имена заранее не угадывать.

## DEP-02 — RBAC matrix (subject system:serviceaccount:portal:portal-reader)

Allowed (get/list; named reads):
- core: nodes, persistentvolumes, pods, services, persistentvolumeclaims, events
- storage.k8s.io: storageclasses; snapshot.storage.k8s.io: volumesnapshots; metrics.k8s.io: nodes, pods
- apps: deployments, statefulsets, daemonsets, replicasets; batch: jobs, cronjobs
- discovery.k8s.io: endpointslices
- postgresql.cnpg.io: clusters (name portal-db), scheduledbackups (name portal-db-daily), backups (get/list)
- barmancloud.cnpg.io: objectstores (name portal-db-backup)
- gateway.networking.k8s.io: gateways (name portal-gateway), httproutes (name portal)
- velero.io: backupstoragelocations, backups, restores

Denied: secrets, configmaps, serviceaccounts/token, pods/exec, pods/proxy, create/update/patch/delete
(все mutation verbs), любые resourceNames вне перечисленных, любые namespace вне portal+velero.

Authz-механизм (operator, не actual mutation): `SubjectAccessReview` authorization.k8s.io/v1 от operator
для portal-reader; конечное число reviews (≤ 20), по одному на allowed-verb/denied-verb случай; mutation
НЕ выполняется, destructive объект не создаётся ради отказа.

## DEP-03 — Migration + schema

- version = 1, checksum = `53e37c762d9efd4f8985ad848d33a6a3604c4554e65accb39429d14d62dfdbe7`
  (sha256 embedded SQL0001), source_revision `^[0-9a-f]{40}$`.
- Proof: Job `portal migrate` exit 0 → ledger row (version=1, checksum exact) → `VerifySchema`
  (main.go validateMigration) подтверждает таблицы/колонки/constraints. Read-only ledger query:
  `SELECT version, checksum FROM portal.schema_migrations ORDER BY version DESC LIMIT 1` (store.go).
  Ожидание — версия+checksum exact, не только exit 0.

## DEP-04 — DB TLS (verify-full) — доказательство, не только readiness

pinned config: DBHost=portal-db-rw.portal.svc:5432, sslmode=verify-full, sslrootcert=/etc/portal/db/ca.crt,
ServerName(SNI)=portal-db-rw.portal.svc, sslsni=1, MinVersion=TLS1.2, InsecureSkipVerify=false, Fallbacks=0
(poolConfig отклоняет ambient PG/no-fallback/insecure). Proof = успешное установление verify-full pool
(миграция/VerifySchema через этот pool успешны ⇒ cert/hostname проверены; иначе connection fail).
`/readyz` 200 = migration+collector OK, НЕ самостоятельное доказательство verify-full. `ssl=true` ≠ hostname
verification. App DB signal = store.Ping (pool.Ping, 3s). Без superuser, Secret export, exec.

## DEP-05 — UI/auth/11 API + events + bounds

- 11 API (server.go): /api/v1/{health,summary,nodes,workloads,pods,services,storage,backups,database,metrics,events}
  — Basic Auth (401 missing/wrong → 200 valid), GET/HEAD only, 405 иначе.
- mgmt: /livez,/readyz,/startupz на 8081 (НЕ открывать через внешний Service). `/healthz` отсутствует.
- UI: `/` + `/assets/*` (200). TLS trust/hostname: Gateway hostname portal.demo-pak.test, TLS Terminate.
- Owner credential ввод: secret-safe (без argv/log/evidence), auth verifier hex SHA-256 из secretKeyRef.
- Events persistence: timeline_events (dedup_key UNIQUE, TTL 7d, cap 50000, prune ≤1000/statement),
  observation_batches (TTL 7d, cap 20000); readback ListEvents keyset (id DESC, afterID); EventRow fields
  (ingestedAt, sourceTime, source, severity, objectKind/NS/Name, reasonCode, occurrences, message).
  Без создания искусственных K8s событий/mutations.
- Bounds: наследуются из accepted plan HC-* (request timeout min(15s, remaining W); W=60/30/120s;
  Gateway 120s×12); конечное число проверок; expiry = завершение одного approved run.

## Статус
```text
DEPLOYMENT_GATE_DRAFT=REVIEW_READY (DRAFT)
IMAGE_DIGEST=UNAVAILABLE (до CI release; не fake hex)
PRODUCTION_MIGRATION_DEPLOYMENT=NOT_EXECUTED · NETPOL_APPROVED_FOR_APPLY=NO · P8C=NOT_FINAL_ACCEPTED
```
