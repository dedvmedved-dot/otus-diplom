# P7C Decision Register

| ID | Decision | Status | Evidence | Next action |
|---|---|---|---|---|
| D1 | Velero version | DECIDED | versions.lock 1.18.1; digest 2752a011 verified | none |
| D2 | object-store plugin ver | PROPOSED | velero-plugin-for-aws v1.14.2; digest abe29a7b | Architect approval |
| D3 | object-store provider | OWNER_INPUT_REQUIRED | not found in SoT | Owner input |
| D4 | S3 endpoint/bucket/region | OWNER_INPUT_REQUIRED | not found in SoT | Owner input |
| D5 | credential secret ref | OWNER_INPUT_REQUIRED | not found | Owner input |
| D6 | Object Lock policy | OWNER_INPUT_REQUIRED | not specified | Owner input |
| D7 | external-snapshotter ver | PROPOSED | v8.6.0 (2026-05-28) | Architect approval |
| D8 | CSI snapshot enablement | PROPOSED | Velero EnableCSI | Architect approval |
| D9 | VolumeSnapshotClass design | PROPOSED | LINSTOR CSI | Architect approval |
| D10 | data movement strategy | PROPOSED | CSI Snapshot Data Movement | Architect approval |
| D11 | PostgreSQL boundary | DECIDED | CNPG/Barman (P8) | none |
| D12 | RPO/RTO | OWNER_INPUT_REQUIRED | not specified | Owner input |
| D13 | retention | OWNER_INPUT_REQUIRED | not specified | Owner input |
| D14 | restore-test policy | OWNER_INPUT_REQUIRED | not specified | Owner input |
| D15 | TLS CA model | OWNER_INPUT_REQUIRED | depends on endpoint | Owner input |
