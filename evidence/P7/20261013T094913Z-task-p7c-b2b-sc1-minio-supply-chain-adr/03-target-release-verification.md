# P7C-B2B-SC1 — Target Release Verification

TARGET_TAG = RELEASE.2025-10-15T17-29-55Z
TARGET_TAG_EXISTS = YES
TARGET_COMMIT_SHA = 9e49d5e7a648f00e26f2246f4dc28e6b07f8c84a
  (verified via: git ls-remote https://github.com/minio/minio.git
   refs/tags/RELEASE.2025-10-15T17-29-55Z)
TARGET_RELEASE_TYPE = Security/CVE release (GitHub name: "Security/CVE RELEASE.2025-10-15T17-29-55Z", prerelease: false)
TARGET_RELEASE_ASSETS = 0 (no binary assets)
TARGET_RELEASE_PUBLISHED = 2025-10-16T19:33:51Z

## Security significance (verified from upstream release body)

The release body states a CVE was reported ("Privilege Escalation via Session
Policy Bypass in Service Accounts and STS", GHSA-jjjj-jwhf-8rgr) and fixed in
this release; users advised to upgrade immediately.

## Build requirement

SOURCE_BUILD_REQUIRED = YES
The target release has zero downloadable binary assets, therefore the binary
must be built from the pinned source tag/commit.
