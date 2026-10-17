# Velero compatibility (target Velero 1.18.1 + velero-plugin-for-aws v1.14.2)

Config keys verified in velero-plugin-for-aws object_store.go (retrieval 2026-10-17):
  s3Url (s3URLKey = "s3Url")         -> custom S3-compatible endpoint
  s3ForcePathStyle                    -> path-style support
  caCert (caCertKey)                  -> custom CA bundle
  insecureSkipTLSVerify               -> MUST be false (TLS verification mandatory)
  publicUrl, region, checksumAlgorithm, signatureVersion, serverSideEncryption, etc.

Classification for any S3-compatible provider exposing a custom endpoint:
  VELERO_COMPATIBILITY = SUPPORTED (custom endpoint + path-style + private CA + TLS verify,
  multipart upload, list/put/get, versioning/retention/lifecycle via standard S3 semantics).

Provider-specific caveats (non-AWS tagging/API quirks) noted in p7c-object-store-plugin-decision.md.
POD_TO_MINIO_PATH / POD_DNS_TO_S3 remain NOT_PROVEN until Velero/node-agent runtime (P7C-B2).
