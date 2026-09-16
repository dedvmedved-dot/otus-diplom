# P7C-B2A — Credential Model (least privilege)

Kubernetes reference (no values):
  namespace: velero
  Secret: velero-minio-credentials

MinIO policy for Velero (least privilege, scoped to backup bucket):

  bucket = portal-velero-backup

  Allow:
    s3:ListBucket                         (on bucket)
    s3:GetBucketLocation                  (on bucket)
    s3:GetObject, s3:PutObject, s3:DeleteObject   (objects)
    s3:ListMultipartUploadParts, s3:AbortMultipartUpload (multipart)
    s3:GetObjectVersion, s3:DeleteObjectVersion        (versioning)
    s3:GetObjectRetention, s3:PutObjectRetention        (Object Lock)

  Deny (default):
    s3:* on other buckets
    admin:* (no MinIO admin API)

Rule: do NOT use MinIO root/admin credentials for Velero. Create a dedicated
scoped access key. Object Lock Governance mode permits delete only with
s3:BypassGovernanceRetention, which is NOT granted to the Velero credential
(so Velero cannot delete immutable objects during the 7-day lock window).
