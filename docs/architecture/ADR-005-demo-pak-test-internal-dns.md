# ADR-005 — demo-pak.test internal DNS (retire demo-pak.local)

STATUS: ACCEPTED
ACCEPTED_BY: Chief Architect / Technical Authority
ACCEPTED_DATE: 2026-10-16
SCOPE: DEMO / NON-PRODUCTION ONLY
SOURCE TASK: P7C-B2B-N1-R1

## Decision

Retire the canonical DNS name `demo-pak.local` and adopt `demo-pak.test`.

- Canonical S3 endpoint: https://s3-backup.demo-pak.test
- IP (unchanged): 172.30.143.10
- External port (unchanged): 443
- Provider (unchanged): MinIO
- Bucket (unchanged): portal-velero-backup
- Region (unchanged): ru-west-1

## Context

TR v4.0 originally used `demo-pak.local`. P7C-B2B-N1 discovery established:

- no internal authoritative DNS exists in the PAK;
- Kubernetes nodes use public resolvers (8.8.8.8/8.8.4.4);
- the external MinIO VM uses a public resolver (77.88.8.8);
- the OS NSS configuration reserves `.local` for mDNS:
  `hosts: files mdns4_minimal [NOTFOUND=return] dns`.

`.local` is therefore unsuitable for this project's deterministic unicast DNS
architecture: the actual resolver stack treats `.local` specially (mDNS
namespace, RFC 6762). This is not a claim that `.local` is technically
impossible — it is unsuitable for the selected design.

## DNS Server Decision

For this isolated demo PAK, deploy BIND9 on the same external MinIO VM.

Accepted because:
- it is DEMO only;
- the DNS name exists solely to reach the S3 service on that VM;
- if the external MinIO VM fails, the S3 service itself is unavailable anyway;
- no additional infrastructure currently exists.

PRODUCTION_RECOMMENDATION != SAME-HOST DNS. No production approval is implied.

## Evidence

- nsswitch.conf: `hosts: files mdns4_minimal [NOTFOUND=return] dns`
- node resolv.conf: 8.8.8.8 / 8.8.4.4; VM resolv.conf: 77.88.8.8
- repository infrastructure inventory contains no internal DNS server
  (only Kubernetes CoreDNS, which is cluster-internal and not authoritative
  for demo-pak.*).

## Relationships

ADR-005 supersedes ONLY the canonical DNS-name portion of ADR-004 and the
corresponding FQDN in TR v4.0 for this deployment.

It does NOT invalidate ADR-004's supply-chain decision and does NOT change:
MinIO version decision, IP, VLAN, S3 port, bucket, region, TLS verification
requirement, or backup architecture.

## Consequences

- New authoritative zone: demo-pak.test (on BIND9 at 172.30.143.10).
- Required A record: s3-backup.demo-pak.test. A 172.30.143.10
- Historical references to demo-pak.local / minio.demo-pak.local remain
  historical and are not rewritten.
