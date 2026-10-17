# Current accepted project contract (Layer B) — mandatory

| ID | Requirement |
|----|-------------|
| B01 | S3 compatibility |
| B02 | endpoint https://s3-backup.demo-pak.test |
| B03 | TCP/443 external contract |
| B04 | custom/private CA TLS verification |
| B05 | path-style S3 support |
| B06 | bucket portal-velero-backup |
| B07 | region ru-west-1 |
| B08 | versioning |
| B09 | Object Lock |
| B10 | GOVERNANCE retention |
| B11 | default Object Lock 7 days |
| B12 | lifecycle target 30 days |
| B13 | no BypassGovernanceRetention for normal backup identity |
| B14 | separate least-privilege identities |
| B15 | no admin/root credentials for Velero |
| B16 | external placement outside protected K8s cluster |
| B17 | VLAN143 connectivity |
| B18 | active maintained security path |
| B19 | reproducible/pinned supply chain |
| B20 | no floating latest/master |
