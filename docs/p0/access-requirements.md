# P0 Access Requirements

What is required to perform the **actual** P0 infrastructure discovery. Until
these are provided, P0 discovery is `BLOCKED — ACCESS PARAMETERS NOT AVAILABLE`.
No credentials are stored in this repository.

## Linux nodes

Controlled SSH access with sudo (read-only discovery scope) to:

```text
node-01
node-02
node-03
```

Provided out-of-band (not in Git): SSH endpoints, a controlled SSH key or
mechanism, and sudo rights limited to the read-only commands below.

## Read-only discovery commands

These are informational only and change nothing:

```bash
hostnamectl
uname -a
cat /etc/os-release
timedatectl status
ip -br address
ip -br link
ip route
lsblk
ls -l /dev/disk/by-id/
lscpu
free -h
findmnt
pvs
vgs
lvs
```

`pvs`/`vgs`/`lvs` are informational only — no LVM is created or modified in P0.

## External dependencies

Factual parameters and/or access required (credentials supplied out-of-band via
secret references, never committed):

- **DNS** — resolver addresses, forward/reverse zones for node & VIP names.
- **NTP** — time source addresses; target skew ≤ 1 second across nodes.
- **Internal package repositories** — endpoints for Astra/Kubernetes packages.
- **Internal container registry** — endpoint + CA reference for image mirroring.
- **S3 backup endpoint** — endpoint, bucket, region, object-lock policy.
- **Corporate PKI** — issuer, portal FQDN, certificate issuance path.
- **BMC/Redfish** — management network, isolation model, allowed nodes.
- **VLAN/network configuration** — VLAN 140/141/142/143 delivery to nodes.

## Constraints

- Do NOT scan subnets, use nmap, brute-force SSH, guess passwords, or probe the
  reference IPs merely because they appear in the baseline.
- Do NOT store any credential in this repository.
- Discovery is read-only: no package installs, no config changes, no reboots.
