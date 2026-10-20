P8B-R1 BLOCKED at §19-24 (dedicated S3 bucket identity/Object Lock config).

ROOT CAUSE: need SeaweedFS admin access to create barman-portal identity +
Object Lock retention (GOVERNANCE 7d) + lifecycle (30d).

FINDINGS:
- weed shell (via SSH astraadm automation key) works WITHOUT sudo for READ (s3.bucket.list) + s3.bucket.create (withLock).
- s3.configure (IAM) requires JWT (filer signing key): 'missing authorization metadata'.
- Object Lock default retention + lifecycle need S3 admin API (admin creds in iam.json).
- iam.json + seaweedfs.env are root:seaweedfs 640 (unreadable by astraadm).
- Provided sudo password rejected (sudo -S, SSH password auth, interactive PTY). Account NOT locked (faillock tally empty).

WAITING ON: user to provide (1) correct sudo password, (2) JWT filer signing key, or (3) admin S3 access+secret key.
