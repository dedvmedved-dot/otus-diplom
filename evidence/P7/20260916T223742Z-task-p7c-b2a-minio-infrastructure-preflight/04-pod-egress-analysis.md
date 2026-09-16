=== 04-pod-egress-analysis ===
--- NetworkPolicies (all ns) ---
No resources found
--- Calico IPPool / felix config ---
NAME                  AGE
default-ipv4-ippool   21d
--- node-01 routing table (pod egress path) ---
default via 192.168.194.1 dev bond0.700 proto static metric 400 
10.244.184.0/26 via 172.30.140.102 dev tunl0 proto bird metric 1024 onlink 
blackhole 10.244.190.0/26 proto bird 
10.244.190.5 dev cali6862648ce58 scope link metric 1024 
10.244.190.6 dev cali6b0fdb09c85 scope link metric 1024 
10.244.190.7 dev calid1e7755dc79 scope link metric 1024 
10.244.190.33 dev cali0c57bc62666 scope link metric 1024 
10.244.254.64/26 via 172.30.140.103 dev tunl0 proto bird metric 1024 onlink 
172.30.20.0/24 via 172.30.140.1 dev bond0.140 proto static metric 404 
172.30.140.0/24 dev bond0.140 proto kernel scope link src 172.30.140.101 metric 404 
172.30.141.0/24 dev bond1.141 proto kernel scope link src 172.30.141.101 metric 403 
172.30.143.0/24 dev bond0.143 proto kernel scope link src 172.30.143.101 metric 401 
192.168.194.0/24 dev bond0.700 proto kernel scope link src 192.168.194.38 metric 400 
--- ip rule ---
0:	from all lookup local
32766:	from all lookup main
32767:	from all lookup default

--- R1 CORRECTION (summary/interpretation, raw output above unchanged) ---
The raw observations prove only the NODE-level VLAN143 route (bond0.143 UP,
172.30.143.0/24 kernel route on all three nodes) and the absence of NetworkPolicies.

They do NOT prove actual Velero/node-agent/data-mover Pod egress to MinIO, because
MinIO and Velero/node-agent are not deployed and no Pod-origin TCP/TLS/S3
connectivity has been executed.

VLAN143_NODE_PATH = PASS (node-level, proven)
POD_TO_MINIO_PATH = NOT_PROVEN (application-Pod S3 reachability requires the
deployed-context P7C-B2 Network Gate, not node routing alone).
