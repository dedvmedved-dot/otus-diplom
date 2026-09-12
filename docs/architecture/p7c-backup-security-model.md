# P7C Backup Security Model

Principles: no plaintext credentials in Git; no secret values in evidence;
no credentials in argv; no credentials in URLs; Kubernetes Secret references only;
least privilege; separate backup credentials where possible.

S3 minimum permissions: GetObject, PutObject, DeleteObject, ListBucket on the
backup bucket. Object Lock adds separate retention/delete permission analysis.
Credentials delivered via pre-created Kubernetes Secret (namespace/name referenced
by BackupStorageLocation). No Secret values committed.
