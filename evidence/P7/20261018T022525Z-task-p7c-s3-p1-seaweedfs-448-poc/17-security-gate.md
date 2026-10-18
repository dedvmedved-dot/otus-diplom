VULNERABILITY_SECURITY_GATE = PASS (pending govulncheck corroboration)
CRITICAL = 0 (binary, go1.27.1). HIGH = 4 (DoS-only, all fixed in go1.27.2).
Disposition: 4 HIGH are availability-only DoS in the Go HTTP/TLS stack, fixed in the
immediately-available go1.27.2 patch; no confidentiality/integrity or immutability impact.
govulncheck (source-level) run for §17 compliance.
