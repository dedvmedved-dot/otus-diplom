# P0 Gate Checklist

Every item MUST be evidence-backed before P0 can be submitted to the Chief
Architect for `PASS`. Hermes does not self-assign P0 PASS. Current state:
infrastructure access not available → all discovery-dependent items are
unchecked.

## Node identity & hardware

- [ ] three nodes identified
- [ ] serials recorded
- [ ] CPU/RAM recorded
- [ ] Astra version recorded
- [ ] kernel recorded

## Storage safety

- [ ] storage WWN/by-id verified
- [ ] no ambiguous storage device
- [ ] storage remains untouched

## Network

- [ ] management addresses verified
- [ ] DRBD addresses verified
- [ ] BMC addresses verified
- [ ] no IP conflict
- [ ] no CIDR overlap
- [ ] DNS verified
- [ ] reverse DNS verified where required

## Time

- [ ] NTP synchronized
- [ ] time difference ≤ 1 second

## External dependencies

- [ ] registry reachable
- [ ] S3 reachable
- [ ] PKI parameters known
- [ ] BMC isolation known/verified

## Compatibility & sources

- [ ] Astra/kernel/DRBD compatibility verified
- [ ] required versions available from approved/internal sources

## Gate

- [ ] no unresolved blocking prerequisite

---

**Status:** NOT READY — no authorized infrastructure access; discovery not
started. Repository bootstrap is complete but does not constitute P0 PASS.
