# Encryption qualification

AIStor Free: no native SSE (plaintext only) -> AIStor_Free_Encryption = CONDITIONAL_LUKS
  (LUKS2/dm-crypt -> XFS -> S3 server is technically possible on 500 GB; not implemented).
AIStor Ent: SSE-S3/SSE-KMS/SSE-C native -> PASS_NATIVE.
SeaweedFS 4.48: SSE-S3 + SSE-KMS(internal) + SSE-C + -s3.encryptVolumeData -> PASS_NATIVE.
Ceph RGW: SSE-C (no dep), SSE-KMS (Vault/Barbican/KMIP), SSE-S3 (Vault) -> CONDITIONAL (external KMS).

TR_ENCRYPTION_COMPLIANCE: SeaweedFS=PASS_NATIVE; AIStor Free=CONDITIONAL_STORAGE_LAYER;
AIStor Ent=PASS_NATIVE; Ceph RGW=CONDITIONAL_STORAGE_LAYER (or external KMS).
