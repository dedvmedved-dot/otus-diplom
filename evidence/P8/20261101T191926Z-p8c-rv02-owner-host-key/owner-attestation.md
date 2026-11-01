# Owner attestation: node-01 SSH host-key identity

Received in the project conversation on 2026-11-01.
Evidence class: OWNER_REPORTED_TRUSTED_CONSOLE; not an Architect-executed live check.
Owner explicitly identified the source as the trusted console of node-01, not skhome01
and not the previously first-trust SSH session.

Reported commands/results:
```text
hostname -s -> node-01
date -u -> 2026-11-01T19:19:26Z
ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub -E sha256
256 SHA256:4Janc/G5wzV6Yfi8gPTz55u/81atXF1xzjkDIISJjvc root@astra-38 (ED25519)
```

Target binding reported by Owner: node-01, management192.168.194.38.
ED25519 matches the previously reported in-band SSH fingerprint exactly.
Other public fingerprints reported from the same trusted console:
- RSA SHA256:nf5b31oYdnKqJEr3dHSAf3M9VXkGuGATtLuCZPVkKWs
- ECDSA SHA256:mnHCOea9pokSOq2BUVt7IerK949RXaNu6y7UAzekkKk

The historical comment root@astra-38 does not alter the public key fingerprint.
The unrelated fc-prefixed identifier is excluded from identity evidence.
No private key, password, token or kubeconfig included.

Limit: accepted Owner out-of-band attestation authenticates the expected host-key binding
for subsequent strict verification. It is not a blanket proof of no MITM, no compromise,
safe credentials, or authenticated future connections. Future SSH must verify the expected
key and STOP on mismatch; never disable host-key checking.
No new connection, scan, collector run or credential inspection was performed by Architect.
