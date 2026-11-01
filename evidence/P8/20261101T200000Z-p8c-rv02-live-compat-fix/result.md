# P8C-RV02-LIVE-COMPATIBILITY-FIX — source correction evidence

Date: 2026-11-01 (UTC). Source-only offline correction per Architect review 3a0afb4. No live reads,
no cluster/SSH/registry access, no new gate consumption. R2/FU-01/FU-07/S1/identity-chain untouched.

## Two integration defects fixed

### LR-01 — F-I1 request/parser boundary
- F-I1 now issues exactly one literal raw GET
  `/api/v1/namespaces/kube-system/pods?labelSelector=k8s-app%3Dcalico-node&limit=200`
  (a real PodList with server resourceVersion), instead of `kubectl get pods -o json`
  (which kubectl formats as a generic `List`). No pagination / second page.
- Nonempty `metadata.continue` → PARSE_ERROR `COMPLETENESS` (block all five identity consumers);
  `>200` items → PARTIAL `OVERLONG`, complete=false, no identity approval, no projection.
- Malformed envelope/type → PARSE_ERROR; empty identity → UNSUPPORTED; valid-but-unbound digest
  → UNSUPPORTED with the safe projected identity retained. The exact image/config digest contract
  and fail-closed rules are unchanged.
- Finite value-free diagnostic stage codes on F-I1 records:
  `ENVELOPE | METADATA | COMPLETENESS | ITEM | IDENTITY | OVERLONG` (no raw values/tokens/objects).

### LR-02 — CNP schema pin + semantic alignment
- `CNP_SPEC_SHA256` repinned to `ff433d3463dfa2264a7a3ff6201baabf1ec789e98664aff3401a7ef79ae7ce5e`,
  the normalized spec subtree of `ansible/playbooks/files/calico-v3.32.0.yaml`
  (blob `21ea9b4b163305ea479bc7708965104465ffc716`, commit dd00e2f36fdae9cb91baab256ecf9ecf2f662249).
  This is the live F-CS hash exactly — the prior `770130a4…` was a different upstream candidate.
  Live schema drift is NOT established.
- `followup-typed-contract.json` `cnp.spec_schema` replaced with the Calico subtree;
  `canonical_spec_schema_sha256` and source provenance (repo/commit/blob) updated.
- CNP projector adds `destinationNamedPort` (string, preserved as supplied) as the fourth protocol
  alternative; keeps `destinationPort` number/range semantics.
- `_valid_cidr` now follows `isCIDR(self)`: host bits are permitted (e.g. `10.0.0.5/24`,
  `2001:db8::5/64`) and the value is preserved as supplied, never normalized; a bare IP without
  `/` and malformed CIDRs remain rejected.

## Tests
```text
followup_test.py: 116/116 PASS  (includes new TestI1Transport + CIDR/named-port + schema alignment)
supplemental_test.py: 36/36 PASS (unchanged)
Python 3.11.15
START_UTC=2026-11-01T19:56:54Z · END_UTC=2026-11-01T19:56:56Z
```

## File hashes
```text
followup.py:       blob c598428bac67f6869b2f67220f9e125c1bd2392f  sha256 7456851ef3c1d679b5a9ca1ec666bf3b7c4ee34c7d7ca761757e9185a5621ea9
followup_test.py:  blob 894df0d622cfe2e27358d95d0e7fb09b60dfe1b8  sha256 f7ba3d960e39229562c2023a918221c3509dc18837621154b381a14dfe326967
typed-contract:    blob cd92740a4b857c6b8c9226eba579e5d9525494d0  sha256 95d76352cb4235820af2684660379ff0436b624e5ebe4d55401f2a3343b3fd6b
```

## Status
```text
REVIEWED_MAIN_SHA (parent): 3a0afb45b07daa8ac5e5ceb41563fc518db87dc9
FOLLOWUP_SOURCE_COMPATIBILITY: FIXED (offline, source-only)
PHASE2_NEW_RUN_APPROVED=NO
NETPOL_APPROVED_FOR_APPLY=NO
P8C=NOT_FINAL_ACCEPTED · P8D–P8G/P9=NOT_AUTHORIZED
```
STOP for independent Architect review. No live rerun authorized by this source change.
