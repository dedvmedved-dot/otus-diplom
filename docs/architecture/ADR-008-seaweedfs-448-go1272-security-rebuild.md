# ADR-008 — SeaweedFS 4.48 Go 1.27.2 security rebuild

STATUS: ACCEPTED FOR SECURITY REMEDIATION
ACCEPTED_BY: Chief Architect / Technical Authority
ACCEPTED_DATE: 2026-10-18
SOURCE_TASK: P7C-S3-P1-R1

## Decision

SeaweedFS version remains: 4.48
Source tag remains: 4.48
Source commit remains: 530be3e37337488ecc34d58441e0bc476e121c93

Only build toolchain changes:
FROM: Go 1.27.1 (used by official release binary)
TO:   Go 1.27.2

Reason: security remediation of known Go runtime/library HIGH vulnerabilities
with fixes available in Go 1.27.2.

## Explicitly recorded

- NO SEAWEEDFS SOURCE PATCHES
- NO DEPENDENCY UPGRADES
- NO go get -u
- NO go.mod CHANGE
- NO go.sum CHANGE

## Remediation result (P7C-S3-P1-R1)

REMEDIATION_RESULT: PASS
RUNTIME_BINARY: SeaweedFS 4.48 exact source commit rebuilt with Go 1.27.2
SOURCE_COMMIT: 530be3e37337488ecc34d58441e0bc476e121c93
NEW_BINARY_SHA256: f3cd51efeb90f86e8fa82febfb007c56798ea687752af4d527c478b45d8a6dc9
FINAL_RUNTIME_PROVIDER: SeaweedFS 4.48 — FINAL ACCEPTED FOR DEMO PAK
