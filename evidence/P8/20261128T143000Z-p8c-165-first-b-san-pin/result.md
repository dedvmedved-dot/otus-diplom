# P8C #165 — First B: pin literal SAN + audience, present workflow for re-review

Role: engineer (Hermes). Base: `main` @ `53dcd7fc91e53979df687f43578bd75e0ff9c9cc`.
Owner decision basis: issue #162 comment 12512 (2026-11-28 13:14 UTC).
Scope: prepare publication in a working branch + PR ONLY. Merge to main and
dispatch are NOT authorized. No image push / sign / attest / lock.

## What was changed

1. **Literal SAN pinned** in BOTH the gate and the template (no regex, no
   diagnostic branch, no placeholder):
   `WORKFLOW_IDENTITY = repo:aiopslab/otus-diplom:ref:refs/heads/main`
   (format `repo:{repository}:ref:{ref}`, no event suffix, no diagnostic sub).
2. **Token audience pinned** to the literal `sigstore`
   (`OIDC_AUDIENCE = "sigstore"`), enforced by the gate fail-closed; the keyless
   sign step passes `--oidc-client-id "$OIDC_AUDIENCE"`.
3. **Exact issuer** unchanged and source-confirmed:
   `https://git.aiopslab.online/api/actions`.
4. `identity_is_confirmed()` now matches the literal SAN by EXACT string equality
   (previously it only rejected a placeholder). A foreign / near-miss SAN is
   rejected before push/sign.
5. `decide_lock_update` Stage 4 additionally cross-checks
   `evidence.certificate_audience == "sigstore"` (added `OIDC_AUDIENCE` constant,
   `BINDINGS["audience"]`, `--audience` CLI flag, `certificate_audience` evidence
   field).
6. Final template copied byte-identical into `.forgejo/workflows/p8c-portal-forgejo-release.yml`.

## Pins (correct + reproducible)

- `PINNED_SOURCE_SHA = 4c09d6b4a85e2d021516244988f48b92eade7acf` (unchanged, accepted source)
- `PINNED_TOOLS_SHA = 3395d0cca3475efc1c4df910c1188bc5fe9db2d5` (tools commit — carries the
  SAN-pinned gate + tests + CUE policies + template)
- `PINNED_WORKFLOW_SHA` = carried OUT-OF-BAND as repo secret `POLICY_WORKFLOW_SHA` (never embedded)
- Workflow blob (git) = `46f8bdc9956655f065a54f3e09540357034cc7f1`
  (sha256 `007518053e4492290f5a946e10eff68a0fd4ea2263b3ac1d86a98f9ee3e43cf9`)

## Offline checks (positive + negative)

Full forgejo offline suite: **177 tests OK** (`test_forgejo_lock_gate` 89 +
`test_forgejo_offline_integration` 38 + `test_owner_gate_barrier` 50) +
`check_forgejo_workflow_syntax.py` VERIFIED (4 jobs, 97 expressions balanced) +
`test_cosign_cli_flags` 5 OK (cosign v3.1.3).

Named negative checks required by the order:
- **Foreign SAN** (чужой SAN): `test_wrong_identity_rejected`,
  `test_evidence_foreign_identity_rejected`,
  `test_foreign_binding_identity_rejected_even_with_confirmed_trust` — all reject.
- **No trust** (отсутствие trust): `test_trust_not_confirmed_blocks` — rejects.
- **Wrong gate binding** (неверная привязка gate): owner-gate replay/expiry/foreign/
  unconfirmed-actor + observed repo/ref/workflow-sha mismatch tests — all reject.
- **Wrong audience**: `test_wrong_audience_rejected`,
  `test_certificate_audience_mismatch_not_allowed` — reject non-sigstore audience.

Positive: `test_positive_allowed`, `test_positive_allowed_with_confirmed_trust`,
`test_positive_writes_scratch_lock_pair` — allowed only with literal SAN + sigstore
audience + confirmed trust.

## Boundaries honoured

- No merge to main, no dispatch/rerun, no image push, no sign/attest, no lock write.
- `admission → test → preflight → release` preserved; operational admission barrier
  NOT marked complete (operator closes `otus-diplom-admission` issuance before the
  future dispatch, gate bound to returned run id / attempt=1, PUT 201/204).
- Private Fulcio/Rekor/TUF NOT assumed deployed; `oidc_trust_confirmed` stays false
  until those trust roots are deployed (separate order). NO public-sigstore fallback.

Raw transcript: `offline-forgejo-suite.txt` (same directory).

PR head SHA: reported externally in the review issue (this file predates its own commit).
