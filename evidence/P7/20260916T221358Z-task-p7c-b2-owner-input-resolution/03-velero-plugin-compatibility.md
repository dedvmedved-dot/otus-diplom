# P7C-B2 — Velero / Plugin Compatibility Verification (independent)

## Velero 1.18.1

- Image: `docker.io/velero/velero:v1.18.1`
- amd64 digest (verified via Docker Hub registry API, manifest list -> linux/amd64):
  `sha256:2752a01188bd8f16572a76b3b2c4331a6a5337a5cbe65715c22ac7f91b31bfa8`
- Matches repo D1 prefix `2752a011...`: YES
- go.mod (v1.18.0): `k8s.io/client-go v0.33.3`, `k8s.io/api v0.33.3`, `k8s.io/apimachinery v0.33.3`
  -> built against K8s 1.33 client-go. Cluster is K8s 1.36.2 -> client-go version skew
  (N-3) exists; Velero 1.18 is a recent release and supports newer clusters, but this
  skew should be noted as an acceptance item (same pattern as D7 snapshot-controller).

## velero-plugin-for-aws v1.14.2

- Image: `docker.io/velero/velero-plugin-for-aws:v1.14.2`
- amd64 digest (verified via Docker Hub registry API):
  `sha256:abe29a7b360231e359f7aaee79668141bd619ab6989c7cc78d041110987f6ca2`
- Matches repo D2 digest `abe29a7b...`: YES (exact)
- go.mod: `github.com/vmware-tanzu/velero v1.18.0` -> built against Velero 1.18.x API
  -> compatible with Velero 1.18.1 (same minor line).
- SDK: aws-sdk-go-v2 v1.41.12 (service/s3 v1.101.0) -> supports S3-compatible endpoints
  via `s3Url`, `s3ForcePathStyle`, custom CA bundle, SSE.

## Conclusion

- D2 plugin selection is VERIFIED COMPATIBLE with Velero 1.18.1 (same minor, exact digest match).
- No ADR-PROPOSAL required; v1.14.2 is demonstrably suitable.
- K8s 1.36 vs client-go 1.33 skew: acceptance note (not a blocker; mirrors D7).
