# TR v4.0 requirements (Layer A) — traceability

| ID | Requirement | Detail |
|----|-------------|--------|
| A01 | External storage | External S3-compatible backup storage |
| A02 | Protected objects | PostgreSQL backup + WAL; non-DB PVC (Velero/data mover); etcd snapshots; LINSTOR metadata; other object-backup per TR |
| A03 | Versioning | Required |
| A04 | Encryption | Required (TR does NOT mandate S3-native SSE). Distinguish: NATIVE_S3_ENCRYPTION / BLOCK_DEVICE_ENCRYPTION (LUKS/dm-crypt) / CLIENT_SIDE_ENCRYPTION. ENCRYPTION_COMPLIANCE = CONDITIONAL — ARCHITECT INTERPRETATION REQUIRED |
| A05 | Separate credentials | Required |
| A06 | Delete protection | Working backup identity must NOT have delete authority that defeats retention |
| A07 | Object Lock | TR: "where supported". Current project architecture hardened this into a HARD requirement (see Layer B) |
| A08 | Retention baseline | PostgreSQL WAL >=14 days; PG full backup 8 copies; PG incremental/differential 14 copies; etcd snapshots 14 copies; Velero backups 14 copies; monthly control copy 12 copies. (Owner 30-day lifecycle / 7-day lock is Layer B, recorded separately, NOT a silent replacement) |
