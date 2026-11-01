# Owner-forwarded authentication report

Date received: 2026-11-01. Message display time:22:28; no independently captured UTC
authentication transcript supplied. Evidence class: OWNER_FORWARDED_OPERATOR_REPORT.
This is not an Architect-executed SSH or Kubernetes verification.

Owner supplied an operator report stating:
- public id_ed25519 key with comment hermes@vps1 was installed for root on node-01/02/03;
- /root/.ssh mode700; authorized_keys mode600; owner root:root;
- passwordless BatchMode tests returned KEY_AUTH_OK with the expected hostname and root;
- kubectl using the existing on-node /etc/kubernetes/admin.conf returned three node names;
- the intended method for primary Hermes is SSH key authentication; private key not exposed;
- password authentication remains enabled as backup, but is not the selected live-gate method.

Only the node-01 account/method readiness is accepted for this gate. Reports about other nodes
are historical operator claims, not authorization for further actions there.
Key comment alone is not cryptographic identity proof; the operator must use the actual
authorized private key locally without exposing it. No secret bytes requested or recorded.

Expected server ED25519 public fingerprint independently attested by Owner console:
SHA256:4Janc/G5wzV6Yfi8gPTz55u/81atXF1xzjkDIISJjvc
Host: node-01 /192.168.194.38.
Reference: docs/architecture/P8C_RV02_OWNER_HOST_KEY_ACCEPTANCE_20261101.md
at915f2c640cb3f0024c7631b6c9284ca0eea99cd7.

Acceptance scope: account=root, method=authorized non-exposed SSH key, readiness=Owner-reported.
This does not prove key setup provenance retrospectively, rotation of the disclosed password,
general host security, or future connection success. Password fallback and reading/using the
old password file are explicitly excluded. No new SSH, kubectl, provisioning or live run
performed by Architect.
