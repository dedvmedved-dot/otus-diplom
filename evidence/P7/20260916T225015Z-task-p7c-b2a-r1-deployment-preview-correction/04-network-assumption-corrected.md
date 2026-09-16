# Network Assumption Corrected

Removed unsupported assumption: node-agent hostNetwork=true.

Corrected baseline:
  Velero node-agent = DaemonSet, normal Pod networking, Kopia data mover,
  hostNetwork NOT explicitly enabled.

POD_TO_MINIO_PATH = NOT_PROVEN (node-level VLAN143 route proven, but actual
Velero/node-agent Pod S3 egress not executed — MinIO + Velero not deployed).

VLAN143_NODE_PATH = PASS (unchanged; node-level route proven).

## P7C-B2 NETWORK GATE (future runtime Gate)

PRECONDITIONS:
  external MinIO VM deployed
  172.30.143.10 assigned and IPAM-confirmed
  MinIO S3 API listening
  TLS configured
  bucket created
  credentials provisioned
  Velero/node-agent deployed

RUNTIME PROOF (must all succeed):
  1. Actual Velero/node-agent context can reach MinIO
  2. TCP/9000 succeeds
  3. TLS certificate validation succeeds
  4. Private CA chain trusted
  5. S3 authentication succeeds
  6. Target bucket can be listed
  7. Test object can be written
  8. Test object can be read
  9. Delete semantics compatible with Object Lock
  10. Effective network/source path captured in evidence

ONLY AFTER NETWORK GATE PASS: canary backup -> data movement -> restore -> integrity.
(Not executed now.)
