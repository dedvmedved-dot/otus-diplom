#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export PORTAL_FIXTURE_DIR
PORTAL_FIXTURE_DIR=$(mktemp -d)
trap 'rm -rf "$PORTAL_FIXTURE_DIR"' EXIT
# This removes only this script's own synthetic fixture directory.
go test -count=1 ./internal/collectors -run '^TestExportCollectorDataflow$' -v
go test -count=1 ./internal/httpapi -run '^TestExportActualCollectorHandlerResponses$' -v
node web/dataflow-smoke.test.mjs
