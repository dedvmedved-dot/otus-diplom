# P7C Decision Register (R4-final)

| ID | Decision | Status | Evidence | Next action |
|---|---|---|---|---|
| D1 | Velero version | DECIDED | 1.18.1 digest 2752a011 | none |
| D2 | object-store plugin ver | PROPOSED | velero-plugin-for-aws v1.14.2 digest abe29a7b | Architect approval |
| D3 | object-store provider | OWNER_INPUT_REQUIRED | not found | Owner input |
| D4 | S3 endpoint/bucket/region | OWNER_INPUT_REQUIRED | not found | Owner input |
| D5 | credential secret ref | OWNER_INPUT_REQUIRED | not found | Owner input |
| D6 | Object Lock policy | OWNER_INPUT_REQUIRED | not specified | Owner input |
| D7 | external-snapshotter version | PROPOSED | snapshot-controller v8.6.0 digest d1ab1b09 (k8s.io 0.36.1 exact) | Architect approval + skew acceptance |
| D8 | CSI snapshot API enablement | PROPOSED | P7C-B1 (NOT AUTHORIZED) | Architect authorization |
| D9 | VolumeSnapshotClass | PROPOSED | piraeus-r2-snapclass / linstor.csi.linbit.com / Delete | Architect approval |
| D10 | data movement | PROPOSED | WAITING FOR S3 OWNER INPUT | Owner input |
| D11 | PostgreSQL boundary | DECIDED | CNPG/Barman (P8) | none |
| D12 | RPO/RTO | OWNER_INPUT_REQUIRED | not specified | Owner input |
| D13 | retention | OWNER_INPUT_REQUIRED | not specified | Owner input |
| D14 | restore-test policy | OWNER_INPUT_REQUIRED | not specified | Owner input |
| D15 | TLS CA model | OWNER_INPUT_REQUIRED | depends on endpoint | Owner input |
