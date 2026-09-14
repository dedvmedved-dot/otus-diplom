# P7C-B1 Risk Acceptance Candidate

Status: PROPOSED / NOT APPROVED

Risk description: CVE-2026-32283 — Go crypto/tls TLS 1.3 KeyUpdate handling.
Affected component/version: snapshot-controller image (v8.5.0 go 1.25.5 / v8.6.0 go 1.26.0).
Attack precondition: an unauthenticated TLS 1.3 KeyUpdate record causing persistent
  connection retention / resource consumption on the client side.
Impact: limited DoS on the controller's API-server connection.
Likelihood: low (client-side, trusted kube-apiserver; no network-exposed surface).
Existing controls: in-cluster controller, trusted API server, no inbound listeners.
Compensating controls: leader election + replicas=2 provide controller availability.
Fixed alternative: a future Go patch release (>= fixed threshold).
Reason not selecting fixed alternative: no published snapshot-controller image is
  built with a patched Go yet (both v8.5/v8.6 predate the fix).
Rollback trigger: P7C-B1 canary failure or runtime instability.
Upgrade trigger: when upstream releases a snapshot-controller built with a patched Go.
Expiry/review: re-review at P7C-B1 authorization and at next external-snapshotter release.

Hermes MUST NOT mark this accepted.
