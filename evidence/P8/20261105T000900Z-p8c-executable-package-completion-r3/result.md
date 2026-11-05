# P8C-R1-EXECUTABLE-PACKAGE-COMPLETION — final result (R3)

Дата: 2026-11-05 (UTC). PRIMARY HERMES. Source-only. Live/SSH/CI/registry/apply/production НЕ выполнялись.

## Исправлено по review 2ff8b58 (R2-01…08)
- **R2-01 seed**: `release-check.py first-creation` реализован (typed gate: source_sha/issued_at/expiry≤24);
  cleanup после build (set -e не обрывает до kill на success path).
- **R2-02 lists/baseline**: `validate_envelope` exact api list (+`policy.networking.k8s.io/v1alpha2`),
  continue absent/"" OK, null/non-string/nonempty reject; PR-3 требует 6443/TCP порт + endpoint presence;
  PR-6 сравнивает принятую Tier/Felix projection (default/Deny+kube-admin/Pass+kube-baseline/Pass,
  Felix default nftablesMode=Auto), а не требует пустых; HC-PORTAL требует generation (не None==None).
- **R2-03 state/receipt**: reservation по стабильному authority (package_sha256), не по state-dir;
  receipt — verified JSON (source+package+stage+PASS), plain text не authority; только PASS продвигает
  stage, non-PASS освобождает reservation (retry возможен), crash оставляет UNKNOWN_OUTCOME (no retry).
- **R2-04 subprocess**: stdout EOF ≠ child failure — wait до exit в оставшемся deadline, kill только при
  deadline/failure.
- **R2-05 WAL**: future clock/owner-binding (owner==cluster UID, отсутствие не proof)/sample 30s deadline/
  gate_hash binding на фактическом route.
- **R2-06 release/qualifier**: registry image binding, malformed scan leaf (None vuln) reject; valid
  baseline (signature+attestations) passes verified; qualifier no-checkout/inherited-write-all/seed-extra-trigger.
- **R2-07 pins**: verify_action/verify_image diagnostics sanitized (только тип исключения).
- **R2-08 runbook**: clock_evidence (не clock_skew_bound) + reservation/receipt семантика.

## Полная offline suite (source SHA-bound)
```text
SOURCE_SHA=d5dffe6ad0702bc3883fca45cd6947cb43e86076
A readiness 23 · B qualification 3 + release 4 + negative 7 + qualified:true
C prev regression 28 · D residual 25 · E pin verify exit 0 (10/10) · bash -n + py_compile OK
ИТОГО 90 test methods PASS · 2026-11-05T00:08:15Z–00:09:00Z
```

## Остаётся (CI-only/NOT_EXECUTED, честно)
- Live clock evidence (UNRESOLVED future read proposal) → live PASS требует real evidence.
- CI runtime / private GHCR / rootless availability / cosign·syft·trivy crypto = CI-only.
- WAL scheduler windows/slots 0/300/600 + суммарные бюджеты (90/233 req, 36/179 MiB) реализованы
  частично (sample-deadline + per-request + clock validator есть; полный W/I/N scheduler — остаток).

```text
SOURCE_SHA=d5dffe6ad0702bc3883fca45cd6947cb43e86076
SOURCE_WORK=IN_PROGRESS/PARTIAL (до независимой приёмки)
PUBLIC_PINS_VERIFICATION=ALL_VERIFIED (10/10)
CI_RELEASE / WORKFLOW_PUBLICATION / BOOTSTRAP_PUSH / LIVE_READINESS=NOT_EXECUTED
NETPOL_APPROVED_FOR_APPLY=NO · OWNER_HELPERS=NOT_EXECUTED · PRODUCTION=NOT_EXECUTED
P8C=NOT_FINAL_ACCEPTED · P8D–P8G/P9=NOT_AUTHORIZED
NEXT_GATE_REQUEST=независимая source-приёмка → отдельный execution gate
```
STOP для независимого Architect review.
