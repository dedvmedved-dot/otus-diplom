# P7C-B2 — Owner Questionnaire (only unresolved decisions)

1. Какое S3-совместимое хранилище используем? (AWS S3 / MinIO / Ceph RGW / Yandex Object Storage / Cloudflare R2 / иное)
2. Endpoint S3 (URL)?
3. Bucket для бэкапов (имя)?
4. Region?
5. Как называется Kubernetes Secret/ExternalSecret с S3 credentials (имя + namespace)? — только ссылка, значения не нужны.
6. Требуется ли Object Lock (immutability)? Если да — режим (GOVERNANCE/COMPLIANCE) и период.
7. Какой срок хранения бэкапов (retention)?
8. Требуемый RPO (как часто делать backup)?
9. Требуемый RTO (целевое время восстановления)?
10. Как часто выполнять контрольный restore (restore-test)?

(Все 10 — только нерешённые; D1/D2/D10/D11/D7/D8/D9 уже определены фактами.)
