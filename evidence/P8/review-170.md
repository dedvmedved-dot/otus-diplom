# Architect review #170 — REQUEST CHANGES

PR #167, head `3cdc026c201e7ba731c86dc1ac150072b0314a73`, base `53dcd7fc91e53979df687f43578bd75e0ff9c9cc`. Template and published workflow share blob `8f47086b381cf29adeb2d576cf72663dd39d33da`. Tools pin `0511b4674cd4239362be9602fa354ce587c0a9ff`; gate unchanged between pin and reviewed head.

Stage 4 checks literal issuer and audience even for matching foreign bindings. All three signing calls specify `--oidc-client-id`. Audience is policy, not an observed certificate property; no token evidence is required or retained. Accepted for these two review items.

Private trust: not accepted. References below are to the reviewed head.

1. `portal/tools/forgejo_lock_gate.py:435-456` checks URL prefixes and the digest of nonempty bytes, but does not establish approved service origins or parse a usable Sigstore trusted root. The positive fixture (`portal/tools/test_owner_gate_barrier.py:375-389`) is not a Sigstore root. This check precedes the candidate push but cannot establish applicability.
2. `.forgejo/workflows/p8c-portal-forgejo-release.yml:644-648,678-685`: sign and both attest calls mix explicit service URLs with cosign v3.1.3's default signing-config mode, a rejected combination; they also omit the pinned trusted root on the signing path. Candidate push (line 590) precedes this failure. See [cosign v3.1.3 signing loader](https://github.com/sigstore/cosign/blob/v3.1.3/cmd/cosign/cli/signcommon/common.go). No public connection is asserted to have occurred.

Acceptance: pin and validate a coherent private signing config and root before build/push, use them on all three signing paths and validate verification inputs. Prove offline that the pinned loader accepts the actual config/arguments, rejects unapproved origins and unusable roots even with matching digests, and needs no public defaults. Keep owner gates and placeholders closed until real private material is approved.

Independent offline rerun: Python 3.12.3; 191/191 gate/integration/barrier tests, workflow syntax verified (4 jobs, 29 release steps, 115 expressions), 9/9 cosign v3.1.3 CLI checks. CLI help checks validate flag recognition, not runtime compatibility. No merge, dispatch/rerun, image push, sign/attest or release-lock.
