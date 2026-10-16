# Network Change Safety Gate

NETWORK_ROLLBACK_PATH = PROVEN
- hypervisor console access available (used by infrastructure admin for
  credential recovery during N1).
- /16 -> /24 change preserves 172.30.143.10 (same IP) and keeps gateway
  172.30.143.1 reachable (in 172.30.143.0/24).
- persistent config managed by ifupdown (/etc/network/interfaces) -> backup
  created before edit.
CONFIG_BACKUP = CREATED (before edit, in section 10)
