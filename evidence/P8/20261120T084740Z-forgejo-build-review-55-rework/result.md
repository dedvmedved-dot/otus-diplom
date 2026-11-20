# P8C #55 — PR #51 rework result (forgejo build spec)

Revision reworked from `d9e6d4096fd32d0bc43626dec96a5a571dd42d85`.
New source SHA: `d6421f6f213619bd6eb8705cc4d820a4a1fde1c2` (branch `engineer/49-forgejo-build-spec`).
Source pin (unchanged): `d22aa8f1170deaf09580518916ea02c7c4d8bfba`.

## Boundaries respected
CI not run; no build/push of the image; no sign/attest; no workflow publication;
no change to the real `portal/versions.lock` or `portal/tools/pins.lock.json`
(only scratch copies exercised). Digest/provenance remain `NOT_VERIFIED`. All
checks are offline, with synthetic inputs and mock/local transports only.

## Fixes by review criterion

### 1. Owner gate (accepted rework)
- New unprivileged `preflight` job (`permissions: contents: read` only, NO
  `packages: write`/`id-token: write`) checks out the pinned trees, verifies the
  HEADs, builds inventories and verifies the owner gate BEFORE the `release` job
  (`needs: preflight`) can access any registry credential / build / push / sign.
- The gate document is supplied as the `OWNER_GATE` repo secret and passed to the
  step via `env:` — the JSON is written from the env var, never interpolated into
  the shell source text (`printf '%s' "$OWNER_GATE" > gate.json`).
- The owner is confirmed against the trusted runtime actor (`github.actor`), not
  the self-asserted `owner` name alone (`verify_owner_gate` rejects a
  missing/mismatched actor).
- `repository`/`ref` are the ACTUAL `github.repository` / `github.ref` (no
  hardcoded strings).
- The gate is bound to a single run: it must carry `run_id` equal to
  `github.run_id`, plus `attempt == 1` and `run_attempt == 1`, so re-dispatching
  the same gate within its expiry window is refused.

### 2. Two trees
- `REQUIRED_SOURCE_FILES` expanded to every file the test job actually invokes:
  `test_helpers.py`, `test_release.py` (+ their local imports `release-check.py`,
  `provision-ui-auth.py`, `provision-registry-pull.py`), `package.json` +
  `package-lock.json` (npm ci), `app.js`/`renderer-smoke.test.mjs`/
  `fixture-smoke.test.mjs` (+ the go-embedded `web/embed.go`, `index.html`,
  `style.css`). Verified against the REAL pinned source tree: 19 required files,
  0 missing.
- The repeated `cd src/portal` (which resolved from an already-changed cwd) is
  fixed to a single `cd src/portal` in the test step (boundary test asserts the
  run script contains exactly one `cd src/portal`).

### 3. Registry
- The execution transport now restricts EVERY transition to the trusted HTTPS
  origin: `_trusted_origin_ok` (https + same host) gates the bearer realm
  (`_bearer_token_url` refuses a foreign/HTTP realm BEFORE any Basic credential is
  sent), and `_RefuseRedirect` refuses every implicit redirect (proven end-to-end
  against a local redirecting HTTP server).
- Basic credentials are only ever offered to the trusted host; Bearer/Basic are
  not mixed across origins.
- `registry-fetch` now verifies `sha256(body)` AND `Docker-Content-Digest` at
  FETCH time (before any sign/attest/lock), not deferred to just before the lock.

### 4. Signed run
- `source` / `tools` / `workflow` are THREE separate pins
  (`PINNED_SOURCE_SHA`, `PINNED_TOOLS_SHA`, `PINNED_WORKFLOW_SHA`). The predicate
  binds `configSource.digest.sha1 = workflow SHA` and `materials = [source, tools]`;
  the tools checkout SHA is no longer presented as the executed-workflow SHA.
- `decide_lock_update` reads the pinned SHAs from the INDEPENDENT policy bindings
  (module constants / `--pinned-source` / `--pinned-tools` / `--workflow-sha`
  flags), never from the self-reported evidence bundle. Stale legacy
  `pinned_source_sha` / `pinned_workflow_sha` keys in the evidence are ignored.

### 5. Lock
- `apply_lock_pair` now matches the FULL image name (`image.registry ==
  image_ref`), is section-aware (only touches the `image:` section), preserves
  every other section byte-for-byte, refuses to rewrite a foreign image, and
  refuses an already-set digest.
- The workflow applies to the SOURCE tree's real lock `src/portal/versions.lock`
  and additionally requires `--apply-lock true` (only passed under
  `if: inputs.apply_lock == true`), so a bare `--apply` can never write.
- Proven against a COPY of the real `portal/versions.lock` in the same
  `src/portal/versions.lock` layout (boundary regression).

### 6. Offline harness
- Re-run with `/usr/bin/python3 -B` (PyYAML 6.0.1): unit 56/56, integration
  31/31, boundary regressions 11/11 (98/98 PASS), syntax 3 jobs / 56 expressions.

## Commands (offline)
```
cd portal/tools
/usr/bin/python3 -B -m unittest -v test_forgejo_lock_gate            # 56 OK
/usr/bin/python3 -B -m unittest -v test_forgejo_offline_integration  # 31 OK
/usr/bin/python3 -B -m unittest -v test_forgejo_boundary_regressions # 11 OK
/usr/bin/python3 -B check_forgejo_workflow_syntax.py                 # 3 jobs / 56 expr VERIFIED
# real-layout inventory:
git ls-tree -r --name-only d22aa8f1170deaf09580518916ea02c7c4d8bfba -- portal/ > src.txt
git ls-files portal/tools/ > tools.txt
/usr/bin/python3 -B portal/tools/forgejo_lock_gate.py inventory \
  --source-inventory src.txt --tools-inventory tools.txt \
  --pinned-source d22aa8f1170deaf09580518916ea02c7c4d8bfba \
  --pinned-tools aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa            # verified
```

## Result
`SOURCE_PACKAGE` rework submitted for Architect re-check (review #55). The
independent Architect verdict is authoritative; this engineer does not assign
PASS/ACCEPT.
