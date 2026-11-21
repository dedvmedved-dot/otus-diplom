# P8C #82 — review #81 rework result (atomic replace targets the verified reference)

Head (this branch): `engineer/77-tools-root-binding`, built on PR #78 head
`9d54bd0b054f2bf71d830e5e2d215abbe3be0ff0`. Base: `architect/73-lock` =
`aeed3b314fa0fc00626310dec8a4a9f81d3f248b`.

SOURCE (code+test) commit: `c523eb825d726383546dc4e07b62d6bb5455fe51`.

Review criteria doc: re-review #81 (Forgejo issue #81), applied to PR #78.

## Boundaries respected
CI / Forgejo workflow NOT run; no build/push; no sign/attest; no workflow
publication; no merge; no change to the real `images.lock` (root of the checkout)
— only scratch copies under `tempfile` are exercised. All checks are offline,
with synthetic inputs and mock/local transports only. The prepared pin-cache
(`/tmp/p8c-pin-cache`) is used read-only by the offline pin verification.

## The #81 blocker (conclusion by code, no reproduction)
`os.path.samefile(path, trusted)` proves inode identity, NOT the directory-entry
name. A different name for the same inode (e.g. a hardlink alias of
`<root>/images.lock`) still passes `samefile`, but the read, the temp-file
directory, the `stat`, and the `os.replace` all still used the caller-supplied
`path`. `os.replace(tmp, path)` on such an alias replaces the ALIAS directory
entry and leaves the canonical root `images.lock` unchanged.

## Fix by review criterion
### 1. File operations target the verified reference only
After the three symlink checks, the `samefile` inode proof, and the
`is_file()` regular-file confirmation, EVERY file operation now operates on the
verified reference `trusted` (`<root>/images.lock`), never on the input `path`:
- read: `trusted.read_bytes()`
- temp-file directory: `dir=trusted.parent` (== the verified root)
- mode preservation: `trusted.stat().st_mode`
- atomic replace: `os.replace(tmp.name, trusted)`

### 2. Offline check of the atomic-replacement destination (bytes via read_bytes)
New test `test_replace_targets_verified_reference_not_input_alias`:
- writes a valid `DEST_LOCK` to `<root>/images.lock` and creates a hardlink
  alias `images.lock.alias` (same inode, different directory entry);
- asserts `os.path.samefile(alias, lock)` is True (precondition);
- calls `apply_lock_pair(alias, IMAGE, DIGEST, tools_root=root)`;
- asserts the canonical root `images.lock` IS the replacement destination —
  `NOT_VERIFIED` gone, `digest` and `verified: true` present, and the full
  byte content equals the expected updated `DEST_LOCK` (compared via
  `read_bytes`, no newline/text normalization);
- asserts the alias entry still names the OLD inode/content — `alias.read_bytes()`
  byte-identical to the pre-call bytes and still contains `NOT_VERIFIED`.

Verified the test is a genuine regression: with `os.replace(tmp.name, path)`
restored, the test FAILS (`NOT_VERIFIED` unexpectedly found in root bytes).

### 3. Previous tests preserved
All prior positive byte checks (LF / CRLF / mixed endings / absent trailing
newline / exactly-one-digest-line), the three #76 negatives (outside root,
nested same-named file, symlink file, symlink parent), the three #79 negatives
(reference-file symlink, tools-root symlink, `..`-through-symlink), and the
`fd286f5` regression remain GREEN.

## Offline harness (all PASS, prepared pin-cache)
```
python3 -m unittest -v test_forgejo_lock_gate             # 89 OK  (+1, was 88)
python3 -m unittest -v test_forgejo_offline_integration   # 37 OK
python3 -m unittest -v test_forgejo_boundary_regressions  # 19 OK
python3 verify-pins.py --offline                          # 10/10 VERIFIED
bash portal/tools/run_offline_suite.sh                    # SUITE RESULT: PASS (22 stages)
python3 -m py_compile <all tools>                         # OK (part of the suite)
```
Profile total: 89 + 37 + 19 = **145** offline tests PASS (144 preserved + 1 new).
Full `run_offline_suite.sh` → `SUITE RESULT: PASS` (exit 0), including public
pins offline verification.

## Evidence files
- `01-unit-tests.txt` (89 OK), `02-integration-harness.txt` (37 OK),
  `03-boundary-regressions.txt` (19 OK),
- `04-pin-cache-offline.txt` (10/10 VERIFIED),
- `05-full-offline-suite.txt` (full `run_offline_suite.sh` transcript,
  `SUITE RESULT: PASS`, SOURCE_SHA `c523eb825d726383546dc4e07b62d6bb5455fe51`).
