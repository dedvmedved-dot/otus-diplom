# P8C #80 — review #79 rework result (tools root reference-path binding)

Head (this branch): `engineer/77-tools-root-binding`, built on PR #78 head
`7b14922bf79b3fcae4201039d5fd3e6353479af7`. Base: `architect/73-lock` =
`aeed3b314fa0fc00626310dec8a4a9f81d3f248b`.

NEW SHA: EXTERNAL_POST_COMMIT_VALUE — VERIFY BY CONNECTOR
(reported in the Forgejo issue #80 comment, after this commit lands; a committed
file cannot self-reference its own commit SHA.)

Review criteria doc: `4544b04be59f4ba7536a090dae62323f21a4afe2:docs/architecture/P8C_REVIEW_79.md`.

## Boundaries respected
CI / Forgejo workflow NOT run; no build/push of the image; no sign/attest; no
workflow publication; no change to the real `images.lock` (root of the checkout)
— only scratch copies under `tempfile` are exercised. All checks are offline,
with synthetic inputs and mock/local transports only. The prepared pin-cache
(`/tmp/p8c-pin-cache`) is used read-only by the offline pin verification.

## Fix by review criterion (the #79 blocker)

The blocker: `apply_lock_pair` verified components only of the INPUT `lock_path`,
but obtained the reference by `(root / "images.lock").resolve()` — so the
reference could itself traverse a symlink, and equality of resolved paths did not
prove the write targeted the ordinary root file; additionally `abspath` collapsed
`..` before checking the source components.

### 1. Verify both paths independently, before dereferencing, without losing components
- `_has_symlink_component` no longer uses `os.path.abspath` (which folds `..`
  lexically and drops a symlinked ancestor before it is checked). It now walks the
  absolute path component-by-component via `os.lstat`, preserving `..` and `.`:
  `..` is applied against the symlink-free prefix accumulated so far, so a symlink
  is always detected BEFORE a `..` could traverse through it; `.` is a no-op; a
  missing tail is symlink-free.
- `apply_lock_pair` now checks, IN ORDER and each INDEPENDENTLY before any
  dereference: (a) the trusted root `tools_root`; (b) the trusted reference
  `<root>/images.lock`; (c) the input `lock_path`. Any symlink component is
  refused with `RuntimeError`.

### 2. Read and write only the verified ordinary root file
- After all three symlink checks, the input is proven to be the SAME inode as the
  reference via `os.path.samefile` (not a resolved-string equality), and the
  reference is then confirmed to be a regular file (`is_file()`). Only that
  verified ordinary `<root>/images.lock` is read and written.

### 3. Failure checks for reference-path substitution (bytes unchanged)
- `test_refuses_symlinked_reference_lock_file` — `<root>/images.lock` is a symlink;
  the INPUT path is the symlink's real target (symlink-free). The old
  `.resolve()` equality would have written to the target; now refused, target
  byte-identical.
- `test_refuses_symlinked_tools_root` — `tools_root` itself is a symlink to
  another directory; refused before any dereference, real file byte-identical.
- `test_refuses_dotdot_through_symlink_component` — `root/escape/../images.lock`
  where `escape` is a symlink; the component walk catches `escape` before `..`,
  refused, bytes unchanged.

### 4. Existing checks preserved
- Positive byte checks (LF / CRLF / mixed endings / absent trailing newline /
  exactly-one-digest-line) and the three existing negative cases (outside root,
  nested same-named file, symlink file, symlink parent) all remain GREEN. The
  `fd286f5` regression (`test_refuses_images_lock_outside_tools_checkout`) stays
  GREEN.

## Offline harness (all PASS, prepared pin-cache)
```
python3 -m unittest -v test_forgejo_lock_gate             # 88 OK  (+3, was 85)
python3 -m unittest -v test_forgejo_offline_integration   # 37 OK
python3 -m unittest -v test_forgejo_boundary_regressions  # 19 OK
python3 verify-pins.py --offline                          # 10/10 VERIFIED (go/buildkit/rootlesskit/syft/trivy/cosign/checkout/upload-artifact/login-action/postgres)
bash portal/tools/run_offline_suite.sh                    # SUITE RESULT: PASS (all stages, incl. public pins offline)
python3 -m py_compile <all tools>                         # OK
```
Profile total: 88 + 37 + 19 = **144** offline tests PASS (141 preserved + 3 new).
The full `run_offline_suite.sh` now reports `SUITE RESULT: PASS` — the previously
reported empty pin-cache is resolved (cache is prepared/populated) and no BuildKit
conflict reproduced in this environment (sequential isolated stages).

## Evidence files
- `01-unit-tests.txt`, `02-integration-harness.txt`, `03-boundary-regressions.txt`
  (full `-v` transcripts, each ending `OK`),
- `04-pin-cache-offline.txt` (offline pin verification, 10/10 VERIFIED),
- `05-full-offline-suite.txt` (full `run_offline_suite.sh` transcript, `SUITE RESULT: PASS`).
