# P7C-B2B-SC1 — Reproducible Build Plan

SOURCE_REPOSITORY = https://github.com/minio/minio
SOURCE_TAG = RELEASE.2025-10-15T17-29-55Z
SOURCE_COMMIT_SHA = 9e49d5e7a648f00e26f2246f4dc28e6b07f8c84a
SOURCE_ARCHIVE_HASH = TBD (to be computed at checkout in SC2)
GO_MOD_REQUIRED_VERSION = go 1.24.0 (minimum), toolchain go1.24.8
SELECTED_GO_VERSION = go1.24.8
TARGET_ARCH = amd64 (x86_64, verified from runtime host `uname -m`)
BUILD_COMMAND (proposed, finalized in SC2):
    CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o minio .
    (version/commit injection via -X flags to be pinned in SC2)
BUILD_OUTPUT = minio server binary
BUILD_HOST = separate controlled build environment (preferred)
RUNTIME_HOST = verified artifact only

## Evidence to preserve during build

- source checkout evidence (git clone + tag checkout log)
- tag evidence (git tag -v / ls-remote)
- commit evidence (HEAD == 9e49d5e7...)
- Go version (go version output)
- dependency state (go.sum)
- build log
- binary SHA-256
- SBOM
- vulnerability scan report
