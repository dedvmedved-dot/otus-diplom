# P8C #171 — private trust applicability before push + coherent cosign v3.1.3 signing config (review #170 rework)

Role: engineer (Hermes). Base: `main` @ `53dcd7fc91e53979df687f43578bd75e0ff9c9cc`.
PR #167 head (before this rework): `3cdc026c201e7ba731c86dc1ac150072b0314a73`.
Scope: fix the two blockers from review #170 in the PR #167 working branch; add
negative offline tests per blocker + a positive test with a REAL local fixture;
update the tools pin and the workflow blob; present the new head for re-review.
Merge to main and dispatch are NOT authorized. No image push / sign / attest /
release-lock / dispatch / rerun.

## Blockers fixed

### 1. Gate — parse the agreed signing config + a USABLE Sigstore trusted root (approved origins, coherence)
review #170 item 1: `forgejo_lock_gate.py:435-456` only tested URL prefixes and
the sha256 of non-empty bytes — it neither established approved service origins
nor parsed a usable Sigstore trusted root, and the positive fixture was not a
Sigstore root. `verify_keyless_trust_config` now:
- validates the policy-approved PRIVATE origins (https, non-empty,
  non-placeholder, non-public — any `*.sigstore.dev` host is refused) and the
  source-confirmed LITERAL OIDC issuer (`issuer_is_confirmed`);
- PARSES the agreed signing config (`signingconfig.v0.2` mediaType +
  caUrls/oidcUrls/rekorTlogUrls) and the pinned trusted root (`trustedroot v0.1`
  mediaType + at least one tlog with a public key + at least one certificate
  authority with a non-empty cert chain) — arbitrary bytes are no longer accepted;
- enforces APPROVED-ORIGIN COHERENCE: the signing config's caUrls/oidcUrls/
  rekorTlogUrls and the trusted root's CA URIs / tlog baseUrls must be EXACTLY
  the policy-approved private origins, so a foreign HTTPS origin is refused even
  when its digest matches the pin;
- verifies BOTH SHA-256 pins independently (authenticity), so an unfit root or a
  foreign origin is refused even with a correct digest.
The positive fixture is now a REAL Sigstore trusted root + coherent signing
config (`portal/tools/cosign_fixtures.py`), generated locally (real EC P-256
tlog public key + self-signed CA cert).

### 2. Workflow — coherent `--signing-config` + `--trusted-root` on all three signing paths
review #170 item 2: cosign v3.1.3's `--use-signing-config` DEFAULTS TO TRUE, so
explicit `--fulcio-url`/`--rekor-url`/`--oidc-issuer` on sign/attest are REJECTED
("cannot specify service URLs and use signing config"), and the signing path
omitted the pinned trusted root (silent public-TUF fallback). Fix:
- sign and BOTH attest commands now pass `--signing-config "$RUNNER_TEMP/signing-config.json"`
  + `--trusted-root "$RUNNER_TEMP/trusted-root.json"` + `--new-bundle-format`
  (no `--fulcio-url`/`--rekor-url`/`--oidc-issuer`); the private Fulcio/OIDC/Rekor
  origins come FROM the signing config, so there is no public/default fallback;
- verify/verify-attestation keep `--trusted-root` + `--rekor-url` + identity +
  issuer (the legacy verify loader, unaffected by the signing-config default);
- the "Verify private keyless trust configuration" step now ALSO reads the
  `PRIVATE_SIGNING_CONFIG` secret (never logged), writes it to a temp file, and
  passes `--signing-config-file`/`--signing-config-sha256`/`--oidc-issuer` to the
  gate check; new out-of-band pin `PRIVATE_SIGNING_CONFIG_SHA256`.
- Literal issuer/audience (`OIDC_ISSUER`/`OIDC_AUDIENCE`/`WORKFLOW_IDENTITY`) and
  the owner gates (admission barrier, owner-gate triple check) are UNCHANGED.

### 3. Offline loader check with ACTUAL parameters (not `--help`)
review #170: the prior 9 CLI checks only proved flag recognition (`--help`), not
runtime compatibility. New `TestCosignLoaderRuntime` in `test_cosign_cli_flags.py`
drives the ACTUAL cosign v3.1.3 binary (`signcommon.LoadTrustedMaterialAndSigningConfig`)
with real parameters:
- ACCEPTS a coherent `--signing-config` + `--trusted-root` + `--new-bundle-format`
  (no service URLs) — the failure, if any, is a later-stage error (reference
  parsing / image access / network), never a loader error;
