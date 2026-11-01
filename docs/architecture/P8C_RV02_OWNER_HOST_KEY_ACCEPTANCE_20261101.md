# P8C-R1 RV-02 — Owner host-key attestation accepted

Date: 2026-11-01 (Europe/Moscow).
Recovery main: fc584690a2b47b7c42933c3722ceec424f4f90bf (Connector verified).
Supplement to docs/architecture/P8C_RV02_REVIEW_97cdf17_20261101.md.

Evidence: evidence/P8/20261101T191926Z-p8c-rv02-owner-host-key/owner-attestation.md.

## Decision
```text
HOST_KEY_TRUST=ACCEPTED_OWNER_OUT_OF_BAND_ATTESTATION
EXPECTED_TARGET=node-01 / 192.168.194.38
EXPECTED_ED25519=SHA256:4Janc/G5wzV6Yfi8gPTz55u/81atXF1xzjkDIISJjvc
SAFE_AUTH_METHOD=BLOCKED_EXTERNAL / NOT_YET_CONFIRMED
ACCESS_COMPLIANCE=PARTIAL (host-key prerequisite closed; authentication outstanding)
FOLLOWUP_SOURCE=ACCEPTED_PREVIOUSLY / NOT_REOPENED
PHASE2_NEW_RUN_APPROVED=NO
OWNER_PHASE2_HANDOFF_ALLOWED=NO
NETPOL_APPROVED_FOR_APPLY=NO
P8C=NOT_FINAL_ACCEPTED
P8D–P8G/P9=NOT_AUTHORIZED
```

The Owner explicitly reports trusted-console verification at2026-11-01T19:19:26Z.
The expected ED25519 value matches the prior SSH report. This closes the out-of-band host-key
prerequisite on the basis of Owner attestation; no further console repetition is needed
unless the host identity/key changes. The Architect did not execute the live commands.

Remaining Owner information (no secrets): whether the authentication credential/key intended
for primary Hermes is authorized, not previously exposed, available through an approved secure
mechanism, and which account/method is intended. Prior successful astraadm password login
alone does not establish that credential safety or availability to Hermes.
Do not send the password/private key/token/kubeconfig through chat or Git.
No further source-development or accepted-test rerun is required.

This update is NOT a live gate and does not authorize script transfer/run, new SSH/cluster
reads, key provisioning, NetPol apply, CI/workflow/token, helpers, migrations or deployment.
Existing one-run budget remains consumed. A future explicit gate must bind the actual operator,
account, permitted privilege use, pinned package and scope; do not infer approval automatically.
