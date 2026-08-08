# Preflight tests (P0)

Read-only preflight material for P0 discovery. Nothing here modifies target
systems.

## Contents (as they appear)

- `../..//ansible/playbooks/p0-readonly-preflight.yml` — read-only Ansible
  preflight playbook (facts + read-only commands only).

## Rules

- Read-only only: no installs, no config changes, no reboots, no firewall/sysctl
  changes, no LVM creation, no formatting.
- Results are captured as evidence under `evidence/P0/`.
- Any ambiguity in storage device identification is a STOP condition.

## Status

No preflight run has been executed — infrastructure access is not available.
