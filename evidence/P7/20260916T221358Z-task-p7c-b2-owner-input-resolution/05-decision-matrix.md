# P7C-B2 — Decision Matrix (post-owner-input-resolution)

| ID | Decision | Status | Detail |
|---|---|---|---|
| D1 | Velero version | DECIDED | 1.18.1, digest 2752a01188bd8f16572a76b3b2c4331a6a5337a5cbe65715c22ac7f91b31bfa8 (verified) |
| D2 | object-store plugin | DECIDED (verified) | velero-plugin-for-aws v1.14.2, digest abe29a7b360231e359f7aaee79668141bd619ab6989c7cc78d041110987f6ca2; go.mod -> velero v1.18.0 |
| D3 | object-store provider | OWNER_INPUT_REQUIRED | no object store provisioned |
| D4 | S3 endpoint/bucket/region | OWNER_INPUT_REQUIRED | none found |
| D5 | credential secret ref | OWNER_INPUT_REQUIRED | only LINSTOR-internal piraeus.io/linstor-backup (not Velero) |
| D6 | Object Lock policy | OWNER_INPUT_REQUIRED | not specified |
| D7 | external-snapshotter | PROPOSED | snapshot-controller v8.6.0 (deployed in P7C-B1, k8s.io 0.36.1 exact) |
| D8 | CSI snapshot API | PROPOSED (now deployed) | P7C-B1 foundation live (3 CRDs + controller + VSC) |
| D9 | VolumeSnapshotClass | PROPOSED (now deployed) | piraeus-r2-snapclass / linstor.csi.linbit.com / Delete |
| D10 | data movement | PROPOSED | CSI snapshot data movement (Velero CSI + Kopia uploader) to object store |
| D11 | PostgreSQL boundary | DECIDED | CNPG/Barman (P8) |
| D12 | RPO / RTO | OWNER_INPUT_REQUIRED | not specified |
| D13 | retention | OWNER_INPUT_REQUIRED | not specified |
| D14 | restore-test policy | OWNER_INPUT_REQUIRED | not specified |
| D15 | TLS CA model | OWNER_INPUT_REQUIRED | depends on endpoint |

Resolved by this task (facts): D1, D2 verified; D7/D8/D9 reflect P7C-B1 live foundation;
D10 recommendation fixed to CSI data movement per architecture matrix.
Still OWNER INPUT REQUIRED: D3, D4, D5, D6, D12, D13, D14, D15.
