# ADR-PROPOSAL-P5-DRBD-DEPLOYMENT-MODEL

STATUS: REJECTED / SUPERSEDED
SUPERSEDED BY: ADR-003-P5-drbd-operator-version-alignment.md
REASON: upstream factual version mapping correction

## Context
P5A выявил несовместимость locked DRBD 9.2.18 с in-kernel DRBD 8.4.11 в Astra
Linux SE 1.8.5.46 (kernel 6.1.158-1-generic). Locked DRBD 9.2.18 требует
out-of-tree модуля. Build toolchain (gcc/make/dkms) отсутствует на всех узлах.

## Decision required
1. Deployment model для DRBD 9.2.18:
   - (a) LINBIT DKMS source build (требует установку gcc/make/dkms/headers в P5B);
   - (b) prebuilt LINBIT package для Astra/kernel (если официально доступен).
2. drbd-utils version lock (отсутствует в versions.lock).
3. Разрешение установить read-only health tools (smartmontools/sg3-utils) до P5B.

## Consequences
Без решения: P5A = BLOCKED (DRBD 9.2.18 kernel compatibility NOT VERIFIED;
candidate health NOT VERIFIED).

## Decision
[PENDING ARCHITECT]

Не реализовывать до APPROVED.
