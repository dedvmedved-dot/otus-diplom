# P8C-R1-CANDIDATE-AND-GATES-R2-RESIDUAL — result (R1–R4, E)

Дата: 2026-11-03 (UTC). Исполнитель: PRIMARY HERMES. Offline только.
CANDIDATE_SEMANTICS=ACCEPTED_SOURCE_ONLY; METRIC_SOURCE_CHOICE=ACCEPTED_SOURCE_ONLY.
Collector/9-9/offline design/P8B/PG17 не переоткрыты.

## R1 — policy tests: полнота negative + structural guard
- API negative цикл src={db,portal} × {ClusterIP:6443, .101/.102/.103:443, .100/.104/.50:6443} + UDP на всех 4 TCP tuples; migrator — все 4 tuple denied.
- DNS wrong-label/wrong-ns теперь TCP и UDP для каждого из 4 workload peers; mutation изолирован к DNS egress peers.
- Structure guard (validateStructure): exact apiVersion/kind/name/namespace + exact type-set (без дубликатов), exact allowed IP/port/proto tuples, запрет пустых from/to peers, selector расширений, пустых ports, port=nil, endPort, named ports, unexpected port/protocol. Baseline podSelector={} допустим на target.
- Negative guard fixtures (mutated copies отвергаются): extra-UDP, SCTP9999, empty peer {}, removed Egress policyType, unset /32:6443, endPort.
- S1/S2a/S2b: добавлены DNS TCP и три endpoint6443 к ClusterIP/peer/operator/S3.
```text
command: go test -count=1 -v ./networkpolicy (workdir portal/)
go: go1.27.3 linux/amd64 (GOTOOLCHAIN=local)
exit=0 · 3 test functions · 91 subtests PASS
START_UTC=2026-11-03T03:05:19Z · END_UTC=2026-11-03T03:05:20Z
```

## R2 — runtime WAL proposal: числа + access method
- Заполнены N=2/stage (max 3), W=5s, I=max(300s,stage)≤600s, per-request timeout 5s, max body 1MiB/≤5MiB total, verdict PASS/FAIL/INCONCLUSIVE (failed_count/last_failed_time, reset/restart/role/idle/parse/NaN/timeout).
- `ACCESS_METHOD=UNRESOLVED` (частично): endpoint `http://portal-db-metrics.portal.svc:9187/metrics` + series определены, но primary-bound binding не решена (Service selector cnpg.io/cluster=portal-db не дискриминирует primary; Portal Pod-IP pinning запрещён). Точный вопрос сформулирован.

## R3 — release draft: URLs + bootstrap + budget
- Точные expanded URLs для каждого pin (go/buildkit/rootlesskit/syft/trivy/cosign/postgres/actions); authoritative pin = SHA, tag→SHA НЕ утверждается.
- Identity/OIDC/artifacts литералами (workflow file, OIDC issuer, certificate-identity, image digest).
- `BOOTSTRAP_METHOD=UNRESOLVED` (механизм первого private upload/repository association требует Owner/Architect).
- Численный budget: test 20m / release 30m, no retry, source-change invalidation (enforcement ещё не в template).

## R4 — deployment draft: таблицы вместо текста
- Полный object inventory (18 объектов: RBAC 10 + CA/Secret + Services 2 + Job + Deployment + Gateway + HTTPRoute + NetPol×6) с kind/name/ns/blob/actor/new-vs-preexisting.
- RBAC matrix: subject portal-reader, exact allowed verbs/resources + denied (secrets/exec/proxy/mutation); authz = SubjectAccessReview (≤20, без mutation).
- Migration: version=1, checksum=53e37c762d9efd4f8985ad848d33a6a3604c4554e65accb39429d14d62dfdbe7; ledger query + VerifySchema.
- DB TLS: verify-full proof = poolConfig (no-fallback/InsecureSkipVerify=false) + успешная миграция через pool; /readyz ≠ TLS proof.
- UI/auth/11 API exact paths; events persistence (TTL 7d, cap 50000/20000, keyset); bounds наследуются из accepted plan.

## Итог
```text
TASK=P8C-R1-CANDIDATE-AND-GATES-R2-RESIDUAL
R1/R2/R3/R4=RESOLVED (авторская offline-подготовка; числа/имена заполнены, не placeholders)
OFFLINE_POLICY_TESTS=PASS (go1.27.3, exit=0, 3 func / 91 subtests)
RELEASE_TEMPLATE_CHANGED=NO
ACCESS_METHOD=UNRESOLVED (primary-bound metrics binding) · BOOTSTRAP_METHOD=UNRESOLVED
CI_RELEASE=NOT_EXECUTED · PHASE2_NEW_RUN_APPROVED=NO · NETPOL_APPROVED_FOR_APPLY=NO
OWNER_HELPERS=NOT_EXECUTED · PRODUCTION_MIGRATION_DEPLOYMENT=NOT_EXECUTED
P8C=NOT_FINAL_ACCEPTED · P8D–P8G/P9=NOT_AUTHORIZED
```
STOP для Architect review.
