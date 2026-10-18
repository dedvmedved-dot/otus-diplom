VULNERABILITY_SECURITY_GATE=PASS
CRITICAL_RELEVANT=0; HIGH_REQUIRING_ACCEPTANCE=0; GOVULNCHECK_REACHABLE_CRITICAL=0.
Go 1.27.1 stdlib HIGH (CVE-2026-78667/78669/97031) are GONE (fixed by go1.27.2).
Remaining 5 x/net HIGH are DoS-only, reachable via internal client-side HTTP/2 + unused features (not the exposed S3 data path), fixed in x/net 0.60.0 (dependency update forbidden by ADR-008).
