# P8C-R1-CANDIDATE-AND-GATES-R3-CORRECTION — result (F1–F4, E)

Дата: 2026-11-03 (UTC). PRIMARY HERMES. Offline only. Candidate YAML/app/collector/RBAC/deployment/Gateway не изменены.

## F1 — structural guard полон
validateStructure теперь: exact target selector (baseline {} допустим; non-baseline exact), ingress ports
(empty/nil/endPort/named) + ingress peers (empty {}), selector-egress port/protocol set, required peer
labels (kube-system→k8s-app=kube-dns; owning-gateway→5 labels). Expected allowlist захардкожен, НЕ выводится
из мутируемого YAML. 12 negative fixtures (6 прежних + 6 новых: ingress-empty-peer, ingress-no-ports,
ingress-endport, selector-egress-sctp, widen-target, dns-missing-label). DNS mutation изолирован к
kube-system/k8s-app=kube-dns peer; xDS/CNPG peers доказаны неизменными.
```text
go test -count=1 -v ./networkpolicy → exit=0, 3 functions / 97 subtests PASS
START_UTC=2026-11-03T03:29:35Z · END_UTC=2026-11-03T03:29:36Z (go1.27.3, GOTOOLCHAIN=local)
```

## F2 — deployment draft исправлен
RBAC scope: portal-platform-reader CRB даёт cluster-wide namespaced read (НЕ «portal+velero»); named
permissions GET-only. 8 SAR case rows. Object inventory дополнен UI PKI (Issuer/Certificate×2, generated
Secrets portal-ui-ca/portal-ui-tls), portal-ui-auth + portal-registry-pull (Owner-provisioned), 6 NetPol
имена; real path:blob refs. Восстановлены DEP-01 prerequisites + S0–S4 + UID/no-overwrite rollback.
Gateway bounds исправлено: W=120s, I=10s, N≤12 в одном окне.

## F3 — metrics access DESIGN_SELECTED
`ACCESS_METHOD=DESIGN_SELECTED` (OPERATOR_PRIMARY_BOUND_DIRECT_EXPORTER) / EXECUTION_NOT_AUTHORIZED.
Binding: Cluster currentPrimary → named Pod → UID/IP/role validation → HTTP 9187/metrics; bracket metadata
GETs; согласованный бюджет (18 GET, 6 metric + 12 metadata, 9 MiB total, 5s/request, 30s/stage, no retry).
Verdict/freshness/reset/idle определены; archive_mode=always отмечено (не «only primary»).

## F4 — release draft: bootstrap DESIGN_SELECTED + traceability
`BOOTSTRAP_METHOD=DESIGN_SELECTED` (SEPARATE_GITHUB_ACTIONS_PRIVATE_SEED_GATE). Восстановлена таблица
requirement→step/helper→offline proof→CI-only proof. Численный budget + launch expiry; identity/OIDC/artifacts.

## E — secret scan: ERROR исправлен на NO-MATCH
Предыдущий exit=2 (self-match + output-inside-input) — сканерная ошибка, не утечка. Новый прогон:
frozen input set (4 файла, sha256 зафиксирован ДО скана), output вне input set, grep exit=1 = NO MATCHES
(0=match/1=no-match/2=error различены), 0 matches.

## Итог
```text
TASK=P8C-R1-CANDIDATE-AND-GATES-R3-CORRECTION
F1/F2/F3/F4/E=RESOLVED (авторская offline-подготовка)
OFFLINE_POLICY_TESTS=PASS (go1.27.3, exit=0, 3 func / 97 subtests)
ACCESS_METHOD=DESIGN_SELECTED (OPERATOR_PRIMARY_BOUND_DIRECT_EXPORTER)
BOOTSTRAP_METHOD=DESIGN_SELECTED (SEPARATE_GITHUB_ACTIONS_PRIVATE_SEED_GATE)
CI_RELEASE=NOT_EXECUTED · PHASE2_NEW_RUN_APPROVED=NO · NETPOL_APPROVED_FOR_APPLY=NO
OWNER_HELPERS=NOT_EXECUTED · PRODUCTION_MIGRATION_DEPLOYMENT=NOT_EXECUTED
P8C=NOT_FINAL_ACCEPTED · P8D–P8G/P9=NOT_AUTHORIZED
```
STOP для Architect review.
