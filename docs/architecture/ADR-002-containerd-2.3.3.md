# ADR-002 — containerd 2.3.3 baseline alignment

**Status:** ACCEPTED
**Authority:** Chief Architect
**Date:** 2026-08-24

---

## Title

containerd 2.3.3 baseline alignment

## Context

TASK-008 (P2) discovered that the exact package `containerd 2.3.1`
(from `versions.lock`) is not available in any approved APT source.

Observed availability:

| Source | Available containerd versions |
| --- | --- |
| Astra repository-main | 2.2.1 |
| Docker Debian Bookworm stable | 1.7.x, 2.1.5, 2.2.0–2.2.6, 2.3.3 |

## Decision

Change containerd baseline from `2.3.1` to `2.3.3`.

## Rationale

- 2.3.3 remains in the containerd 2.3 LTS branch;
- 2.3.3 is a newer patch release of the same minor/LTS line;
- package sourced from the official Docker Debian Bookworm stable repository;
- Kubernetes 1.36 requires CRI v1, supported by containerd 2.x;
- containerd 2.3 is LTS.

## Rejected alternatives

- Astra containerd 2.2.1 — older minor branch;
- Docker repo containerd 2.2.6 — older minor branch;
- Random mirrors / unverified packages — prohibited.

## Impact

- `versions.lock` updated only for containerd (`2.3.1` → `2.3.3`);
- P2 resumes;
- no network/storage architecture change.

## Previous baseline

```text
containerd 2.3.1
```

## Approved baseline

```text
containerd 2.3.3
```