- REJECTS a foreign HTTPS origin (`--fulcio-url` alongside `--signing-config` →
  "cannot specify service URLs and use signing config");
- REJECTS an unusable trusted root (non-Sigstore JSON → "loading trusted root").

## Pins (correct + reproducible)

- `PINNED_SOURCE_SHA = 4c09d6b4a85e2d021516244988f48b92eade7acf` (unchanged, accepted source)
- `PINNED_TOOLS_SHA = d4eea10a4508094bb209524f508e9c3062a46088` (new tools commit — carries the
  parsed signing-config/trusted-root gate + fixtures + tests + template)
- `PINNED_WORKFLOW_SHA` = carried OUT-OF-BAND as repo secret `POLICY_WORKFLOW_SHA` (never embedded)
- Workflow blob (git) = `de7a68f527c5612de4fa947aa9dbdf6779ef9535`
  (sha256 `f3da0f5076263b5ce1c41feaabcc3b19e7e2d44fc11ffbb29078210f020b9de6`);
  template and published workflow are byte-identical (one blob).

## Offline checks (positive + negative)

Full forgejo offline suite: **196 tests OK** (`test_forgejo_lock_gate` 89 +
`test_forgejo_offline_integration` 38 + `test_owner_gate_barrier` 69) +
`check_forgejo_workflow_syntax.py` VERIFIED (4 jobs, 29 release steps, 109
expressions balanced) + `test_cosign_cli_flags` **12 OK** (9 CLI-flag checks +
3 loader-runtime checks, cosign v3.1.3).

Named negative checks added per blocker:
- **Blocker 1 (approved origins + usable root, even with a correct digest)**:
  `test_public_sigstore_fulcio_url_rejected`,
  `test_foreign_origin_signing_config_rejected_even_with_correct_digest`,
  `test_foreign_oidc_issuer_rejected`,
  `test_unfit_root_rejected_even_with_correct_digest`,
  `test_root_not_a_sigstore_root_rejected`,
  `test_signing_config_sha_mismatch_rejected` — a foreign origin / an unfit root /
  a non-Sigstore root is refused even when its SHA-256 matches the pin.
- **Blocker 2 (coherent signing config, no service URLs on sign/attest)**:
  `test_sign_attest_use_signing_config_not_service_urls` (3× `--signing-config`,
  1× `--fulcio-url`/`--oidc-issuer` = gate policy input only, 4× `--rekor-url` =
  verify/verify-attestation + gate) + `test_no_public_sigstore_fallback`.
- **Blocker 3 (loader runtime, not --help)**:
  `test_loader_accepts_coherent_signing_config_and_root`,
  `test_loader_rejects_foreign_https_origin`,
  `test_loader_rejects_unusable_root` (actual cosign v3.1.3 binary).

Positive with local fixtures:
- `test_valid_private_trust_config` — a REAL Sigstore trusted root + coherent
  signing_config.v0.2 (both bound to the approved private origins) accepted by the
  same `verify_keyless_trust_config` the workflow CLI drives (exit 0).
- `test_positive_allowed_with_confirmed_trust` / `test_positive_allowed` /
  `test_positive_writes_scratch_lock_pair` — still allowed only with literal SAN +
  literal issuer + literal sigstore audience + confirmed trust.

## Boundaries honoured

- No merge to main, no dispatch/rerun, no image push, no sign/attest, no lock write.
- `admission → test → preflight → release` preserved; operational admission barrier
  NOT marked complete (operator closes `otus-diplom-admission` issuance before the
  future dispatch, gate bound to returned run id / attempt=1, PUT 201/204).
- Private Fulcio/Rekor/TUF NOT assumed deployed; `oidc_trust_confirmed` stays false
  and the workflow refuses fail-closed before push when the private materials are
  absent or foreign. No public-sigstore fallback (enforced in code + loader).

Raw transcript: `offline-forgejo-suite.txt` (same directory).
Runner: `run-forgejo-suite.sh` (same directory).

PR head SHA: reported externally in the review issue (this file predates its own commit).
