# P7C Snapshot Controller Security Ledger (17/17)

| CVE | Package | Affected feature | v8.5 status | v8.6 status | Severity |
|---|---|---|---|---|---|
| CVE-2026-25679 | net/url | IPv6 host literal | PRESENT_BUT_NOT_REACHABLE | PRESENT_BUT_NOT_REACHABLE | Med |
| CVE-2026-27139 | os | FileInfo Root escape | NOT_APPLICABLE | NOT_APPLICABLE | Med |
| CVE-2026-27142 | html/template | meta URL | NOT_APPLICABLE | NOT_APPLICABLE | Med |
| CVE-2026-29181 | otel | baggage DoS | NOT_APPLICABLE | NOT_APPLICABLE | High |
| CVE-2026-32280 | crypto/x509 | chain building | PRESENT_BUT_NOT_REACHABLE | PRESENT_BUT_NOT_REACHABLE | High |
| CVE-2026-32281 | crypto/x509 | policy validation | PRESENT_BUT_NOT_REACHABLE | PRESENT_BUT_NOT_REACHABLE | High |
| CVE-2026-32283 | crypto/tls | TLS 1.3 KeyUpdate | PRESENT_AND_REACHABLE_LOW_EXPOSURE | PRESENT_AND_REACHABLE_LOW_EXPOSURE | High |
| CVE-2026-32289 | html/template | JsBraceDepth | NOT_APPLICABLE | NOT_APPLICABLE | Med |
| CVE-2026-33186 | grpc | authz bypass | NOT_APPLICABLE | NOT_APPLICABLE | High |
| CVE-2026-33811 | net | CNAME crash | NOT_APPLICABLE | NOT_APPLICABLE | Med |
| CVE-2026-33814 | http2 | SETTINGS loop | PRESENT_AND_REACHABLE_LOW_EXPOSURE | FIXED | High |
| CVE-2026-39820 | net/mail | concat | NOT_APPLICABLE | NOT_APPLICABLE | Med |
| CVE-2026-39823 | html/template | XSS | NOT_APPLICABLE | NOT_APPLICABLE | Med |
| CVE-2026-39826 | html/template | XSS | NOT_APPLICABLE | NOT_APPLICABLE | Med |
| CVE-2026-39836 | net (Windows) | NUL byte | NOT_APPLICABLE | NOT_APPLICABLE | Med |
| CVE-2026-39883 | otel (BSD) | kenv | NOT_APPLICABLE | NOT_APPLICABLE | Med |
| CVE-2026-42499 | net/mail | concat | NOT_APPLICABLE | NOT_APPLICABLE | Med |

Evidence: osv.dev advisory data, go.mod dependency versions, call-path trace
(main.go, client-go v0.35/0.36, apimachinery util/net). Retrieval 2026-09-14.
