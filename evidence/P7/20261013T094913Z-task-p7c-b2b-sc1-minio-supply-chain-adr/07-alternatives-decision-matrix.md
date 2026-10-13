# P7C-B2B-SC1 — Alternatives Decision Matrix

## A0 — Old September Community prebuilt binary (RELEASE.2025-09-07T16-13-09Z)
Advantages: simple deployment (downloadable binary exists).
Disadvantages: older than the selected final security source release;
archived branch; no future maintenance stream can be assumed.
Decision: REJECT.

## A-R1 — Final selected Community security source tag built from official source
Tag: RELEASE.2025-10-15T17-29-55Z (commit 9e49d5e7a648f00e26f2246f4dc28e6b07f8c84a).
Advantages: minimal architectural change; maintains accepted MinIO/S3 design;
uses the final selected source security release.
Disadvantages: archived Community upstream; no future supported security-update
stream can be assumed; requires controlled source build and compensating controls.
Decision: PROPOSED.

## B — Current supported commercial/vendor MinIO offering
Advantages: vendor-supported maintenance path.
Disadvantages: licensing/commercial dependency; different product/support model
may require separate acceptance.
Decision: NOT SELECTED FOR CURRENT DEMO.

## C — Alternative S3-compatible implementation
Advantages: potential maintained alternative.
Disadvantages: requires separate compatibility analysis (Velero,
CloudNativePG/Barman, TLS, Object Lock, versioning, restore, operating model).
Decision: NOT SELECTED.
