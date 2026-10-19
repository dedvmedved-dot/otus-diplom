# ADR-014 — CloudNativePG Kubernetes 1.36 Version Realignment

STATUS: ACCEPTED
ACCEPTED_BY: Chief Architect / Technical Authority
DATE: 2026-10-20
SOURCE_TASK: P8A-R1

## Authorization state

P7 = FINAL ACCEPTED / CONNECTOR VERIFIED
P8 = AUTHORIZED
P8A = AUTHORIZED
P8B = NOT AUTHORIZED
P8C_RUNTIME = NOT AUTHORIZED
P8C_INTERFACE_PREPARATION = AUTHORIZED
P9 = NOT AUTHORIZED

## Version decision

Kubernetes = 1.36.2
CNPG old = 1.29.1
CNPG old compatibility = NOT SUPPORTED ON K8S 1.36
CNPG old lifecycle = EOL (2026-09-29)
CNPG new = 1.30.1
CNPG new compatibility = SUPPORTED ON K8S 1.36 (also 1.34, 1.35; PostgreSQL 14-18)
PostgreSQL = 17.10

## Rationale

Exact upstream CloudNativePG v1.29.1 support matrix lists Kubernetes 1.33/1.34/1.35
and does NOT list Kubernetes 1.36. CloudNativePG 1.29.x reached EOL 2026-09-29.
CloudNativePG v1.30.1 support matrix includes Kubernetes 1.36 and PostgreSQL 17,
matching the platform's Kubernetes 1.36.2 and the locked PostgreSQL 17.10.

## Supersession

This ADR supersedes ONLY the CloudNativePG version entry of the original baseline
(1.29.1 -> 1.30.1). All other component versions remain unchanged.

Barman Cloud Plugin 0.13.0 and cert-manager 1.21.0 remain in versions.lock but are
NOT deployed in P8A. CNPG's own operator/webhook certificate mechanism is used;
cert-manager is not deployed unless an independently demonstrated hard dependency
exists.
