# P7C-B2B-SC1 — Source Provenance Model

Traceability chain (future SC2 evidence):

  official repository (minio/minio)
    -> exact release tag (RELEASE.2025-10-15T17-29-55Z)
    -> exact Git commit (9e49d5e7a648f00e26f2246f4dc28e6b07f8c84a)
    -> verified source tree/archive
    -> exact Go toolchain
    -> documented build command
    -> built binary
    -> binary SHA-256
    -> SBOM
    -> vulnerability assessment
    -> runtime artifact

Provenance fields (populated in SC2):

SOURCE_REPOSITORY = https://github.com/minio/minio
SOURCE_TAG = RELEASE.2025-10-15T17-29-55Z
SOURCE_COMMIT_SHA = 9e49d5e7a648f00e26f2246f4dc28e6b07f8c84a
SOURCE_ARCHIVE_SHA256 = TBD
GO_VERSION = go1.24.8 (toolchain per go.mod)
BUILD_COMMAND = TBD (finalized in SC2)
BUILD_ENVIRONMENT = TBD
BINARY_SHA256 = TBD
SBOM_FILE = TBD
SBOM_SHA256 = TBD
VULNERABILITY_SCAN_RESULT = NOT_REACHED
BUILD_DATE_UTC = TBD
BUILDER_ID = TBD
