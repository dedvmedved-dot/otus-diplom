# P8C-R1 RV-02 — offline identity binding + follow-up design (G1/G2/G3)

Date: 2026-10-27. Source-only work; no cluster access, no live reads, no token/credentials
used for registry research (anonymous quay.io pull scope only).

## G1 — access records (no new connections)
- Method used: `ssh-keyscan 192.168.194.38` → `known_hosts`, then SSH with
  `StrictHostKeyChecking=yes`. This is trust-on-first-use, NOT an independent prior-trusted
  comparison.
- node-01 host-key fingerprints (presented; private keys/known_hosts not included):
  - ECDSA   `SHA256:mnHCOea9pokSOq2BUVt7IerK949RXaNu6y7UAzekkKk`
  - RSA     `SHA256:nf5b31oYdnKqJEr3dHSAf3M9VXkGuGATtLuCZPVkKWs`
  - ED25519 `SHA256:4Janc/G5wzV6Yfi8gPTz55u/81atXF1xzjkDIISJjvc`
- Credential: root-only file `/etc/hermes/pak_root_pass.txt` (mode 600, root, 19 bytes), value
  never echoed; no rotation record available in existing records.
- **ACCESS_COMPLIANCE=NOT_FULLY_EVIDENCED** — no prior trusted fingerprint source and no rotation
  record were found; the one-run budget is already consumed, and no re-verification login was made.

## G2 — immutable Calico identity relation (VERIFIED)
Chain proven via official `quay.io/v2/calico/node` metadata, each link SHA256-verified on exact
bytes (full record: `identity-chain.json`):
```text
pinned manifest-list  sha256:f4fafd8… (mediaType docker manifest.list.v2, 4 platforms)
  └─ amd64 platform manifest sha256:12262c95… (docker manifest.v2, 1 layer)
       └─ amd64 image CONFIG sha256:6bc9fa4… (application/vnd.docker.container.image.v1+json)
            = OBSERVED runtime imageID (bare sha256:6bc9fa4…)
```
- IDENTITY_CHAIN=VERIFIED: every computed SHA256 equals its requested digest.
- RUNTIME_IMAGEID_INTERPRETATION=PROVEN: the observed `6bc9fa4…` is the **amd64 image CONFIG
  digest**, a verified descendant of the pinned manifest-list — NOT the manifest-list digest and
  NOT a platform-manifest digest.
- This explains the gate result: `IMAGE_ID_RE` rejected the bare `sha256:…` form before digest
  comparison, and `endswith(PINNED_DIGEST)` compared against the manifest-list digest, not the
  config digest.
- **Candidate identity contract (for Architect review — NOT implemented)**: accept the pre-computed
  amd64 config digest `sha256:6bc9fa4dc2b10ca1d4b97a1cd570036651898cea8b3c3bcbb1d55cf813e43f65`
  (bare or `containerd://`/`docker-pullable://` prefixed) as the bound runtime imageID for
  `quay.io/calico/node@sha256:f4fafd8…` / `:v3.32.0`. The digest is fixed offline, not looked up at
  runtime and not derived from the mutable tag. No code change is made here.

## G3 — follow-up read design (REVIEW_READY)
`followup-read-design.md`: C3/C4/C5 (post identity binding), ClusterNetworkPolicy v1alpha2
(official v1.36.2 schema), HostEndpoint/Tier + D1 policy inputs, DNAT/enforcement + Barman
directed-flow — each as requirement → fact → UNKNOWN → read → argv/GVR → typed fields → version
pin → deps → output/error → FLOW-ID. No new collector or live command is executed.

## Status
```text
RECOVERY_MAIN_SHA: f75c492f424cd133c22fa63b1a99b8e5e2f18842
IDENTITY_CHAIN: VERIFIED
RUNTIME_IMAGEID_INTERPRETATION: PROVEN (amd64 config digest)
ACCESS_COMPLIANCE: NOT_FULLY_EVIDENCED
FOLLOWUP_READ_DESIGN: REVIEW_READY
PHASE2_NEW_RUN_APPROVED: NO
NETPOL_APPROVED_FOR_APPLY: NO
P8C: NOT_FINAL_ACCEPTED · P8D–P8G/P9: NOT_AUTHORIZED
```
STOP. This is a source-only package; the identity-chain proof and candidate contract await
Architect review.
