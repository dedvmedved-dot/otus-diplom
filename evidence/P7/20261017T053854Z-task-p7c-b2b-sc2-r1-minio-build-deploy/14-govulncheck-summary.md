govulncheck = v1.9.0 (go install golang.org/x/vuln/cmd/govulncheck@v1.9.0)
RESULT: "Your code is affected by 73 vulnerabilities from 8 modules and the Go standard library"
  + 17 vulnerabilities in imported packages (not called)
  + 20 vulnerabilities in required modules (not called)
Examples reachable: GO-2025-4007 (crypto/x509 quadratic name-constraint, fixed go1.24.9),
GO-2025-4134 (x/crypto/ssh unbounded memory, fixed v0.45.0), ... (73 total reachable)
