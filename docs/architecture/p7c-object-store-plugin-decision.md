# P7C Object-Store Plugin Decision

| Candidate | Velero compat | Provider compat | Known issues | Image digest verified | Recommendation |
|---|---|---|---|---|---|
| velero-plugin-for-aws v1.14.2 | Velero 1.18.x | S3-compatible (provider-dependent) | non-AWS tagging/API quirks possible | YES (abe29a7b...) | PROPOSED (pending provider) |
| velero-plugin-for-aws v1.14.1 | Velero 1.18.x | S3-compatible | - | not re-verified | alternative |
| velero-plugin-for-aws v1.14.0 | Velero 1.18.x | S3-compatible | - | not re-verified | older |

OBJECT_STORE_PLUGIN_DECISION=BLOCKED_NO_S3_PROVIDER

The plugin family is identified (velero-plugin-for-aws, candidate v1.14.2), but the
final provider-specific selection cannot be made until the Owner provides the
S3 provider type/endpoint. Non-AWS S3 requires a compatibility canary.

Proposed immutable lock entry (P7C-B only, NOT written to images.lock in P7C-A):
```yaml
- component: velero-plugin-for-aws
  image: docker.io/velero/velero-plugin-for-aws
  tag: "v1.14.2"
  digest: "sha256:abe29a7b360231e359f7aaee79668141bd619ab6989c7cc78d041110987f6ca2"
  platform: linux/amd64
```
