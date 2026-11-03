# P8C-R1-CANDIDATE-AND-GATES-R4-FINALIZATION — result (F1, F3, editorial)

Дата: 2026-11-03 (UTC). PRIMARY HERMES. Offline only. Candidate YAML/app/collector/RBAC/deployment/Gateway не изменены.

## F1 — exact accepted contract (не global allowed-port sets)
- Скопирован frozen `accepted-policy-contract.json` (blob 91a4e571…) в `portal/networkpolicy/testdata/`
  (byte-identical reviewer-фикстуре; НЕ генерируется из кандидата в рантайме).
- `validateStructure` переписан на сравнение 6 identities + полных specs против frozen контракта
  (reflect.DeepEqual; missing/extra objects, rules, selectors, expressions, peers, ports, protocols,
  policyTypes). Global allowed-port наборы удалены → «разрешённый порт у неправильного peer» теперь
  отклоняется.
- Интегрирован reviewer `exact_rule_regression_test.go` (10 случаев, blob e40304dc…).
- Поведенческие both-sides тесты сохранены (fixture equality = дополнительный change guard).
```text
go test -count=1 -v ./networkpolicy → exit=0, 4 функции / 107 sub-тестов PASS
START_UTC=2026-11-03T09:38:40Z · END_UTC=2026-11-03T09:38:41Z (go1.27.3, GOTOOLCHAIN=local)
```

## F3 — normative observation budget (заменён)
Один sample = 5 запросов (Cluster GET → Pod GET → metrics GET → same Pod GET → same Cluster GET).
Заполнена нормативная таблица: 6 окон × 3 slots (offsets 0/300/600s), per-request ≤5s, per-sample ≤30s,
per-window 660s, caps (metadata 256KiB / metric 1MiB / sample 2MiB / window 15req+6MiB / все 90req+36MiB
+3960s observation), abort/retry-distinction. Verdict + clock (skew ≤5s, PASS boundary `> op_end+5s &&
<= sample_end+5s`; S0 first-sample-end). Primary-only = политика сравнения; archive_mode=always note.

## Editorial (закрытые дизайны)
- Deployment: resourceNames-denied ограничен named-GET Role-ресурсами (scope portal+velero); full SAR
  subject `system:serviceaccount:portal:portal-reader`; literal ledger query
  `SELECT version, checksum FROM portal.schema_migrations ORDER BY version DESC LIMIT 1;`.
- Release: launch expiry = 24h от future gate issued_at UTC; NOT_IMPLEMENTED_IN_TEMPLATE.

## E — evidence
Frozen input (6 файлов, sha256 до скана), output вне input set, grep exit=1 = no-match (0/1/2 различены).

## Итог
```text
TASK=P8C-R1-CANDIDATE-AND-GATES-R4-FINALIZATION
F1/F3/editorial=RESOLVED (авторская offline-подготовка)
OFFLINE_POLICY_TESTS=PASS (go1.27.3, exit=0, 4 func / 107 subtests)
CONTRACT_FIXTURE=91a4e571ea36395b3cafd8490f057a28e78cf4d6 (frozen, unchanged)
ACCESS_METHOD=DESIGN_SELECTED (operator-primary-bound) / EXECUTION_NOT_AUTHORIZED
CI_RELEASE=NOT_EXECUTED · PHASE2_NEW_RUN_APPROVED=NO · NETPOL_APPROVED_FOR_APPLY=NO
OWNER_HELPERS=NOT_EXECUTED · PRODUCTION_MIGRATION_DEPLOYMENT=NOT_EXECUTED
P8C=NOT_FINAL_ACCEPTED · P8D–P8G/P9=NOT_AUTHORIZED
```
STOP для Architect review.
