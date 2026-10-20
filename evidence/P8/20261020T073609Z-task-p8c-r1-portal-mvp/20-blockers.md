STOP at G3 — minimal Architect decisions required:
1. BLOCKED_NETWORKPOLICY_BASELINE — portal namespace has no default-deny;
   safe introduction needs full existing-flow inventory (CNPG/Velero/Barman).
2. BLOCKED_SUPPLY_CHAIN — registry push access to ghcr.io/dedvmedved-dot/otus-diplom-portal
   and Cosign signing identity (protected key/KMS/keyless) not available/verified.
3. BLOCKED_AUTH_HANDOFF — no secure mechanism to deliver the 32-byte operator
   password SHA-256 verifier to the Owner (per §6).
Runtime (G4-G7) not started until these are resolved.
