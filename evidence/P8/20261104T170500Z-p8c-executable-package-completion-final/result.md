# P8C-R1-EXECUTABLE-PACKAGE-COMPLETION — final result

Дата: 2026-11-04 (UTC). PRIMARY HERMES. Source-only. Live/SSH/CI/registry/apply/production НЕ выполнялись.

## §5 критерии — проверены
1. G1–G6 / ER-01…08: code + test + evidence; обязательный маршрут без stub.
2. Полная suite на финальном source SHA: 37 test methods PASS + qualification qualified:true + pin verify exit 0.
3. Runtime manifest: все исполняемые файлы + hashes (source-manifest.txt); entry points запускаются из комплекта.
4. Runbook соответствует CLI/paths/schema/exits; три drafts синхронизированы в пределах реализации.
5. Source commit (8ffd457) → прогоны → отдельный evidence commit (e5a6f83); frozen scan (12 файлов, output вне input, exit=1 no-match).
6. External prerequisites перечислены отдельно (CI-only/NOT_EXECUTED).

## Закрыто в этом проходе (по review e0c2d3b)
- **Seed**: checkout ДО precheck + pinned rootless BuildKit install/start/readiness/cleanup (CREATE_ALLOWED-only).
- **Release negative matrix (ER-05)**: `test_release_negative.py` — 7 binding tests (missing/invalid JSON/wrong digest/bad provenance/bad SBOM → non-zero, no payloadBinding).
- **Qualification end-to-end**: release-check `verified` исполняется как реальный entry point с synthetic fixtures (не только структура).

## Suite (реальный прогон)
```text
SOURCE_SHA=8ffd45792123e8e2ae1ccdd330ee5e1d013523f9
readiness 23 OK · qualification 3 OK · test_release 4 OK · test_release_negative 7 OK (итого 37)
qualification check qualified:true · pin verify exit 0 (10/10) · bash -n OK · py_compile OK
START_UTC=2026-11-04T17:04:47Z · END_UTC=2026-11-04T17:05:24Z
```

## Остаётся честно (NOT_EXECUTED / CI-only — не маскируют готовое)
- Live clock evidence (UNRESOLVED future read proposal) → будущий live PASS требует real evidence.
- CI runtime / private GHCR / rootless buildctl availability / cosign·syft·trivy runtime = CI-only.
- Полный G2 R-01..08 negative matrix доведён через test_release_negative (7) + существующие (4+3); crypto-verify (cosign) — CI-only.

```text
SOURCE_SHA=8ffd45792123e8e2ae1ccdd330ee5e1d013523f9
FINAL_REMOTE_MAIN_SHA=e5a6f83cc553e9a57832a2082c363b7f31f9ed4c
SOURCE_WORK=IN_PROGRESS/PARTIAL (до независимой приёмки)
PUBLIC_PINS_VERIFICATION=ALL_VERIFIED (10/10)
CI_RELEASE / WORKFLOW_PUBLICATION / BOOTSTRAP_PUSH / LIVE_READINESS=NOT_EXECUTED
NETPOL_APPROVED_FOR_APPLY=NO · OWNER_HELPERS=NOT_EXECUTED · PRODUCTION=NOT_EXECUTED
P8C=NOT_FINAL_ACCEPTED · P8D–P8G/P9=NOT_AUTHORIZED
NEXT_GATE_REQUEST=независимая source-приёмка → отдельный execution gate
```
STOP для независимого Architect review.
