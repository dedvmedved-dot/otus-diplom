# ADR-003 — P5 DRBD Operator Version Alignment

STATUS: APPROVED
APPROVED BY: Chief Architect
SOURCE TASK: TASK-015-R1

## Decision

Piraeus Operator 2.10.6
LINSTOR 1.33.2
LINSTOR CSI 1.11.0
DRBD 9.3.2

## Context

TASK-015 / P5A изначально фиксировал DRBD 9.2.18, полагая его bundled в
operator 2.10.6. Официальный changelog piraeus-operator v2.10.6 (2026-05-05)
указывает DRBD 9.3.2. Коррекция выравнивает P5 baseline с точным official
component set operator 2.10.6.

## Evidence

- Official changelog: https://piraeus.io/docs/ (v2.10.6 → DRBD 9.3.2)
- Official image config: quay.io/piraeusdatastore/drbd9-resolute:v9.3.2

## Consequences

- versions.lock: drbd 9.2.18 → 9.3.2.
- DRBD 9.3.2 kernel compatibility верифицируется compile-only в TASK-015-R1.
- P5B остаётся NOT AUTHORIZED до отдельной destructive authorization.
