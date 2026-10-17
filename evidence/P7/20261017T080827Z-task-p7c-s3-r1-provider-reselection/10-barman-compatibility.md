# CloudNativePG / Barman Cloud compatibility (CNPG 1.29.1, PostgreSQL 17.10, Barman Cloud Plugin 0.13.0)

Barman Cloud (barman-cloud-backup / barman-cloud-wal-archive) uses boto3 for S3:
  --endpoint-url       custom S3-compatible endpoint
  path-style           via boto3 config
  custom CA            via AWS_CA_BUNDLE / certifi
  credentials          env / profile (separate backup identity)
  multipart            boto3 multipart upload for large objects

Barman latest release: 3.20.1 (2026-09-29). Barman Cloud Plugin 0.13.0 (CNPG) wraps barman-cloud.

Object Lock interaction: Barman's WAL/basebackup pruning (retention_policy) issues DELETE calls;
locked objects (GOVERNANCE) will be DENIED — retention/object-lock windows must be coordinated
so Barman can still prune expired objects without BypassGovernanceRetention.

Classification: BARMAN_COMPATIBILITY = EXPECTED_COMPATIBLE (boto3 S3 with custom endpoint,
path-style, private CA; Object Lock requires retention coordination — provider-specific).
