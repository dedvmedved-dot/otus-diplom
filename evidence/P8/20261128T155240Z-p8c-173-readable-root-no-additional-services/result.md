# P8C #173 — readable private root before push + split origin-policy / cosign-loader checks (review #172 rework)

Role: engineer (Hermes). Base: `main` @ `53dcd7fc91e53979df687f43578bd75e0ff9c9cc`.
PR #167 head (before this rework): `16cf505132ae5e830ca72980b7af49244cb9cc2a`
(tools `d4eea10a4508094bb209524f508e9c3062a46088`, workflow blob
`de7a68f527c5612de4fa947aa9dbdf6779ef9535`).
Scope: fix the two blockers from review #172 in the PR #167 working branch; add
negative offline tests per blocker + strengthen the positive loader test; update
the tools pin and the workflow blob; present the new head for re-review.
Merge to main and dispatch are NOT authorized. No image push / sign / attest /
release-lock / dispatch / rerun.

## Blockers fixed

### 1. Readable cert/key material before push + forbid unapproved additional services
review #172 item 1: `forgejo_lock_gate.py:510-527` only checked that the
certificate / tlog public key `rawBytes` was a non-empty string — the correct
SHA merely fixes the transmitted bytes, so an unreadable cert/key at the right
digest was accepted, and cosign's first actual LOAD of those files happened only
AFTER the `:candidate` push. Also `forgejo_lock_gate.py:474-491` did not restrict
additional signing-config services (e.g. a Timestamp Authority). Fixes:

- `_validate_trusted_root` now PARSES every certificate `rawBytes` and every tlog
  public-key `rawBytes` as a real base64-DER structure (a minimal ASN.1/DER
  skeleton check in pure Python: outer SEQUENCE wrapping tbsCertificate
  [0]+INTEGER+5×SEQUENCE for certs, SEQUENCE wrapping AlgorithmIdentifier+BIT
  STRING for keys). A structurally-correct trusted root whose cert/key is
  unreadable garbage is refused with "no readable certificate chain (unfit)" /
  "not a readable key (unusable)" — BEFORE any push/sign, even when its SHA-256
  matches the pin.
- `_validate_signing_config` now forbids unapproved ADDITIONAL services: a
  non-empty `tsaUrls` list, a non-empty `tsaConfig` selector, and (in
  `_validate_trusted_root`) non-empty `ctlogs` / `timestampAuthorities` are all
  refused fail-closed. The private chain approves ONLY Fulcio / OIDC / Rekor.
- The "Verify private keyless trust configuration" step already runs BEFORE
  registry login/push, on the SAME files cosign later loads (`$RUNNER_TEMP/
  signing-config.json` + `trusted-root.json`), with NO network access and NO
  signing; the gate now ALSO proves loader suitability there (readable
  cert/key + no additional services). The positive fixture
  (`cosign_fixtures.py`) was made the canonical "no TSA" shape (`tsaConfig: {}`).

### 2. Runtime test checked the wrong failure — now split policy vs loader-compat
review #172 item 2: `test_loader_rejects_foreign_https_origin` left the JSON
approved and added `--fulcio-url`, so it proved cosign's FLAG incompatibility
("cannot specify service URLs and use signing config"), NOT the ban on a foreign
origin INSIDE the JSON. The positive test only asserted the ABSENCE of four
loader messages (the independent run had already reached registry access, but the
test did not require it). The negative root test used an unknown proto field, not
a structurally-correct root with an unreadable cert/key. Fixes:

- ORIGIN-POLICY half (gate, unit-tested in `test_owner_gate_barrier.py`): a
  foreign URL INSIDE the signing-config JSON with NO CLI override is refused
  (`test_signing_config_tsa_urls_rejected`,
  `test_signing_config_tsa_selector_rejected`,
  `test_foreign_origin_signing_config_rejected_even_with_correct_digest` — the
  last pre-existing). The foreign-origin / additional-service ban is enforced by
  the GATE, never by cosign's loader (which loads foreign URLs fine).
- LOADER-COMPATIBILITY half (`test_cosign_cli_flags.py`, actual cosign v3.1.3):
  * the coherent pair now REQUIRES a POSITIVE observable loader pass — the
    command must reach the image-access stage (`"accessing image" in out`), NOT
    merely avoid loader errors;
  * a STRUCTURALLY-CORRECT root with an unreadable cert / tlog key (garbage
    base64, correct structure) is rejected by the loader
    (`test_loader_rejects_unreadable_certificate`,
    `test_loader_rejects_unreadable_tlog_key`);
  * the explicit `--fulcio-url` alongside `--signing-config` flag rejection is
    kept as a distinct loader-compat observation
    (`test_loader_rejects_explicit_service_url_alongside_signing_config`).

## Pins (correct + reproducible)

- `PINNED_SOURCE_SHA = 4c09d6b4a85e2d021516244988f48b92eade7acf` (unchanged, accepted source)
- `PINNED_TOOLS_SHA = c4eee31a561b021abea31eb1f09e7f84d6fbd8bd` (new tools commit — carries the
  readable cert/key + no-additional-service gate + fixtures + tests + template)
- `PINNED_WORKFLOW_SHA` = carried OUT-OF-BAND as repo secret `POLICY_WORKFLOW_SHA` (never embedded)
- Workflow blob (git) = `afe900c90642f16e87726d4e2e2604bfc5d36164`
  (sha256 `c979758e84644a89ef5e9143e4e8506ad9d630b25e5245f54b7118c6e969538b`);
  template and published workflow are byte-identical (one blob).

## Offline checks (positive + negative)

Full forgejo offline suite: **201 tests OK** (`test_forgejo_lock_gate` 89 +
`test_forgejo_offline_integration` 38 + `test_owner_gate_barrier` 74) +
`check_forgejo_workflow_syntax.py` VERIFIED (4 jobs, 29 release steps, 109
expressions balanced) + `test_cosign_cli_flags` **13 OK, 0 skips** (9 CLI-flag +
4 loader-runtime, cosign v3.1.3).

Named negative/positive checks added per blocker:
- **Blocker 1 (readable material + no additional services, even at correct digest)**: gate tests
  `test_unreadable_certificate_rejected_even_with_correct_digest`,
  `test_unreadable_tlog_key_rejected_even_with_correct_digest`,
  `test_signing_config_tsa_urls_rejected`, `test_signing_config_tsa_selector_rejected`,
  `test_trusted_root_additional_service_rejected`.
- **Blocker 2 (policy vs loader split)**: policy half
  `test_foreign_origin_signing_config_rejected_even_with_correct_digest` (foreign URL inside JSON,
  no CLI override) vs loader-compat half `test_loader_accepts_coherent_signing_config_and_root`
  (observable "accessing image" pass), `test_loader_rejects_unreadable_certificate`,
  `test_loader_rejects_unreadable_tlog_key`.
- Positive still allowed only with literal SAN + literal issuer + literal sigstore
  audience + confirmed trust (`test_valid_private_trust_config` and the owner-gate
  positives are unchanged).

## Boundaries honoured

- No merge to main, no dispatch/rerun, no image push, no sign/attest, no lock write.
- `admission → test → preflight → release` preserved; operational admission barrier
  NOT marked complete.
- Private Fulcio/Rekor/TUF NOT assumed deployed; `oidc_trust_confirmed` stays false
  and the workflow refuses fail-closed before push when the private materials are
  absent, foreign, unreadable, or carry an unapproved additional service.

Raw transcript: `offline-forgejo-suite.txt` (same directory).
Runner: `run-forgejo-suite.sh` (same directory).

PR head SHA: reported externally in the review issue (this file predates its own commit).
