# Runtime Delta (N1-R1)

MINIO_SOURCE_BUILD = NOT_STARTED
GO_SC2_INSTALL = NOT_STARTED
MC_INSTALL = NOT_STARTED
MINIO_BINARY_INSTALL = NOT_STARTED
MINIO_SYSTEMD_SERVICE = NOT_CREATED
MINIO_DATA_FILESYSTEM = NOT_CREATED
MINIO_BUCKET = NOT_CREATED
MINIO_CREDENTIALS = NOT_CREATED
MINIO_TLS_CERTIFICATE = NOT_CREATED
VELERO = NOT_DEPLOYED

Allowed runtime changes performed: credential rotated, /16->/24 prefix fixed,
BIND9 installed/configured/running, DNS zone demo-pak.test live.

Resolver configuration on VM+nodes (§20-21): NOT_APPLIED (blocked by terminal
safety guard on /etc/resolv.conf writes; pending admin console or approval).
KUBERNETES_OBJECTS_CHANGED = NO
LINSTOR_DRBD_CHANGED = NO
