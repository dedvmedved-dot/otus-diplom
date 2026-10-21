# P8C-R1 RESUME-R3 — independent source work and external blockers

Date: 2026-10-21 UTC. Implementation evidence, not Architect acceptance.

- Recovery/base main: `17c832c1be518bdc70e300cbbdc2bbee3bfc201c` (Connector).
- User checkpoint: `d768c2603ec64f6c312e4f0ef24d8f6d2f943959`; main contained a newer scope-preserving Hermes source/evidence pair. It was retained, not overwritten.
- Governing review: `docs/architecture/P8C_R3_REVIEW_618d677_20261021.md`, Architect `27bd744856b61c35e7c66dbd1ea397d3e86f97ad`; inherited R3 closure task also checked in full.
- **Final application source SHA: `817f0ecef8da1cd756f4b6ab48d61e023764329a`.**
- Source tree: `36675399a5f85b7fa4b5937ad6ddedde3056232b`.
- Publication model: source commit parent is recovered main; evidence-only child; `update_ref(main, expected_sha=17c832…, force=false)`. The final evidence commit ID is reported after publication, not embedded recursively in itself.

## Outcome

`SOURCE_WORK=PARTIAL / BLOCKED_EXTERNAL`; all independent source/test/template work in this package is complete. Individual executed checks below PASS. No blanket RV-01…08 CLOSED or source-package acceptance is claimed.

1. **RV-02 full live inventory is blocked externally.** This workspace has no authorized cluster connection or kubectl. The repository confirms Barman controller namespace `cnpg-system` and declared TCP9090, but does not establish actual plugin/operator traffic, monitoring presence/absence, or Service/DNAT/CNI enforcement paths. `portal/networkpolicy/inventory.py` is a fixed read-only, projected-field collector ready for the previously authorized Hermes environment. Candidate manifests, both-side union tests and rollback plan are prepared; the API /24 and incomplete plugin/monitoring inventory are explicitly NOT approved. Raw current evidence must precede any allowlist completion or apply gate.
2. **Native PostgreSQL 17 regression qualification remains NOT_EXECUTED here.** No native PostgreSQL/container engine is installed; the current user namespace maps only UID0, and PostgreSQL refuses root execution. No security/UID-map bypass was attempted. An isolated PostgreSQL **17.5 WebAssembly engine (PGlite)** did execute all ten SQL integration tests using actual migrations, including schema drift and concurrent insert/update/prune semantics. This is useful SQL compatibility evidence, not native PG17/production TLS/HA qualification. Native regression commands are prepared in the CI template and can run in the already authorized isolated Hermes PG17 environment without dispatching CI or touching PAK.

The pending CI release is a deliberate gate, not a reason to request credentials or run it now.

## What changed

- Preserved the accepted one-collector-snapshot-per-response implementation and regression. DB event pages now use a bounded immutable server view (500 events, 32 cached views, 90-second TTL); concurrent inserts/updates/prunes cannot move rows between pages. View expiry/eviction, filters, collector revision and backend changes invalidate cursors.
- Exercised all 21 actual list-category paths with 201/501/second-page-error fixtures. Fixed truthful Partial/source reporting, including EndpointSlices, metrics and VolumeSnapshots. These are synthetic served-API tests, not a claim about live API pagination support.
- Connected collector Barman/WAL/Velero/metrics data through all 11 actual handlers and the actual DOM renderer. Freshness never demotes critical, stale/partial/error sources do not remain green, trusted empty results differ from failures, and page navigation really fetches the next cursor.
- Replaced diagnostic-only persistence with the production bounded queue/retry/flush path, stable batch IDs, platform and persistence transitions, cleanup failure visibility and latched irreversible loss. Expanded schema checks to types/nullability/identity/defaults/PK/UNIQUE/CHECK. TLS tests cover real synthetic certificate handshakes, fixed SNI/CA/minimum, no fallback and rejection of ambient PG variables before pgx parsing.
- Expanded both Owner helper mock suites without executing provisioning. Replaced the partial schema validator with pinned test-only JSON Schema 2020-12 validation, including format assertions and actual startup/stale/error/fallback responses.
- Prepared a release template using installed checksum-verified Go bytes, corrected immutable action refs, private-package fail-closed prerequisite, single-build digest/registry checks, job-scoped privileges, strict signed-payload source/subject checks and retained required artifacts. Template only; no `.github/workflows` mutation.

