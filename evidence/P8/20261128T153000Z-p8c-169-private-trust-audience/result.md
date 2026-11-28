# P8C #169 — pin literal issuer+audience, bind keyless ops to private trust chain (review #168 rework)

Role: engineer (Hermes). Base: `main` @ `53dcd7fc91e53979df687f43578bd75e0ff9c9cc`.
PR #167 head (before this rework): `b8da2b096f8829359f3da7916ef1c4375261116a`.
Scope: fix the three blockers from review #168 in the PR #167 working branch; add
negative offline tests per blocker + a positive test with local fixtures; update
the tools pin and the workflow blob; present the new head for re-review.
Merge to main and dispatch are NOT authorized. No image push / sign / attest /
release-lock / dispatch / rerun.

## Blockers fixed

### 1. Gate — literal issuer + audience (forgejo_lock_gate.py:912–914,991,1457–1469)
The expected audience (and issuer) were overridable via bindings/CLI, and Stage 4
compared the evidence value against that overridable binding only — a matching
WRONG pair (binding + evidence both foreign) passed. Fix:
- `audience_is_confirmed()` and `issuer_is_confirmed()` now match the LITERAL
  `sigstore` and `https://git.aiopslab.online/api/actions` by exact string
  equality (mirroring `identity_is_confirmed`), no regex, no diagnostic branch.
- Stage 4 literal-checks the binding AND (for issuer) the evidence BEFORE the
  equality comparison, so a wrong-but-consistent override is refused fail-closed.
- The token audience is now a pure POLICY value: it is NOT read from evidence
  (it is not carried by the certificate and the token is never logged/saved), so
  there is no per-run audience observation to compare against.

### 2. Workflow — audience bound on all three keyless operations
- `--oidc-client-id "$OIDC_AUDIENCE"` is now passed to BOTH `cosign attest`
  commands (spdxjson + slsaprovenance) as well as `sign` — the actual token
  audience is bound for all three operations, never left to a default.
- The evidence bundle no longer emits `certificate_audience` (previously an
  env-policy copy presented as an observation); the gate enforces the literal
  sigstore audience from policy only. Tokens are never logged or saved.

### 3. Workflow — private trust chain verified fail-closed (no public fallback)
- New gate mode `keyless-trust-check` (`verify_keyless_trust_config`): the
  PRIVATE Fulcio/Rekor/TUF materials must be PRESENT, AUTHENTIC (trust root
  SHA-256 pinned out-of-band) and applicable before sign/attest/verify. A
  missing/placeholder/non-https endpoint, a missing/empty trust root, or a
  mismatched SHA refuses the release fail-closed BEFORE any build/push/sign.
- New release step "Verify private keyless trust configuration (fail-closed, no
  public fallback)" reads the `PRIVATE_TRUST_ROOT` secret (never logged), writes
  it to a temp file, and runs the gate check. Until the separate private
  deployment, the release refuses here unconditionally.
- sign/attest now pass `--fulcio-url`/`--rekor-url`/`--oidc-issuer` (pinned
  cosign v3.1.3 mechanism) and verify/verify-attestation pass
  `--rekor-url`/`--trusted-root`, so cosign cannot fall back to public sigstore.
  The absence of a public fallback is enforced by CODE, not a comment.

## Pins (correct + reproducible)

- `PINNED_SOURCE_SHA = 4c09d6b4a85e2d021516244988f48b92eade7acf` (unchanged, accepted source)
- `PINNED_TOOLS_SHA = 0511b4674cd4239362be9602fa354ce587c0a9ff` (new tools commit — carries the
  literal issuer/audience gate + keyless-trust-check + tests + template)
- `PINNED_WORKFLOW_SHA` = carried OUT-OF-BAND as repo secret `POLICY_WORKFLOW_SHA` (never embedded)
- Workflow blob (git) = `8f47086b381cf29adeb2d576cf72663dd39d33da`
  (sha256 `ee74a8fe52224a204e3169e92fce358bce3d5aeae29b77764329f4632c6ac35e`);
  template and published workflow are byte-identical (one blob).

## Offline checks (positive + negative)

Full forgejo offline suite: **191 tests OK** (`test_forgejo_lock_gate` 89 +
`test_forgejo_offline_integration` 38 + `test_owner_gate_barrier` 64) +
`check_forgejo_workflow_syntax.py` VERIFIED (4 jobs, 29 release steps, 115
expressions balanced) + `test_cosign_cli_flags` 9 OK (cosign v3.1.3).

Named negative checks added per blocker:
- **Blocker 1 (matching-wrong audience/issuer)**:
  `test_wrong_audience_rejected`, `test_foreign_binding_audience_rejected_even_with_matching_evidence`,
  `test_foreign_binding_issuer_rejected_even_with_matching_evidence`,
  `test_certificate_audience_mismatch_not_allowed` — all refuse a foreign
  audience/issuer even when the overridable binding (and a stale evidence value)
  agree.
- **Blocker 2 (audience on all three ops, not an observation)**:
  `test_attest_commands_request_literal_audience` (3× `--oidc-client-id`),
  `test_evidence_bundle_does_not_emit_audience` — both attestations request the
  literal sigstore audience and the evidence bundle no longer emits an audience.
- **Blocker 3 (private trust chain fail-closed)**:
  `TestKeylessTrustConfig` (placeholder/non-https Fulcio URL, placeholder Rekor
  URL, missing/empty trust root, SHA mismatch → all refused) + workflow
  structure `test_private_keyless_trust_step_present` and
  `test_no_public_sigstore_fallback` (no `fulcio.sigstore.dev`/`rekor.sigstore.dev`
  as a cosign target; private endpoints + trusted root passed explicitly).

Positive with local fixtures:
- `test_valid_private_trust_config` — a real temp trust-root file + its correct
  sha256 is accepted (exit 0) via the same `verify_keyless_trust_config` the
  workflow CLI drives.
- `test_positive_allowed_with_confirmed_trust` / `test_positive_allowed` /
  `test_positive_writes_scratch_lock_pair` — still allowed only with literal SAN
  + literal issuer + literal sigstore audience + confirmed trust.

## Boundaries honoured

- No merge to main, no dispatch/rerun, no image push, no sign/attest, no lock write.
- `admission → test → preflight → release` preserved; operational admission barrier
  NOT marked complete (operator closes `otus-diplom-admission` issuance before the
  future dispatch, gate bound to returned run id / attempt=1, PUT 201/204).
- Private Fulcio/Rekor/TUF NOT assumed deployed; `oidc_trust_confirmed` stays false
  until those trust roots are deployed (separate order), and the workflow now
  refuses fail-closed before push when the private materials are absent. No
  public-sigstore fallback (enforced in code).

Raw transcript: `offline-forgejo-suite.txt` (same directory).

PR head SHA: reported externally in the review issue (this file predates its own commit).
