CREDENTIAL_BRIDGE=BLOCKED — OWNER/ADMIN PRIVILEGED ACTION REQUIRED.
The Velero least-privilege S3 credential lives at /etc/seaweedfs/velero-credentials.env (mode 600 root:root) and /etc/seaweedfs/iam.json (mode 640 root:seaweedfs) on the S3 VM 172.30.143.10. Hermes holds only SSH-key (non-sudo) access to the VM (plaintext sudo password was removed in P7C-S3-P1-R1 §38). velero-credentials.env NOT_READABLE; iam.json NOT_READABLE; sudo -n true -> 'a password is required' (PASSWORDLESS_SUDO=NO).
Per ADR/task §18, Hermes MUST NOT create a new/wider S3 identity, MUST NOT create NOPASSWD:ALL, and MUST NOT restore plaintext sudo-password storage. STOP BEFORE SECRET CREATION.
Required owner action (exactly one):
  A. securely provide the existing Velero access/secret pair to Hermes via an out-of-band 0600 temporary credential file; or
  B. create Kubernetes Secret velero/velero-s3-credentials out-of-band from the existing least-privilege credential.
