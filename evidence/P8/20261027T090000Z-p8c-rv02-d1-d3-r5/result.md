# P8C RV-02 — D1–D3 / R5 closure (review 7584df5)

Date: 2026-10-27 UTC. R4-B.1 CLOSED (identity diagnostic preserved). Code byte-identical
(supplemental.py blob `ad2edaa9…`, supplemental_test.py blob `8157b942…`, 33/33).

## D1 — typed per-read output + dispositions
`supplemental-design.md` §1 now maps every read (D1/D2/I1/C1-C5/S1-S2) to its projector,
type helpers, required-vs-optional (`allow_none`/`_dict_req`), normalization
(`origin_only`, secret-ref name/key), and missing/error/unsupported dispositions
(PARSE_ERROR / UNSUPPORTED / TIMEOUT / FORBIDDEN / API_NOT_SERVED / CONNECTION /
GET_FAILED), including the accepted UnsupportedIdentity outcome.

## D2 — Felix precedence + host/global/tier scope
§3 cites the calico-v3.32.0.yaml FelixConfiguration CRD (cluster-scoped `default`;
`nodeSelector` field) and states the precedence model: default resource is the base;
node-scoped FelixConfiguration / node annotations / env overrides are NOT read by the
bounded collector → effective per-node mode + policy union UNKNOWN (not inferred from
default alone).

## D3 — source-backed Barman/API/DNS interpretation
§4 resolves the 9090 label: `plugin-barman-cloud-v0.13.0-release.yaml` Service
`barman-cloud` (port 9090, `cnpg.io/pluginPort: "9090"`) + container arg
`--server-address=:9090` → the plugin's RPC server surface invoked by CNPG (not a
per-instance sidecar, not a DB/S3 path); wire protocol left UNRESOLVED. Four-role
distinction retained; S3 port not assumed (443 not asserted). §5 interprets API/DNS
under Calico CNI with DNAT/enforcement UNKNOWN.

## R5 — exact evidence provenance
`coverage-matrix.md`: evidence root 080000Z; current review bindings
(7584df5-review/observations.json `valid_unsupported_identity` = fix, `literal_main_path.calls`,
execution.json 33-test run); the 010ff33-review `valid_unsupported_identity` marked
HISTORICAL (defect, not closure); Felix row uses a document check (not an unrelated test);
full repo paths + exact test IDs + source SHA.

## Status
```text
RECOVERY_MAIN_SHA: 08c08165ceb0ab9ab324c489261a7e946c9a8fbf
FINAL_SOURCE_SHA: 72c0a1aed924f9353b560cf2a54a249068674218
SUPPLEMENTAL_TESTS: 33/33 PASS (code unchanged)
R2/R3/R4-A/R4-B.1: CLOSED; D1/D2/D3: complete; R5: provenance corrected
PHASE2_LIVE_READS_APPROVED: NO
OWNER_PHASE2_HANDOFF_ALLOWED: NO
NETPOL_APPROVED_FOR_APPLY: NO
BASE_INVENTORY_ARTIFACT_REVIEW: ACCEPTED_WITH_LIMITS; INVENTORY_EXIT_CODE=1 (preserved)
FLOW_MATRIX_COMPLETE: NO
PHASE2_PACKAGE_REVIEW_READY: YES
P8C: NOT_FINAL_ACCEPTED; P8D–P8G/P9: NOT_AUTHORIZED
CI_RELEASE / OWNER_HELPERS / PRODUCTION_MIGRATION_DEPLOYMENT: NOT_EXECUTED
```
