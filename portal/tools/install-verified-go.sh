#!/usr/bin/env bash
# Same verified bytes supply every build/test; no setup-go or auto toolchain.
set -euo pipefail
: "${RUNNER_TEMP:?}" "${GO_VERSION:?}" "${GO_SHA256:?}"
archive="${GO_ARCHIVE:-$RUNNER_TEMP/go.tar.gz}"
if [ -z "${GO_ARCHIVE:-}" ]; then
  curl --proto '=https' --tlsv1.2 -fsSL "https://go.dev/dl/go${GO_VERSION}.linux-amd64.tar.gz" -o "$archive"
fi
printf '%s  %s\n' "$GO_SHA256" "$archive" | sha256sum -c -
install_dir="$RUNNER_TEMP/portal-verified-go"
mkdir -p "$install_dir"
tar -xzf "$archive" -C "$install_dir" --strip-components=1
export GOTOOLCHAIN=local
"$install_dir/bin/go" version | tee "$RUNNER_TEMP/go-version.txt"
[ "$("$install_dir/bin/go" env GOVERSION)" = "go$GO_VERSION" ]
sha256sum "$install_dir/bin/go" > "$RUNNER_TEMP/go-binary.sha256"
if [ -n "${GITHUB_PATH:-}" ]; then printf '%s\n' "$install_dir/bin" >> "$GITHUB_PATH"; fi
if [ -n "${GITHUB_ENV:-}" ]; then printf 'GOTOOLCHAIN=local\n' >> "$GITHUB_ENV"; fi
