# P7C-B2 — S3 Object Store Requirements

The object store is NOT provisioned. Required inputs (all OWNER INPUT REQUIRED):

| Field | Requirement | Status |
|---|---|---|
| provider type | AWS_NATIVE / MINIO / CEPH_RGW / YANDEX / CLOUD_R2 / OTHER_S3 | OWNER INPUT REQUIRED |
| endpoint | S3 endpoint URL | OWNER INPUT REQUIRED |
| bucket | backup bucket name (dedicated, versioned) | OWNER INPUT REQUIRED |
| region | S3 region (may be `us-east-1` style default for self-hosted) | OWNER INPUT REQUIRED |
| force path style | true for self-hosted (MinIO/RGW), false for AWS | OWNER INPUT REQUIRED (derive from provider) |
| TLS CA mode | PUBLIC_CA / PRIVATE_CA / CUSTOM_BUNDLE | OWNER INPUT REQUIRED |
| CA ref | ConfigMap/Secret name with CA bundle (if private) | OWNER INPUT REQUIRED |
| credential secret ref | Kubernetes Secret/ExternalSecret name + namespace (no values) | OWNER INPUT REQUIRED |
| Object Lock | required? enabled? retention mode/period | OWNER INPUT REQUIRED |
| versioning | bucket versioning enabled? | OWNER INPUT REQUIRED |
| SSE | NONE / SSE-S3 / SSE-KMS | OWNER INPUT REQUIRED |

Discovery result: no S3/MinIO/Ceph RGW namespace, service, or bucket found in the cluster.
Only a LINSTOR-internal secret `piraeus.io/linstor-backup` (piraeus-datastore ns) exists;
it is LINSTOR's own backup credential type, NOT a Velero object store target.

Secret-value discipline: only names/references are requested; no values committed.
