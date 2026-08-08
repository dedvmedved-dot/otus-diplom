# Infrastructure Passport — P0

Factual hardware/OS/network passport required before deployment. This file is a
**template**. Network parameters are tracked in three columns:

- **REFERENCE** — the approved plan from TR v4.0 (not a claim of actual config).
- **OBSERVED** — what is actually read from the node during authorized P0
  discovery. Until then it MUST remain `NOT VERIFIED`.
- **MATCH** — whether OBSERVED equals REFERENCE. `NOT VERIFIED` until OBSERVED
  is factually collected.

> RULE (TASK-003 §17): REFERENCE MUST NOT be copied into OBSERVED. OBSERVED is
> filled only from real per-node discovery. No value is invented to fill a table.
>
> Current state: **no authorized infrastructure access** — every OBSERVED and
> MATCH cell is `NOT VERIFIED`, and all per-node hardware facts are `NOT VERIFIED`.

## Network addressing — REFERENCE / OBSERVED / MATCH

### Per-node addresses

| Parameter | REFERENCE | OBSERVED | MATCH |
| --- | --- | --- | --- |
| node-01 Management (VLAN 140) | 172.30.140.101 | NOT VERIFIED | NOT VERIFIED |
| node-01 DRBD (VLAN 141) | 172.30.141.101 | NOT VERIFIED | NOT VERIFIED |
| node-01 BMC (VLAN 142) | 172.30.142.101 | NOT VERIFIED | NOT VERIFIED |
| node-02 Management (VLAN 140) | 172.30.140.102 | NOT VERIFIED | NOT VERIFIED |
| node-02 DRBD (VLAN 141) | 172.30.141.102 | NOT VERIFIED | NOT VERIFIED |
| node-02 BMC (VLAN 142) | 172.30.142.102 | NOT VERIFIED | NOT VERIFIED |
| node-03 Management (VLAN 140) | 172.30.140.103 | NOT VERIFIED | NOT VERIFIED |
| node-03 DRBD (VLAN 141) | 172.30.141.103 | NOT VERIFIED | NOT VERIFIED |
| node-03 BMC (VLAN 142) | 172.30.142.103 | NOT VERIFIED | NOT VERIFIED |

### Cluster-wide network parameters

| Parameter | REFERENCE | OBSERVED | MATCH |
| --- | --- | --- | --- |
| API VIP | 172.30.140.100 | NOT VERIFIED | NOT VERIFIED |
| Ingress pool | 172.30.140.110-172.30.140.119 | NOT VERIFIED | NOT VERIFIED |
| Pod CIDR | 10.244.0.0/16 | NOT VERIFIED | NOT VERIFIED |
| Service CIDR | 10.96.0.0/12 | NOT VERIFIED | NOT VERIFIED |
| Management subnet | 172.30.140.0/24 (VLAN 140) | NOT VERIFIED | NOT VERIFIED |
| DRBD subnet | 172.30.141.0/24 (VLAN 141) | NOT VERIFIED | NOT VERIFIED |
| BMC subnet | 172.30.142.0/24 (VLAN 142) | NOT VERIFIED | NOT VERIFIED |
| Backup subnet | 172.30.143.0/24 (VLAN 143) | NOT VERIFIED | NOT VERIFIED |

```text
REFERENCE CONFIGURATION — REQUIRES FACTUAL VERIFICATION
OBSERVED / MATCH: NOT VERIFIED until real per-node discovery.
```

## Per-node hardware/OS passport

Captured via read-only discovery (see `access-requirements.md` and
`ansible/playbooks/p0-readonly-preflight.yml`). All values `NOT VERIFIED` until
authorized discovery runs.

### node-01

| Field | Value |
| --- | --- |
| hostname | NOT VERIFIED |
| serial | NOT VERIFIED |
| vendor/model | NOT VERIFIED |
| CPU model | NOT VERIFIED |
| CPU architecture | NOT VERIFIED |
| physical core count | NOT VERIFIED |
| RAM | NOT VERIFIED |
| Astra Linux version | NOT VERIFIED |
| kernel | NOT VERIFIED |
| OS RAID | NOT VERIFIED |
| OS disks | NOT VERIFIED |
| storage device (/dev/disk/by-id) | NOT VERIFIED |
| storage WWN | NOT VERIFIED |
| storage serial | NOT VERIFIED |
| storage capacity | NOT VERIFIED |
| NIC names | NOT VERIFIED |
| NIC MAC | NOT VERIFIED |
| management IP | NOT VERIFIED |
| DRBD IP | NOT VERIFIED |
| BMC IP | NOT VERIFIED |
| firmware | NOT VERIFIED |
| power/PSU observations | NOT VERIFIED |

### node-02

| Field | Value |
| --- | --- |
| hostname | NOT VERIFIED |
| serial | NOT VERIFIED |
| vendor/model | NOT VERIFIED |
| CPU model | NOT VERIFIED |
| CPU architecture | NOT VERIFIED |
| physical core count | NOT VERIFIED |
| RAM | NOT VERIFIED |
| Astra Linux version | NOT VERIFIED |
| kernel | NOT VERIFIED |
| OS RAID | NOT VERIFIED |
| OS disks | NOT VERIFIED |
| storage device (/dev/disk/by-id) | NOT VERIFIED |
| storage WWN | NOT VERIFIED |
| storage serial | NOT VERIFIED |
| storage capacity | NOT VERIFIED |
| NIC names | NOT VERIFIED |
| NIC MAC | NOT VERIFIED |
| management IP | NOT VERIFIED |
| DRBD IP | NOT VERIFIED |
| BMC IP | NOT VERIFIED |
| firmware | NOT VERIFIED |
| power/PSU observations | NOT VERIFIED |

### node-03

| Field | Value |
| --- | --- |
| hostname | NOT VERIFIED |
| serial | NOT VERIFIED |
| vendor/model | NOT VERIFIED |
| CPU model | NOT VERIFIED |
| CPU architecture | NOT VERIFIED |
| physical core count | NOT VERIFIED |
| RAM | NOT VERIFIED |
| Astra Linux version | NOT VERIFIED |
| kernel | NOT VERIFIED |
| OS RAID | NOT VERIFIED |
| OS disks | NOT VERIFIED |
| storage device (/dev/disk/by-id) | NOT VERIFIED |
| storage WWN | NOT VERIFIED |
| storage serial | NOT VERIFIED |
| storage capacity | NOT VERIFIED |
| NIC names | NOT VERIFIED |
| NIC MAC | NOT VERIFIED |
| management IP | NOT VERIFIED |
| DRBD IP | NOT VERIFIED |
| BMC IP | NOT VERIFIED |
| firmware | NOT VERIFIED |
| power/PSU observations | NOT VERIFIED |
