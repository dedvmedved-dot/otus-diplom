# P8C RV-02 — access path (G1)

## Checked (single verification, not a probe loop)
- `kubectl` binary: ABSENT on the Hermes host.
- `/etc/kubernetes/admin.conf`: ABSENT.
- `~/.kube/config`: ABSENT.
- Prior verified connectivity (evidence `…-native-pg17/cluster-connectivity.txt`):
  PAK GW `192.168.194.1` reachable via tun0; nodes `172.30.140.101/102/103:22`
  timed out; node-03 mgmt `192.168.194.39:22` answers SSH but requires credentials
  not held by this host (Permission denied under BatchMode).

## Conclusion
- Path A (local kube-context): unavailable.
- Path B (existing authorized session on a node/jump host with kubectl): not
  reachable from this host.
- Path C (operator runs the prepared package in their session): required — see
  `operator-handoff.md`.

No access was created, no subnet scan, no BMC/SOL/IPMI bypass, no credential
guessing, no secrets requested in chat. Per task G1, when A/B/C are unavailable:
finish independent preparation (done) + issue one concrete owner request (in
result.md) + record BLOCKED_EXTERNAL.
