# P8C-R1 RV-02 — follow-up live-run pinned package manifest

Status: **DRAFT / NOT_AUTHORIZED_FOR_RUN** (no authorization to transfer or run).
Date: 2026-11-01 (UTC). Prepared from the ACCEPTED follow-up source; no code changes.

## Accepted source
```text
ACCEPTED_SOURCE_SHA: 05d61ac74e88256adee455dcefd2d9c33335b6b3
ACCEPTED_EVIDENCE_SHA: dd2a4115e6d4c7799a4acf5156a42ab0590ceea8
ACCEPTANCE_DOC: docs/architecture/P8C_RV02_ACCEPTANCE_dd2a411_20261101.md
```

## Pinned runtime file set (extract from ACCEPTED_SOURCE_SHA, not the working tree)
`followup.py` imports `supplemental.py` (pure projectors, identity gate, helpers). No other
local dependency and no data file is read at run time — `CNP_SPEC_SHA256`, `LIST_ENVELOPE`,
`D1_EXPECT` and the read table are embedded in the source. The test fixture
`derived-i1-fixture.json` and `followup_test.py` are TEST-ONLY and NOT part of the run set.

| Path | Source commit | Git blob | SHA-256 | Purpose |
|---|---|---|---|---|
| `portal/networkpolicy/followup.py` | 05d61ac74e88256adee455dcefd2d9c33335b6b3 | `8f2d7f6d0d3d033810046d93b33448f465ab57f6` | `f48cfc825f25a002cac6afcc63da9f7d5800a3a92b5bc231eeb456b7d6328b98` | bounded follow-up collector (F-D1..F-TIER) |
| `portal/networkpolicy/supplemental.py` | 05d61ac74e88256adee455dcefd2d9c33335b6b3 | `1b613fbd1e35a109072d2843d6e5f3a3fd47b3d6` | `ddd9a4dc17bca97d6b36ae6b4d501e1722c5d38d6e5ac8c7b051698fa0b15491` | imported dependency: pure projectors + finite S1 identity gate + `classify` |

Node-side prerequisites (NOT repository files, NOT copied): `python3` (3.11.x), `kubectl`,
`KUBECONFIG=/etc/kubernetes/admin.conf` with context `kubernetes-admin@pak-portal`.

## Exact local extraction and verification (Bash; no transfer/run authorization)

Execute from a trusted repository checkout containing the accepted commit. A new private
directory prevents overwriting working files. Any git/hash failure terminates the subshell.
Git blob checks are local; Git is not required on the execution node.

```bash
(
set -euo pipefail
umask 077
bundle_dir=$(mktemp -d "${TMPDIR:-/tmp}/p8c-followup-package.XXXXXXXX")
git show 05d61ac74e88256adee455dcefd2d9c33335b6b3:portal/networkpolicy/followup.py > "$bundle_dir/followup.py"
git show 05d61ac74e88256adee455dcefd2d9c33335b6b3:portal/networkpolicy/supplemental.py > "$bundle_dir/supplemental.py"
cd "$bundle_dir"
sha256sum --check <<'SHA256SUMS'
f48cfc825f25a002cac6afcc63da9f7d5800a3a92b5bc231eeb456b7d6328b98  followup.py
ddd9a4dc17bca97d6b36ae6b4d501e1722c5d38d6e5ac8c7b051698fa0b15491  supplemental.py
SHA256SUMS
test "$(git hash-object followup.py)" = 8f2d7f6d0d3d033810046d93b33448f465ab57f6
test "$(git hash-object supplemental.py)" = 1b613fbd1e35a109072d2843d6e5f3a3fd47b3d6
printf 'VERIFIED_LOCAL_BUNDLE=%s\n' "$bundle_dir"
)
```

## Future node-side block — DRAFT, NOT AUTHORIZED TO EXECUTE

After a separate live gate and approved transfer into a fresh private directory, the following
Bash block rechecks both hashes before collector execution. No literal angle-bracket placeholder.
Set P8C_APPROVED_BUNDLE_DIR to an absolute approved directory. No automatic retry.

```bash
(
set -euo pipefail
umask 077
# Only after a separate live gate: operator supplies the approved fresh bundle directory.
: "${P8C_APPROVED_BUNDLE_DIR:?Set approved bundle directory after live authorization}"
cd "$P8C_APPROVED_BUNDLE_DIR"
sha256sum --check <<'SHA256SUMS'
f48cfc825f25a002cac6afcc63da9f7d5800a3a92b5bc231eeb456b7d6328b98  followup.py
ddd9a4dc17bca97d6b36ae6b4d501e1722c5d38d6e5ac8c7b051698fa0b15491  supplemental.py
SHA256SUMS
test "$(hostname -s)" = node-01
test ! -e followup-output
test ! -e run-meta.txt
export KUBECONFIG=/etc/kubernetes/admin.conf
set -o noclobber
printf 'START_UTC=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > run-meta.txt
set +e
python3 -B followup.py --context kubernetes-admin@pak-portal --output "$P8C_APPROVED_BUNDLE_DIR/followup-output"
run_rc=$?
set -e
printf 'END_UTC=%s\nEXIT_CODE=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$run_rc" >> run-meta.txt
if test -f followup-output/followup.jsonl; then
  sha256sum followup.py supplemental.py followup-output/followup.jsonl run-meta.txt > SHA256SUMS.result
else
  printf 'RESULT_FILE=ABSENT\n' >> run-meta.txt
  sha256sum followup.py supplemental.py run-meta.txt > SHA256SUMS.result
fi
exit "$run_rc"
)
```

The script files remain byte-identical. Python -B avoids writing import bytecode. Local
result/metadata creation is expected; no Kubernetes mutation is authorized. The block preserves
the collector exit code, including1, and does not treat it as permission for another attempt.
If interrupted before an exit is known, record UNKNOWN_OUTCOME; do not infer a retry budget.
Review/sanitize collected artifacts before Git publication; never publish arbitrary stdout/stderr.

## Reference: embedded runtime constants

```text
CTX=kubernetes-admin@pak-portal  REQUEST_TIMEOUT=15s  SUBPROCESS_TIMEOUT=20s
PAGE_LIMIT=200  PAGE_LIMIT_LAST=100  TOTAL_CAP=500  MAX_PAGES=3
CNP_SPEC_SHA256=770130a412fd6fab2f02d953edf35f8cc68bf4379db8307e2185937c1e699568
OUTPUT_FILE=followup.jsonl
```
Maximum19 collector-issued kubectl subprocess invocations (4 non-paginated +5×3).
This is not an exact HTTP-request bound: kubectl discovery/client behavior can issue additional
HTTP exchanges, particularly for the typed Pod read. Collector code has no automatic rerun.
