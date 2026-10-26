# P8C RV-02 — live inventory result (base read-only collection)

Date: 2026-10-26 (UTC).
Executor: Hermes2. Review: Architect.

## Artifact
- File: `inventory.jsonl` (15 records, 49 675 bytes)
- SHA-256: `bc692fc80634fc7eeda6f5d5cc564101ca4b391974a37b5185e1baeef4044f41`

## Script binding (pinned)
- Source commit: `9a98b385c5a484b0a8f79086b432b8b72289ccee`
- Script: `portal/networkpolicy/inventory.py`
- Blob SHA-1: `5f0e2450358bfd9b08b542f013be5a914b9195a4`
- SHA-256 (pinned): `7806f494bcee93f31eb2cb0348d2cd8f7cbbf5743261336226a251643d8988a2`
- Verification: `sha256sum --check --strict -` → OK (verified before transfer and again on node-01)

## Execution
- Context: `kubernetes-admin@pak-portal`
- START: `2026-10-26T17:32:44Z`
- END:   `2026-10-26T17:32:47Z`
- EXIT:  `1`
- Client: `v1.36.2` (Kustomize v5.8.1)
- Server: `v1.36.2`

## Result
- Records: 15 — 12 OK, 3 API_NOT_SERVED.
- API_NOT_SERVED (3) — `monitoring.coreos.com` API group not served (Prometheus Operator
  CRDs absent). This is a discovery-read gap, NOT an access error:
  1. `kubectl get servicemonitors.monitoring.coreos.com -A`
  2. `kubectl get podmonitors.monitoring.coreos.com -A`
  3. `kubectl get --raw /apis/monitoring.coreos.com/v1`
- Secret scan: CLEAN (no token/password/private-key/secret material; strict URL sanitization).

## Status
`RV02_BASE_INVENTORY`: PARTIAL. Three API_NOT_SERVED and the partial result are preserved
as-is; the status is NOT relabeled PASS.
