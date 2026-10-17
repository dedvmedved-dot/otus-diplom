# Security / maintenance

AIStor: active; AIStor tags patch 2026 CVEs; Free no LTS/hotfix term.
SeaweedFS 4.48: active; 25 advisories (many CRITICAL/HIGH S3/IAM); ALL CRITICAL/HIGH
  S3-path fixed in 4.48 (vuln ranges <=4.45); requires jwt.filer_signing.key + S3-only exposure.
Ceph 20.2.4: active to 2027-06; CVE-2026-54330 (SigV4), CVE-2026-39944 (STS), CVE-2025-30156 (CephX) fixed in 20.2.4; prefer AES-256-GCM.
