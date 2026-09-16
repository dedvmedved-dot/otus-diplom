# P7C-B2A — TLS Design

HTTPS: YES
PRIVATE_CA: YES
TLS_VERIFY: YES
insecureSkipTLSVerify: false

CERT_SUBJECT: CN=minio.demo-pak.local (proposed)
SAN_IP: 172.30.143.10   (endpoint remains IP-based)
SAN_DNS: minio.demo-pak.local  (proposed; NOT configured in this task)
CA_OWNER: corporate PKI (or project-local self-signed CA for demo)
CA_BUNDLE_FORMAT: PEM (CA certificate only)
K8S_CA_CONFIGMAP_REF: velero/minio-ca   (ConfigMap carrying the CA PEM)

Rationale:
- Endpoint is IP-based (https://172.30.143.10:9000) -> SAN IP is mandatory.
- A DNS name (minio.demo-pak.local) is proposed for operator convenience but is
  NOT configured here; if adopted, SAN_DNS must be added to the cert.
- Velero BackupStorageLocation `caCert` field + mounting the CA ConfigMap into the
  Velero deployment enables TLS verification without disabling verify.
