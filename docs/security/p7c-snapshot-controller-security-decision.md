# P7C Snapshot Controller Security Decision

Neither v8.5.0 nor v8.6.0 fully clears the security gate (CVE-2026-42505 Go
crypto/tls remains applicable in both).

- v8.5.0: go 1.25.5 -> CVE-2026-42505 applicable; x/net 0.49.0 -> CVE-2026-33814 applicable (2 high).
- v8.6.0: go 1.26.0 -> CVE-2026-42505 applicable; x/net 0.54.0 -> CVE-2026-33814 fixed (1 high).

Comparison: v8.6.0 reduces applicable CVEs but introduces version skew vs LINSTOR
csi-snapshotter v8.5.0 and does not fix CVE-2026-42505.

SECURITY_GATE=GO_WITH_DOCUMENTED_ACCEPTED_RISK
SELECTED_CONTROLLER_VERSION=v8.5.0 (aligned; skew NONE)
ARCHITECT_RISK_ACCEPTANCE_REQUIRED=YES
RISK_ITEMS=CVE-2026-42505 (crypto/tls High), CVE-2026-33814 (x/net High, fixed only in v8.6)

Hermes does NOT self-approve risk. Runtime exposure is reduced (in-cluster
controller, no network-exposed server surface), but acceptance belongs to Architect.
