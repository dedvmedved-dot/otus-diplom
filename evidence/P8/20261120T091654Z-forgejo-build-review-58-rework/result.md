# P8C #58 — PR #51 rework result (forgejo build spec, review #58)

Revision reworked from `5cba6614759d6a678cd24a91d7d6c9a3c4ec42c8`.
New source SHA (this rework): `f4b05854b6d0715a44adf4d609277bf71540c91d`
(branch `engineer/49-forgejo-build-spec`).
Source pin (unchanged): `d22aa8f1170deaf09580518916ea02c7c4d8bfba`.
Review criteria doc: `2bcfeb69b0c50165c8f98d4141ed8fabd3a157e3:docs/architecture/P8C_FORGEJO_BUILD_REVIEW_58.md`.

## Boundaries respected
CI not run; no build/push of the image; no sign/attest; no workflow publication;
no change to the real `portal/versions.lock` or `portal/tools/pins.lock.json`
(only scratch copies exercised; `git status` confirms neither lock is modified).
Digest/provenance remain `NOT_VERIFIED`. All checks are offline, with synthetic
inputs and mock/local transports only.

## Fixes by review criterion

### 1. Owner gate — TRIPLE check (review items 1 & 4)
- `verify_owner_gate` now triple-checks repository, ref and workflow SHA:
  policy-ALLOWED value (from `--repository`/`--ref`/`--pinned-workflow`) == owner
  document == OBSERVED runtime context (`--observed-repository`/`--observed-ref`/
  `--observed-workflow-sha` = `github.repository`/`github.ref`/`GITHUB_WORKFLOW_SHA`).
- Absence of any observed value is a fail-closed REJECTION (never skipped) —
  the runtime context must be bound.
- The workflow SHA is verified in the unprivileged preflight job BEFORE any
  release rights are granted.

### 2. Full-tree inventory (review item 2)
- New `PINNED_SOURCE_TREE_SHA256` = sha256 of the SORTED full
  `git ls-tree -r --name-only d22aa8f…` list (4574 files) — the COMPLETE input
  tree. Any omission / extra / substituted file (inputs OUTSIDE `portal/`
  included) changes the hash and is refused.
- `REQUIRED_SOURCE_FILES` expanded with the out-of-portal inputs the go tests
  actually read: `docs/architecture/p8c/openapi.json`,
  `portal/migrations/{migrations.go,0001_portal_observations.sql}`,
  `portal/manifests/{networkpolicy,deployment}.yaml`,
  `portal/networkpolicy/testdata/accepted-policy-contract.json`.
- Independent regressions on omissions (`README.md` dropped) and extras
  (`extra/evil-injected.txt` injected) both refused.

### 3. Registry — Basic vs issued-Bearer split (review item 3)
- `_generic_oci_transport` no longer does `token = cred` on a 200 and then
  `Bearer <cred>`. Basic and issued-Bearer are SEPARATE schemes: the manifest
  fetch uses the Basic credential only when `/v2/` accepted Basic directly;
  otherwise it uses an ISSUED Bearer token (and refuses a token endpoint that
  issues none). Both paths covered by unit tests with a mock transport.

### 4. Signed run — out-of-band workflow SHA (review item 4)
- `PINNED_WORKFLOW_SHA` removed from the workflow template `env` (the previous
  self-pin was circular). The expected workflow SHA is carried OUT-OF-BAND by the
  OWNER_GATE document (`workflow_sha`) and cross-checked against the observed
  runtime `GITHUB_WORKFLOW_SHA` in preflight; a mismatch or absence is refused
  before release.
- The predicate is built from already-verified values (runtime
  `GITHUB_WORKFLOW_SHA`), and the release job's verify/apply steps use
  `$GITHUB_WORKFLOW_SHA` as the policy pin (already confirmed == owner document).

### 5. Lock — full-image pre-agreement + byte immutability (review item 5)
- New `lock-image-check` CLI: the release job runs it BEFORE build/push and
  refuses when `env.IMAGE` (full ref) != `src/portal/versions.lock:image.registry`
  (the previous template path `/aiopslab/…` vs the pinned lock
  `/dedvmedved-dot/…` is now refused before push). Template `IMAGE` is a full
  owner-supplied ref that must equal the lock byte-for-byte.
- `apply_lock_pair` now asserts ALL bytes outside the changed digest line are
  unchanged (exact per-line diff == the digest line only), not just section
  markers.

### 6. Offline harness
- Re-run with `/usr/bin/python3 -B` (PyYAML 6.0.1): unit 76/76, integration
  37/37, boundary 13/13 (126/126 PASS), syntax 3 jobs / 58 expressions
  VERIFIED, real-layout inventory (full tree) verified + omission negative.

## Commands (offline)
```
cd portal/tools
/usr/bin/python3 -B -m unittest -v test_forgejo_lock_gate            # 76 OK
/usr/bin/python3 -B -m unittest -v test_forgejo_offline_integration  # 37 OK
/usr/bin/python3 -B -m unittest -v test_forgejo_boundary_regressions # 13 OK
/usr/bin/python3 -B check_forgejo_workflow_syntax.py                 # 3 jobs / 58 expr VERIFIED
# real-layout inventory (full tree + full-tree sha):
git ls-tree -r --name-only d22aa8f1170deaf09580518916ea02c7c4d8bfba > src.txt
git ls-files portal/tools/ > tools.txt
/usr/bin/python3 -B portal/tools/forgejo_lock_gate.py inventory \
  --source-inventory src.txt --tools-inventory tools.txt \
  --pinned-source d22aa8f1170deaf09580518916ea02c7c4d8bfba \
  --pinned-tools aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
  --source-tree-sha256 e273368f01ef242d1fe267647d0c8c1c18f84cfc52e99f9d3974a51bccc13e01
# lock-image pre-agreement:
/usr/bin/python3 -B portal/tools/forgejo_lock_gate.py lock-image-check \
  --lock portal/versions.lock --image ghcr.io/dedvmedved-dot/otus-diplom-portal
```

## Result
`SOURCE_PACKAGE` rework submitted for Architect re-check (review #58). The
independent Architect verdict is authoritative; this engineer does not assign
PASS/ACCEPT.
