# P7C Snapshot Controller Security Decision (final)

Call-path correction removed false positives:
- CVE-2026-42505 (crypto/tls ECH): ECH is NOT configured by client-go/controller
  => PRESENT_BUT_AFFECTED_FEATURE_UNUSED (not applicable).
- gRPC advisory: no gRPC server => NOT_APPLICABLE.
- OTel advisory: platform-specific (Darwin/BSD), Linux runtime => NOT_APPLICABLE.
- x509/pem/url stdlib: no untrusted input path => PRESENT_BUT_NOT_REACHABLE.

Only material residual: CVE-2026-33814 (x/net/http2) PRESENT_AND_REACHABLE_LOW_EXPOSURE
in v8.5.0 (HTTP/2 client to a trusted kube-apiserver); FIXED in v8.6.0.

SECURITY_GATE=GO_WITH_DOCUMENTED_ACCEPTED_RISK
SELECTED_CONTROLLER_VERSION=v8.5.0 (aligned with LINSTOR csi-snapshotter v8.5.0)
ARCHITECT_RISK_ACCEPTANCE_REQUIRED=YES
RESIDUAL_RISK=CVE-2026-33814 (x/net/http2) low exposure in v8.5.0 (fixed in v8.6.0)
VERSION_SKEW_ACCEPTANCE_REQUIRED=NO (v8.5.0 selected; skew NONE)

Hermes does NOT self-approve risk. Architect decision required.
