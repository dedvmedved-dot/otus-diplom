# TASK-P6B-R2 — Root Cause Analysis

## Root cause (proven, factual)

MetalLB speaker does NOT announce the LoadBalancer IP (172.30.140.110) because
every Kubernetes node carries the label:

  node.kubernetes.io/exclude-from-external-load-balancers = ""

(empty-string value, but the LABEL IS PRESENT on node-01, node-02, node-03).

MetalLB's layer2 controller treats PRESENCE of this label (regardless of value)
as "this node must not announce L2 addresses". Debug log evidence:

  layer2_controller.go:269 event="skipping should announce l2"
    ips=["172.30.140.110"] pool="p6-ingress-pool" protocol="layer2"
    reason="speaker's node has labeled
            'node.kubernetes.io/exclude-from-external-load-balancers'"

  layer2_controller.go:104 event="skipping should announce l2"
    reason="no available nodes"

Consequently no ARP responder is activated for .110, so ARP who-has .110 gets
no reply (observed in packet capture), while kube-vip .100 (a separate mechanism)
still replies normally.

## Why R1 evidence did not catch it

R1 HTTP 200 from node-01/node-02 was hairpin/kube-proxy local processing of
Service LoadBalancer traffic (externalTrafficPolicy=Cluster), NOT proof of
external L2 ARP advertisement. The ARP capture in R2 definitively distinguishes
the two: ARP who-has .110 -> no reply.

## Evidence chain

- 13-packet-capture-before.txt: ARP REQUEST who-has .110 (3x), NO reply;
  kube-vip .100 DOES reply (REPLY is-at 6c:b3:11:61:d3:22).
- 11-speaker-logs-events.txt (debug): "skipping should announce l2" with reason
  exclude-from-external-load-balancers + "no available nodes".
- 08-node-label-exclusion-audit.txt: label present on all 3 nodes (value "").

## Correction class

Removing the label `node.kubernetes.io/exclude-from-external-load-balancers`
from the three nodes is a node-label mutation. Per TASK-P6B-R2 §13 and §17, node
exclusion label removal is in the "NOT automatically authorized" class:

  "Not automatically authorized: remove node exclusion labels"

Therefore the correction requires Architect authorization.

STATUS: BLOCKED — ARCHITECT DECISION REQUIRED (root cause proven, correction
requires removal of node exclusion label, which is outside R2 auto-authority).
