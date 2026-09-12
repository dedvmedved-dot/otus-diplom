# P7C PostgreSQL Backup Boundary

Principle: Velero should not be treated as the sole database-consistency mechanism
for PostgreSQL. Application/database-aware backup remains a P8 responsibility.

- Velero: Kubernetes objects around PostgreSQL (CRDs, Deployments, ConfigMaps, Secrets)
- CloudNativePG/Barman (P8): PostgreSQL-native physical backup + WAL archiving

P7C-A does not deploy CNPG or Barman. No contradictory double-backup model.
