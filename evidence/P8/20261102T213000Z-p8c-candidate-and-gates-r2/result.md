# P8C-R1-CANDIDATE-AND-GATES-R2 — result (T1–T4)

Дата: 2026-11-02 (UTC). Исполнитель: PRIMARY HERMES. Offline только.
CANDIDATE_SEMANTICS=ACCEPTED_SOURCE_ONLY (NP-01..04, review ba2af0a). Collector/9-9/offline design не переоткрыты.

## T1 — flows_test.go: направление DNS исправлено + покрытие
- DNS negative: направление `bad-DNS → Portal` исправлено на `Portal → bad-DNS` (проверяется egress, не ingress).
- API: 4 tuple для CNPG + Portal (TCP), cross-product (clusterip:6443 / endpoint:443), .100/.104/.50 (прежний /24) и UDP denied; migrator — все 4 tuple denied.
- DNS от CNPG/Portal/migrator/dataplane к правильному peer UDP+TCP53 и к двум неверным peers (wrong-label / wrong-ns).
- Mutation regression: расширение DNS peer (снятие podSelector) делает bad-DNS allowed — тест чувствителен к расширению.
- 5 dataplane labels: missing + wrong для каждого, wrong namespace, 8081 deny.
- S1/S2a/S2b по отдельности сохраняют CNPG flows; negative rollback union (deny-only НЕ восстанавливает S0).
- 6 name/namespace/policyTypes; отсутствие broad CIDR (только /32) и unrestricted peer (пустой To/From).
```text
command: go test -count=1 -v ./networkpolicy (workdir portal/)
go: go1.27.3 linux/amd64 (GOTOOLCHAIN=local)
exit=0 · 2 test functions · 65 sub-тестов PASS
START_UTC=2026-11-02T21:28:56Z · END_UTC=2026-11-02T21:28:57Z
```
Изменение networkpolicy.yaml — только stale-комментарий «FULL verified … allowlist» → «candidate … NOT runtime-verified».

## T2 — runtime-readiness: metrics endpoint + bounded WAL proposal
- Убрано ложное «нет скрейпера → нет metrics endpoint». Instance endpoint `9187/metrics` доказан P8B;
  metrics.go — прямой HTTP scrape без Prometheus.
- `S3_WAL_OBSERVATION_METHOD=SOURCE_BOUND_PROPOSAL`: `cnpg_pg_stat_archiver_{archived_count,failed_count,last_archived_time,last_failed_time,stats_reset_time}` на primary instance `9187/metrics` (CNPG v1.30.1 default-monitoring.yaml), прямой scrape, primary-bound, reset/restart/role-change/idle → INCONCLUSIVE.

## T3 — release draft: pins + bootstrap + permissions
- GITHUB_TOKEN: job token выдаёт GitHub Actions; Owner обеспечивает workflow/package settings + publication (не передаёт значение).
- Полная таблица pins (Go/buildkit/rootlesskit/syft/trivy/cosign/postgres/actions) с digest/checksum/source/UNVERIFIED.
- Manifest path/blob/SHA256 для template + install-verified-go.sh + release-check.py + test_release.py.
- Bootstrap private-before: package existence НЕ доказан → конкретный bootstrap-вариант (создание private seed + read-only проверка ДО run); не ослаблять private-before.
- Run budget/timeout/retry/expiry (draft).

## T4 — deployment draft: точные endpoint + доказательства
- `/healthz` отсутствует → mgmt `/livez,/readyz,/startupz` на 8081; 11 API-маршрутов из server.go перечислены.
- readiness (`/readyz` 200) ≠ доказательство DB TLS verify-full; разделены pinned config/CA/SNI/no-fallback + observed connection.
- S0 = spec.instances/status.instances/status.readyInstances + Ready condition (по accepted plan).
- acceptance matrix: migration version/checksum+VerifySchema, 11 API, auth 401/200, RBAC SA verb/resource/scope (authz-only), bounded events, secret scan, platform postcheck.

## Итог
```text
TASK=P8C-R1-CANDIDATE-AND-GATES-R2
CANDIDATE_SEMANTICS=ACCEPTED_SOURCE_ONLY (NP-01..04)
T1=RESOLVED · T2=RESOLVED · T3=RESOLVED · T4=RESOLVED (авторская offline-подготовка)
OFFLINE_POLICY_TESTS=PASS (go1.27.3, exit=0, 2 func / 65 subtests)
RELEASE_TEMPLATE_CHANGED=NO (byte-identical)
S3_WAL_OBSERVATION_METHOD=SOURCE_BOUND_PROPOSAL (cnpg_pg_stat_archiver_* via instance 9187/metrics)
CI_RELEASE=NOT_EXECUTED · PHASE2_NEW_RUN_APPROVED=NO · NETPOL_APPROVED_FOR_APPLY=NO
OWNER_HELPERS=NOT_EXECUTED · PRODUCTION_MIGRATION_DEPLOYMENT=NOT_EXECUTED
P8C=NOT_FINAL_ACCEPTED · P8D–P8G/P9=NOT_AUTHORIZED
```
STOP для Architect review.
