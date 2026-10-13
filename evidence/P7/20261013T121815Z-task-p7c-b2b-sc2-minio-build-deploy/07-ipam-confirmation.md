# IPAM / Reference Address Gate

MINIO_IP = 172.30.143.10
NETWORK = VLAN143
SUBNET = 172.30.143.0/24

IPAM_CONFIRMATION = BLOCKED

No authoritative allocation evidence is available from IPAM, network inventory,
or an infrastructure allocation record. The address was only FREE_OBSERVED
(P7C-B2A) and is operationally reachable on VLAN143, but no authoritative
allocation record has been provided.

Required: explicit Owner/network-owner allocation confirmation for
172.30.143.10 -> MinIO VM before assignment can be considered authoritative.

STOP — do not choose another address autonomously.
