#!/usr/bin/env bash
# P8C — single offline-suite launcher (source closure).
# Runs every production route and active regression test in one pass; exits NONZERO on any
# mandatory error. Each test file runs with an isolated window-authority (RESERVATION_BASE),
# so no test can leak state into another. Full output is emitted (not just a summary).
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
export P8C_REVIEW_ROOT="$ROOT"
cd "$ROOT" || exit 1

fail=0

run() {
  local name="$1"; shift
  echo "################################################################"
  echo "### ${name}"
  echo "### cwd=$(pwd) argv=$*"
  echo "################################################################"
  "$@"
  local rc=$?
  if [ $rc -ne 0 ]; then
    echo ">>> FAILED: ${name} (exit ${rc})"
    fail=1
  else
    echo ">>> PASS: ${name}"
  fi
}

isolated() {
  # Per-suite isolated authority: unique tempdir, never deletes a live operator's directory.
  export P8C_READINESS_BASE="$(mktemp -d /tmp/p8c-readiness-XXXXXX)"
}

echo "UTC_START=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "SOURCE_SHA=$(git rev-parse HEAD 2>/dev/null || echo UNKNOWN)"
echo "python=$(python3 -V 2>&1)  bash=${BASH_VERSION}  cwd=$(pwd)"

# --- readiness executor + active architect residual working copy ---
isolated
run "readiness (unit)" bash -c 'cd portal/tools/readiness && python3 -m unittest -v test_readiness'

isolated
run "architect residual (working copy, isolated)" python3 -m unittest -v portal/tools/readiness/test_architect_residual.py

# --- release / seed qualification ---
isolated
run "release qualification (unit)" bash -c 'cd portal/tools && python3 -m unittest -v test_release_qualification'

isolated
run "release (unit)" bash -c 'cd portal/tools && python3 -m unittest -v test_release'

isolated
run "release negative (unit)" bash -c 'cd portal/tools && python3 -m unittest -v test_release_negative'

isolated
run "fake-tool route E2E (seed + release)" bash -c 'cd portal/tools && python3 -m unittest -v test_route_e2e'

isolated
run "release/seed qualification (CLI)" bash -c 'cd portal/tools && python3 release_qualification.py'

# --- Architect regression suites (frozen in evidence, run as-is) ---
isolated
run "architect regression (28)" python3 evidence/P8/20261105-f783e1e-architect-review/regression_test.py -v

isolated
run "architect scheduler authority working (14)" python3 portal/tools/readiness/test_scheduler_authority_working.py -v

isolated
run "architect contract authority working (15)" python3 portal/tools/readiness/test_contract_authority_working.py -v

isolated
run "architect completion authority working (34)" python3 portal/tools/readiness/test_completion_authority_working.py -v

isolated
run "architect residual contract working (20)" python3 portal/tools/readiness/test_residual_contract_working.py -v

isolated
run "architect remaining contract (17, review e60d1db)" python3 evidence/P8/20261106-e60d1db-architect-review/remaining_contract_test.py -v

# --- public pin verification (offline: cached bytes + prior verified evidence; no network) ---
isolated
run "public pins verification (offline)" bash -c 'cd portal/tools && python3 verify-pins.py --offline'

# --- static/syntax gates ---
isolated
run "bash syntax (install-verified-go.sh)" bash -n portal/tools/install-verified-go.sh

isolated
run "python syntax (all tools)" python3 -m py_compile portal/tools/readiness/*.py portal/tools/*.py

echo "UTC_END=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
if [ $fail -ne 0 ]; then
  echo "SUITE RESULT: FAIL"
  exit 1
fi
echo "SUITE RESULT: PASS"
exit 0
