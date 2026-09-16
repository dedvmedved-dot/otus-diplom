# P7C-B2A — Bucket Design

bucket: portal-velero-backup
region: ru-west-1
versioning: ENABLED
object lock: ENABLED
mode: GOVERNANCE
default retention: 7 days
lifecycle retention: 30 days

IMPORTANT: MinIO requires Object Lock to be enabled AT BUCKET CREATION TIME.
Object Lock cannot be enabled on an existing bucket.

=> BUCKET MUST BE CREATED WITH OBJECT LOCK ENABLED FROM START.

No bucket creation performed in this task.
