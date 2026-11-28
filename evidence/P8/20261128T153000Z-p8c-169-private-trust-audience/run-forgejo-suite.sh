#!/usr/bin/env bash
# P8C #169 — offline forgejo suite transcript (single authoritative run).
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
EV_DIR="$ROOT/evidence/P8/20261128T153000Z-p8c-169-private-trust-audience"
mkdir -p "$EV_DIR"
cd "$ROOT/portal/tools" || exit 1
export COSIGN_BINARY=/tmp/cosign-linux-amd64

OUT="$EV_DIR/offline-forgejo-suite.txt"
{
  echo "UTC_START=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "HEAD_SHA=$(git -C "$ROOT" rev-parse HEAD)"
  echo "TOOLS_PIN=0511b4674cd4239362be9602fa354ce587c0a9ff"
  echo "SOURCE_PIN=4c09d6b4a85e2d021516244988f48b92eade7acf"
  echo "WORKFLOW_BLOB=$(git -C "$ROOT" hash-object "$ROOT/.forgejo/workflows/p8c-portal-forgejo-release.yml")"
  echo "python=$(python3 -V 2>&1)"

  echo "=== check_forgejo_workflow_syntax.py ==="
  python3 check_forgejo_workflow_syntax.py

  echo "=== forgejo offline suite (191 tests) ==="
  python3 -m unittest -v test_forgejo_lock_gate test_forgejo_offline_integration test_owner_gate_barrier

  echo "=== cosign CLI flags (v3.1.3) ==="
  python3 test_cosign_cli_flags.py

  echo "UTC_END=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
} 2>&1 | tee "$OUT"