## Executed checks

All commands below exited 0; raw command/time/cwd/source/output/exit records are retained separately and concatenated in `raw-transcript.txt`.

| Check | Evidence |
|---|---|
| Go 1.27.3 archive checksum → installed binary identity; module verification | `01`, `02`, `19` logs |
| Static build, vet, uncached unit tests, race | `03`–`06` logs |
| Tagged integration vet (compile/static only) | `07-integration-vet.txt` |
| Both helper suites, 18 tests, from portal and repository cwd | `08`, `09` logs |
| Release payload/private/digest negative fixtures, 4 test groups | `10-release-checks.txt` |
| Actual renderer, fixture smoke, collector → 11 schema-validated handlers → DOM | `11`–`13` logs |
| WASM PostgreSQL 17.5 SQL compatibility, ten integration tests plus TLS config tests | `14-wasm-sql.txt` |
| Workflow YAML/shell syntax, immutable refs/permissions/static policy | `15-workflow-static.txt` |
| Heuristic source secret scan, no findings; explicit synthetic CI credential allowlist | `16-secret-scan.txt` |
| Actual pinned Cosign v3.1.3 Go GenerateStatement + strict payload checker | `17`, `18` logs |
| Public upstream rootlesskit checksum; official test-image manifest bytes/hash/header | `20` log and proof JSON |

`source-index.json` lists all 66 Portal blobs read back from the Connector source tree. Local bytes were checked against every Git blob SHA before AND after final tests. The workspace was a Connector-materialized source snapshot, not a clone with remote ancestry; no misleading `git status clean` claim is made. Its convenience local git history was never pushed. The remote Git tree/commit parent chain controls publication.

## Explicit non-results and gates

- Native PostgreSQL integration: NOT_EXECUTED in this workspace; WASM SQL compatibility: PASS with stated limits.
- Live NetPol inventory/CNI behavior: NOT_EXECUTED; offline candidate selector/union tests: PASS.
- Rootless OCI build, final-image SBOM/Trivy scan, registry push/private visibility, signatures and attestations: NOT_EXECUTED.
- Workflow publication/dispatch, real Owner helpers, live policies, production migrations/deployment: NOT_EXECUTED / NOT_APPROVED.
- Workflow token and existing infrastructure secrets: not used or requested.
- `PORTAL_UI=NOT_DEPLOYED`, `PORTAL_API=NOT_DEPLOYED`, `PORTAL_DB=NOT_CONNECTED` (application), `PLATFORM_STATUS=NOT_VISIBLE`, `PORTAL_URL=NONE`.
- `P8C=IN_PROGRESS / NOT_FINAL_ACCEPTED`; P8D–P8G/P9 NOT_AUTHORIZED. No accepted backup/restore/PITR/failover/failure test was repeated.

## Next executable work in the authorized Hermes environment

1. At this exact source SHA, run `go test -tags integration -count=1 -v ./internal/store` against an isolated native PG17 `portal_test` database. The integration suite rejects non-loopback/non-test targets and fails when the URL is unset. Record version, command and raw output; no production access.
2. Execute the prepared read-only inventory helper under the previously authorized context, attach safe raw command/time/output references to each PLAN row, and resolve monitoring/plugin/API-DNAT uncertainties without guessing labels/ports or widening CIDRs. No policy apply or destructive probe.
3. Add new evidence only and submit the complete package for independent Architect review. No Owner/release/runtime permission is implied by these source checks.

See `closure-matrix.md` for every review subpoint and `errata.md` for factual corrections to earlier claims. Historical evidence is unchanged.
