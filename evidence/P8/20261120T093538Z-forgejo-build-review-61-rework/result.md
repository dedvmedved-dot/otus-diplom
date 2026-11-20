# P8C #61 — PR #51 rework result (forgejo build spec, review #61)

Reworked from `33b2945701b0562c90d519a00eb5bbd88b3c58d4` (the head review #61
returned for rework). Branch `engineer/49-forgejo-build-spec`.

NEW SHA: EXTERNAL_POST_COMMIT_VALUE — VERIFY BY CONNECTOR
(reported in the Forgejo issue #61 comment, after this commit lands; a committed
file cannot self-reference its own commit SHA.)

Source pin (UNCHANGED): `d22aa8f1170deaf09580518916ea02c7c4d8bfba`.
Review criteria doc: `3a4c901be141d5667f9613c73c7fc26ae913099e:docs/architecture/P8C_FORGEJO_BUILD_REVIEW_61.md`.

## Boundaries respected
CI not run; no build/push of the image; no sign/attest; no workflow publication;
no change to the real `portal/versions.lock` or `portal/tools/pins.lock.json`
(only scratch copies exercised). Digest/provenance remain `NOT_VERIFIED`. All
checks are offline, with synthetic inputs and mock/local transports only.

## Fixes by review criterion

### 1. Independent protected out-of-band workflow-SHA policy pin (review item 1)
- `forgejo_lock_gate.py owner-gate` now REQUIRES `--pinned-workflow`: it is the
  INDEPENDENT protected out-of-band policy pin (a repo secret supplied by the
  Owner). The previous fallback that took the value from the checked document
  (`gate["workflow_sha"]`) is REMOVED — that collapsed the policy pin and the
  document into one quantity and reduced the check to two values (document vs
  runtime). An absent / invalid `--pinned-workflow` stops the preflight
  fail-closed (exit 1, "policy pin missing/invalid") BEFORE any release rights.
- `verify_owner_gate` performs the triple check over THREE distinct quantities:
  policy pin (`expected_workflow_sha`) == owner document `workflow_sha` ==
  observed runtime `GITHUB_WORKFLOW_SHA`. A document+observed agreement that
  contradicts the policy pin is refused (`workflow_sha not bound`).
- Template wiring (review item 1/4): the preflight `Verify owner gate` step adds
  `POLICY_WORKFLOW_SHA: ${{ secrets.POLICY_WORKFLOW_SHA }}` to its env and passes
  `--pinned-workflow "$POLICY_WORKFLOW_SHA"`. The release `verify`/`apply` steps
  pass `--workflow-sha "${{ secrets.POLICY_WORKFLOW_SHA }}"` (the policy pin),
  NOT `$GITHUB_WORKFLOW_SHA` — so the final check is a true THREE-way compare,
  never using runtime as its own policy pin. The predicate (SLSA configSource)
  still binds the runtime `$GITHUB_WORKFLOW_SHA` (already cross-checked against
  the policy pin in preflight).

### 2. Byte-level lock apply — preserve bytes outside the digest line (review item 5)
- `apply_lock_pair` now operates on RAW bytes. `_line_spans` / `_line_content`
  split the file into (start,end) byte spans preserving each line's exact
  terminator (LF / CRLF / lone CR) and an absent trailing newline. The new digest
  line is spliced into the original byte stream at the exact span of the old
  digest line, reusing the old line's OWN terminator bytes — `read_text()`'s
  newline normalization (which converted CRLF -> LF and rewrote all 47 lines) can
  no longer corrupt the rest of the file.
- Defensive byte-range + line-count checks refuse the write if ANY byte before /
  after the digest line would change, or if the line count would change.
- Regressions: LF, CRLF, mixed endings, and absent trailing newline all proven
  byte-for-byte on scratch copies (see 05-byte-preservation.txt): exactly ONE
  line changes, CRLF count and trailing-newline status are preserved.

### 3–4. Inventory / registry / signed run (unchanged, re-verified)
- Inventory: full-tree `PINNED_SOURCE_TREE_SHA256` unchanged
  (`e273368f…`, 4574 files); source pin unchanged.
- Registry: Basic vs issued-Bearer split unchanged (both paths mock-tested).
- Signed run: the workflow-SHA binding is now the independent policy pin (item 1)
  through preflight AND the final verify/apply steps.

## Offline harness (all PASS)
```
/usr/bin/python3 -B -m unittest -v test_forgejo_lock_gate            # 80 OK  (+4)
/usr/bin/python3 -B -m unittest -v test_forgejo_offline_integration  # 37 OK
/usr/bin/python3 -B -m unittest -v test_forgejo_boundary_regressions # 19 OK  (+6)
/usr/bin/python3 -B check_forgejo_workflow_syntax.py                 # 3 jobs / 61 expr VERIFIED
/usr/bin/python3 -B evidence/P8/20261120T093538Z-forgejo-build-review-61-rework/05-byte-preservation-demo.py
                                                       # BYTE_PRESERVATION = VERIFIED
```
Total 136 offline tests PASS (unit 80 + integration 37 + boundary 19).

## Evidence files
- `01-unit-tests.txt`, `02-integration-harness.txt`, `03-boundary-regressions.txt`,
  `04-syntax-check.txt`, `05-byte-preservation-demo.py` + `05-byte-preservation.txt`,
  `06-real-inventory.txt`.
