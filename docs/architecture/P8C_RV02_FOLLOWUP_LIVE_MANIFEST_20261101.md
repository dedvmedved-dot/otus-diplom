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

## Exact extraction commands (run against the pinned source commit)
```bash
git show 05d61ac74e88256adee455dcefd2d9c33335b6b3:portal/networkpolicy/followup.py     > followup.py
git show 05d61ac74e88256adee455dcefd2d9c33335b6b3:portal/networkpolicy/supplemental.py > supplemental.py
```

## Hash verification (STOP on any mismatch — do not run)
```bash
printf '%s  followup.py\n'   'f48cfc825f25a002cac6afcc63da9f7d5800a3a92b5bc231eeb456b7d6328b98' | sha256sum -c
printf '%s  supplemental.py\n' 'ddd9a4dc17bca97d6b36ae6b4d501e1722c5d38d6e5ac8c7b051698fa0b15491' | sha256sum -c
git hash-object followup.py      # expect 8f2d7f6d0d3d033810046d93b33448f465ab57f6
git hash-object supplemental.py  # expect 1b613fbd1e35a109072d2843d6e5f3a3fd47b3d6
test "$(hostname -s)" = node-01
```

## Future run command (only after an explicit live gate authorization; NOT now)
```bash
export KUBECONFIG=/etc/kubernetes/admin.conf
python3 followup.py --context kubernetes-admin@pak-portal --output /tmp/p8c-rv02-followup-<UTC> 
```
One run only; a fresh output directory (the collector fails on an existing directory). Context
must be exactly `kubernetes-admin@pak-portal` (any other value → `SystemExit` before any call).

## Reference: embedded runtime constants
```text
CTX=kubernetes-admin@pak-portal  REQUEST_TIMEOUT=15s  SUBPROCESS_TIMEOUT=20s
PAGE_LIMIT=200  PAGE_LIMIT_LAST=100  TOTAL_CAP=500  MAX_PAGES=3
CNP_SPEC_SHA256=770130a412fd6fab2f02d953edf35f8cc68bf4379db8307e2185937c1e699568
OUTPUT_FILE=followup.jsonl
```
