# P7C Snapshot Controller Security Decision (R4-final)

Exhaustive 17-CVE ledger complete. No CRITICAL applicable.

v8.5.0: 2 High runtime-relevant (CVE-2026-32283 tls KeyUpdate, CVE-2026-33814 http2).
v8.6.0: 1 High runtime-relevant (CVE-2026-32283); CVE-2026-33814 fixed (x/net 0.54).
v8.6.0 also uses k8s.io/client-go v0.36.1 (K8s 1.36 exact match) vs v8.5.0 v0.35.0.

SECURITY_GATE=GO_WITH_DOCUMENTED_ACCEPTED_RISK
SELECTED_CONTROLLER_VERSION=v8.6.0
ARCHITECT_RISK_ACCEPTANCE_REQUIRED=YES (CVE-2026-32283)
VERSION_SKEW_ACCEPTANCE_REQUIRED=YES (v8.6 controller + v8.5 sidecar)
