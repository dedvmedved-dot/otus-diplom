# P8C-RV02-LIVE-COMPATIBILITY-FIX — residual corrections LC-01/LC-02/LC-03

Date: 2026-11-02 (UTC). Source-only offline correction per review f20f57f. No live/SSH/registry
access, no new gate consumption. Accepted raw GET, Calico schema pin, named ports and host-bit
preservation are NOT reopened.

## LC-01 — explicit null `continue` blocked
`_read_podlist` now uses an explicit presence check (`'continue' in meta`) instead of
`meta.get()`, so absent and explicit null are no longer collapsed:
- absent `continue` or explicit empty string → permitted;
- present `null`, `bool`, number, list, object → PARSE_ERROR `COMPLETENESS`, complete=false,
  empty output, zero identity-dependent reads;
- nonempty string → incomplete/PARSE_ERROR `COMPLETENESS` (as before). No token/raw value emitted.

## LC-02 — Kubernetes CEL isCIDR semantics
`_valid_cidr` no longer delegates to Python `ip_network`; it implements the pinned CEL
`isCIDR` = Go `netip.ParsePrefix` + explicit `Is4In6` rejection:
- exactly one slash; ASCII decimal prefix `0|[1-9][0-9]*` (rejects leading zeros / netmask);
- no zone IDs; no IPv4-mapped IPv6; IPv4 prefix ≤32, IPv6 ≤128;
- `_networks` restores `maxLength 43` at the schema-validation layer;
- host bits remain permitted and original strings are preserved; duplicate-set and array bounds kept.
Six reproduced false-acceptances now all → PARSE_ERROR (dotted netmask, dotted hostmask, zone,
mapped-v6, leading-zero prefix, 49-char length).

## LC-03 — documentation/provenance
- `followup-read-design.md`: Calico manifest named as the CURRENT CNP spec authority
  (blob 21ea9b4b…, commit dd00e2f…, hash ff433d34…); the network-policy-api candidate is labelled
  HISTORICAL; "pinned hash remains unchanged" replaced with "normalizer unchanged, pin is now the
  Calico manifest value".
- `coverage-matrix.md`: added residual-correction rows + `TestManifestProvenance`
  (manifest extraction/hash matches pin; old candidate hash differs).

## Tests
```text
followup_test.py: 122/122 PASS  (TestCompatibilityRemaining + TestManifestProvenance added)
supplemental_test.py: 36/36 PASS (unchanged)
supplied compatibility_regression_test.py: 4/4 PASS (LC-01/LC-02 + controls)
Python 3.11.15
START_UTC=2026-11-02T01:26:37Z · END_UTC=2026-11-02T01:26:40Z
```

## File hashes
```text
followup.py:      blob 6dbfad124a486b0f2d6eccb791777608918fac35  sha256 fc78d03af06f60bbcdde967810ee65a28f37df96a0d85a003807f097fa179e2b
followup_test.py: blob 84630d557f5cb527c623f28f71dcec9ee5a33ed1  sha256 c912db861c7dd5b0b8c8b89f4f905e61251585fa258c36d872c9ad7a4d23325c
```

## Status
```text
REVIEW_HEAD (parent): f20f57f8da94bf0bed81a29d4323de6887b56b72
ACTUAL_PARENT: 65d4676e363bfe5e60214c29828bfea447a8cebb
FOLLOWUP_SOURCE_COMPATIBILITY: FIXED (LC-01/LC-02/LC-03)
PHASE2_NEW_RUN_APPROVED=NO
NETPOL_APPROVED_FOR_APPLY=NO
P8C=NOT_FINAL_ACCEPTED · P8D–P8G/P9=NOT_AUTHORIZED
```
STOP for independent Architect review. No live rerun authorized.
