VULNERABILITY_SECURITY_GATE = BLOCKED
Reason: 7 unreviewed CRITICAL + 64 HIGH (Trivy) + 73 reachable vulns (govulncheck).
Material concerns:
1) minio/minio itself has 2 CRITICAL (CVE-2026-33322, CVE-2026-33419) with NO fixed version (upstream archived).
2) Mandated go1.24.8 toolchain carries CRITICAL CVE-2025-68121 + many HIGH (fixed only in go1.24.9..1.24.13).
3) Multiple dependency CRITICAL/HIGH (grpc, rabbitmq/amqp091-go, x/crypto, x/net, x/text, ...).

STOP RULE (§17): Hermes may not accept material security risk. Any unreviewed CRITICAL => STOP.
DO NOT FORMAT /dev/vdb. DO NOT INSTALL MinIO.
ARCHITECT DECISION REQUIRED.
