# P8C-R1-EXECUTABLE-RELEASE-AND-READINESS-R1 — rework checkpoint

Дата: 2026-11-04 (UTC). PRIMARY HERMES. Source-only. Live/SSH/CI/registry-private/apply/production НЕ выполнялись.

## Исправлено по review 6249b97 (ER-01…ER-08)
- **ER-01 (predicates)**: real predicates — HC-DB spec/status/readyInstances=3/3/3 + Ready condition
  (False/уменьшение → FAIL, missing → INCONCLUSIVE); HC-ARCH-STATE ContinuousArchiving; HC-PORTAL
  replicas/generation; HC-GW Accepted+Programmed+observedGeneration; HC-OP/DNS nonempty ready set;
  PR-3 exact ready API tuples {.101,.102,.103}:6443; PR-5 exactly-one Service LoadBalancer/Local/443→10443
  (2 items → FAIL); PR-6 typed 9-response baseline. Нет PASS для нездоровых объектов.
- **ER-02 (gate/state)**: strict gate — mode=LIVE only, context, source_sha, package_sha256 (runtime
  hash of readset+wrapper), UTC-aware issued/expiry (calendar.timegm, reject future, expiry≤24h), stage
  whitelist, atomic O_EXCL reservation (re-run/UNKNOWN_OUTCOME blocked), nonzero exit on non-PASS.
- **ER-03 (transport)**: bounded streaming subprocess (read chunks, cap during read, kill on deadline),
  secret/configmap path reject, typed envelope (kind/apiVersion/items/continue), value-free journal.
- **ER-04 (WAL)**: wal_sample (5-request Cluster→Pod→metrics→same Pod→same Cluster, primary-bound,
  identity bracket, pg_stat_archiver parser) присутствует; HTTP client/budget wiring в main пока НЕ
  подключён (остаётся PARTIAL — честный gap).
- **ER-07 (pins)**: verify-pins sanitize_url (strip query/userinfo), per-item UTC, explicit nonzero exit
  on non-VERIFIED.

## Тесты (all PASS)
```text
readiness: 16 tests OK · qualification: 3 tests OK · qualification check qualified:true
pin verification: exit 0 (10/10 VERIFIED, cached re-hash) · bash -n OK
```

## Остаётся PARTIAL (честно)
- WAL HTTP client + полный budget-учёт (90/233 req, 36/179 MiB) + clock validator — не подключены в main.
- ER-05/ER-08: полная matrix + package manifest + runbook + drafts-синхронизация — частично.

```text
SOURCE_SHA=e4e2a215cffdb2cf58f98ef82379616342400fc9
SOURCE_WORK=IN_PROGRESS/PARTIAL
READINESS_WRAPPER_SOURCE_QUALIFIED=PARTIAL (predicates/gate/transport готовы; WAL wiring остаётся)
RELEASE_TEMPLATE_SOURCE_QUALIFIED=PARTIAL · PRIVATE_SEED_TEMPLATE_SOURCE_QUALIFIED=PARTIAL
PUBLIC_PINS_VERIFICATION=ALL_VERIFIED (10/10)
CI_RELEASE=NOT_EXECUTED · WORKFLOW_PUBLICATION_DISPATCH=NOT_EXECUTED · BOOTSTRAP_PUSH=NOT_EXECUTED
LIVE_READINESS=NOT_EXECUTED · NETPOL_APPROVED_FOR_APPLY=NO · OWNER_HELPERS=NOT_EXECUTED
PRODUCTION_MIGRATION_DEPLOYMENT=NOT_EXECUTED · P8C=NOT_FINAL_ACCEPTED · P8D–P8G/P9=NOT_AUTHORIZED
```

Промежуточный checkpoint; продолжаю WAL-wiring и финализацию пакета.
