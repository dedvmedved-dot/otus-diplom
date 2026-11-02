# Independent review b594b12
Date: 2026-11-02 UTC. Review metadata captured at 20:58:38Z.
Connector HEAD: b594b12debd574baa614496b090068982a79da21.
Parent: 147324a8420a5060c051057bad4f458f34ee8bbc.
10 changed files; app, collector, accepted design and historical evidence unchanged.
Review: docs/architecture/P8C_REVIEW_b594b12_AND_GATES_R2_TASK_20261102.md.

## Executed
Command: python3 review-b594/reproduce.py
Exit: 0. Python 3.12.14, PyYAML 6.0.3.
3124 finite candidate-policy checks passed.
Reversed DNS negative-test blind spot reproduced: removing DNS podSelector from all egress DNS peers changes correct-direction outcome while reversed tests continue to deny.
reproduce.py and networkpolicy.yaml in this directory are the exact tested bytes. YAML git blob assertion pins reviewed input to 6212a016c783419d2e81c9a2325fdaeef9279bc7.
Run from any cwd: python3 <this-directory>/reproduce.py.
No Go binary available to reviewer; Hermes Go PASS was read as submitted evidence, NOT independently rerun.
No runtime/CNI proof; no cluster/SSH/registry/workflow operations.

## Source findings
CNPG v1.30.1 monitoring.md blob 69aebcaceb1decacab29762da7046f768b248477 describes instance exporter 9187 independently of a scraper.
default-monitoring.yaml blob 91fc65b07b0b69c218c6eb407df004b808b510f7 defines pg_stat_archiver counters/timestamps/reset and primary/archive_mode=always predicate.
P8B endpoint evidence and Portal direct metrics code corroborate the missing-scraper premise is false. Actual current WAL-family availability remains unobserved.
Deployment draft healthz does not match actual management routes; readyz alone is not standalone TLS proof.
Release manifest lacks three helper entries; draft confuses Owner settings with automatic GITHUB_TOKEN issuance.
See review for exact file/blob references and bounded corrective scope.

## Decision
NP-01..04 ACCEPTED_SOURCE_ONLY; G2 coverage and three gate drafts require finite residual corrections.
Collector/accepted inventory/design stay closed. All live/apply/release/production permissions remain NO.
