# P8C RV-02 — operator handoff and live evidence (gate b805dff)

Date: 2026-10-26 UTC.

## G0 — recovery
```text
RECOVERY_MAIN_SHA: 025d2d940e39387dde33c9487c438525c062e04f
origin/main at recovery: 025d2d940e39387dde33c9487c438525c062e04f
Delta from b805dff: 1 commit — docs/architecture/P8C_RV02_ACCEPTANCE_b805dff_20261026.md
  + evidence/P8/20261026-p8c-rv02-b805dff-acceptance/{assurance_test.py,execution.json}
Architect Gate: docs/architecture/P8C_RV02_ACCEPTANCE_b805dff_20261026.md
  TC-01..04=CLOSED / INDEPENDENTLY VERIFIED
  OWNER_INVENTORY_SCRIPT_APPROVED=YES (exact bytes only)
  OWNER_INVENTORY_HANDOFF_ALLOWED=YES
  NETPOL_APPROVED_FOR_APPLY=NO
No contradiction between gate and task. Local worktree was clean; nothing to preserve.
```

## G1 — owner handoff (published)
`portal/networkpolicy/operator-handoff.md` updated to the APPROVED pinned package:
- source commit `9a98b385c5a484b0a8f79086b432b8b72289ccee`
- script blob `5f0e2450358bfd9b08b542f013be5a914b9195a4` / SHA-256 `7806f494…`
- exact verify+run command (hash check fails → STOP):
```sh
printf '%s  %s\n' '7806f494…' 'portal/networkpolicy/inventory.py' | sha256sum --check --strict - &&
python3 portal/networkpolicy/inventory.py --context "<approved-context>" --output "<new-nonexistent-local-directory>"
```
Local hash re-verified at delivery: `portal/networkpolicy/inventory.py: OK`.

## ACCESS_PATH — NONE (BLOCKED_EXTERNAL)
Single verification (not a probe loop):
- `kubectl`: ABSENT on Hermes host.
- `/etc/kubernetes/admin.conf`: ABSENT.
- `~/.kube/config`: ABSENT.
No authorized operator session is reachable from this host. Per the gate, this
remains BLOCKED_EXTERNAL; no offline rework or access scan is authorized to force
a different STOP.

## One concrete request to Owner
Run the pinned handoff (above) in an already authorized operator session and
return: sanitized `inventory.jsonl` + source SHA + verified script SHA-256 + UTC
start/end + exit code + `kubectl version` (client+server) from the same context.
Do NOT return kubeconfig/tokens/keys/raw full objects/Secret or ConfigMap data.

## Status fields (final STOP)
```text
OWNER_HANDOFF: PUBLISHED (APPROVED pinned package, exact verify+run command)
ACCESS_PATH: NONE (BLOCKED_EXTERNAL)
NETPOL_LIVE_INVENTORY: NOT_EXECUTED (BLOCKED_EXTERNAL)
INVENTORY_EXIT_CODE: NOT_AVAILABLE (no authorized session)
FLOW_MATRIX_COMPLETE: NO (14 FLOW-IDs; 8 live-only UNKNOWN)
REMAINING_UNKNOWNS: Barman plugin direction, API DNAT, monitoring scrape identity,
  DNS, S3 routing, Envoy ownership, baseline union, CNI semantics
PHASE2_READS_REVIEW_REQUIRED: YES (CNI/plugin/monitoring/Gateway version-specific
  reads remain NOT_DEFINED/NOT_APPROVED until discovery identifies exact versions)
NETPOL_APPROVED_FOR_APPLY: NO
CI_RELEASE / OWNER_HELPERS / PRODUCTION_MIGRATION_DEPLOYMENT: NOT_EXECUTED
P8C: NOT_FINAL_ACCEPTED
P8D–P8G/P9: NOT_AUTHORIZED
```

Source SHA (handoff doc): `04d4fcbe473a1705016aff1a64616f7287d8827d`.
No workflow token used; no live/CI/production/helper operations; historical
evidence unchanged.
