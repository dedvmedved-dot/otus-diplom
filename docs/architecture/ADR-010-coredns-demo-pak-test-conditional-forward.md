# ADR-010 — CoreDNS conditional forward for demo-pak.test

STATUS: ACCEPTED
ACCEPTED_BY: Chief Architect / Technical Authority
ACCEPTED_DATE: 2026-10-19
SOURCE_TASK: P7C-B2-R1-DNS1

## Decision

Kubernetes CoreDNS SHALL resolve the private authoritative zone `demo-pak.test`
by conditional forwarding to `172.30.143.10:53` (BIND9).

This extends ADR-005. ADR-005 remains valid (authoritative zone demo-pak.test,
authoritative BIND9 172.30.143.10, canonical record s3-backup.demo-pak.test -> 172.30.143.10).

## Scope

ADR-010 does NOT: replace BIND9; make CoreDNS authoritative for demo-pak.test;
change public DNS behavior; change cluster.local; change node DNS; change Calico;
change node routing; change the S3 endpoint.

BIND9 ACL change is NOT authorized in this task (a separate minimal ACL task
will be issued only if evidence proves it required).
