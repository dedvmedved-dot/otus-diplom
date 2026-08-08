# Infrastructure Passport — P0

Factual hardware/OS/network passport required before deployment. This file is a
**template with placeholders**. Every unknown value MUST remain `NOT VERIFIED`.
Values are filled only from real read-only discovery on the actual nodes during
authorized P0 execution. Do not invent values to complete a table.

> Current state: **no authorized infrastructure access** — all node facts below
> are `NOT VERIFIED`.

## Reference addressing

See [`../p0/`](.) and the addressing block below. Reference addressing is the
approved plan from TR v4.0; it is **not** a claim that anything is configured.

```text
REFERENCE CONFIGURATION — REQUIRES FACTUAL VERIFICATION
```

| Purpose | VLAN | Subnet | node-01 | node-02 | node-03 |
| --- | --- | --- | --- | --- | --- |
| Management/API | 140 | 172.30.140.0/24 | 172.30.140.101 | 172.30.140.102 | 172.30.140.103 |
| DRBD | 141 | 172.30.141.0/24 | 172.30.141.101 | 172.30.141.102 | 172.30.141.103 |
| BMC | 142 | 172.30.142.0/24 | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED |
| Backup | 143 | 172.30.143.0/24 | — | — | — |

```text
API VIP:       172.30.140.100
Ingress pool:  172.30.140.110 - 172.30.140.119
Pod CIDR:      10.244.0.0/16
Service CIDR:  10.96.0.0/12
```

## Per-node passport

The following fields must be captured for each node via read-only discovery
(see `access-requirements.md` and `ansible/playbooks/p0-readonly-preflight.yml`).

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
