# P8C-R1 RESUME-R3 — native PG17 + network inventory attempt (Hermes)

Date: 2026-10-24 UTC.

## Native PostgreSQL 17 integration — EXECUTED (PASS)
- Evidence HEAD (main): `8dca3c9e217c51b32554a79cc831dfd454b27ab0`.
- Application source SHA (per Architect result.md): `817f0ecef8da1cd756f4b6ab48d61e023764329a`.
- Go 1.27.3 (GOTOOLCHAIN=local), PostgreSQL 17.11 (PGDG, Ubuntu 24.04).
- Command (from /root/otus-diplom/portal):
  `TEST_DATABASE_URL="postgres://postgres:***@127.0.0.1:5432/portal_test" go test -tags integration -count=1 -v ./internal/store/`
- Result: **12/12 PASS, exit 0, 0 FAIL** (fresh `-count=1`):
  TestIntegrationInsertBatchIdempotent, TestIntegrationEventDedupAndRecreate,
  TestIntegrationMigrationNoopAndMismatch, TestIntegrationLedgerDrift,
  TestIntegrationPruneTTL, TestIntegrationPruneCap, TestIntegrationVerifySchemaNegative,
  TestIntegrationListEventsKeysetStableUnderInsert, TestIntegrationSchemaTypeAndConstraintDrift,
  TestIntegrationCapturedViewSurvivesInsertUpdatePrune, TestFixedTLSConfigAndHandshake,
  TestAllAmbientPGOverridesRejectedBeforeParsing.
- Loopback + `/portal_test` + PostgreSQL major 17 guard enforced by the suite.
- Raw output: `native-pg17-integration.txt`.

## Read-only network inventory — BLOCKED_EXTERNAL
- kubectl: ABSENT on this host; no `/etc/kubernetes/admin.conf`, no `~/.kube/config`.
- OpenConnect VPN (tun0) is UP; PAK GW `192.168.194.1` is REACHABLE.
- node-01 (172.30.140.101:22), node-02 (172.30.140.102:22), node-03 (172.30.140.103:22):
  CLOSED/UNREACHABLE (connection timeout on TCP/22).
- node-03 management (192.168.194.39:22) answers SSH but requires credentials not held
  by this host (Permission denied publickey,password under BatchMode).
- No authorized kubectl context/kubeconfig is available to run
  `portal/networkpolicy/inventory.py` against the live cluster. No policy apply or
  destructive probe attempted.
- Per known environment: cluster CLI access is normally via SSH to node-01
  (KUBECONFIG=/etc/kubernetes/admin.conf on that node) or via user BMC SOL/IPMI
  (port 623); neither is reachable/authorized from this host right now.
- Raw probe output: `cluster-connectivity.txt`.

## Conclusion
- Native PostgreSQL 17 qualification: **PASS (12/12)** — now EXECUTED (previously NOT_EXECUTED here).
- Live NetPol inventory: **NOT_EXECUTED (BLOCKED_EXTERNAL)** — no kubectl/kubeconfig and
  nodes unreachable over SSH from this host.
- P8C = NOT_FINAL_ACCEPTED. P8D–P8G/P9 = NOT_AUTHORIZED. No CI dispatch, no Owner
  helpers, no live policy apply, no production migration/deploy performed.
