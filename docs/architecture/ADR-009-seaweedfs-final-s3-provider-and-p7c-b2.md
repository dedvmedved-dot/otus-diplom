# ADR-009 — SeaweedFS final S3 provider + P7C-B2 authorization

STATUS: ACCEPTED
ACCEPTED_BY: Chief Architect / Technical Authority
ACCEPTED_DATE: 2026-10-19
SOURCE_TASK: P7C-B2-R1

## Decision

FINAL_S3_PROVIDER = SeaweedFS 4.48
SOURCE_COMMIT = 530be3e37337488ecc34d58441e0bc476e121c93
RUNTIME_BUILD = exact SeaweedFS 4.48 source rebuilt with Go 1.27.2
RUNTIME_BINARY_SHA256 = f3cd51efeb90f86e8fa82febfb007c56798ea687752af4d527c478b45d8a6dc9

SCOPE = DEMO / NON-PRODUCTION

P7C-B2 = AUTHORIZED
P7C-C = NOT AUTHORIZED
P8 = NOT AUTHORIZED
P9 = NOT AUTHORIZED

## Compensating control (preserved)

SeaweedFS master/filer/volume/gRPC/admin interfaces MUST remain non-public.
Only S3 HTTPS/443 is permitted from backup clients.
Any future enablement of currently-unused x/net-affected paths requires a new security assessment.

## Stage-split refinement (P7C)

P7C-B2 = Velero/S3 runtime foundation + one controlled end-to-end CSI Snapshot Data Movement backup/restore canary.
P7C-C = failure injection, repeated restore validation, failure/recovery scenarios, broader operational validation.

Reason: a single data-movement canary proves the P7C-B2 foundation actually reaches external S3 from the real Velero/node-agent execution path.
