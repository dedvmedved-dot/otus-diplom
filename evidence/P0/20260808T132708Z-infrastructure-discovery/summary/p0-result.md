# P0 Result
RUN_ID: 20260808T132708Z

overall_result: P0 NOT READY

nodes_expected: 3
nodes_processed: 2 (172.100.10.38, 172.100.10.40)
nodes_unreachable: 1 (172.100.10.39)

BMC-level discovery: PARTIAL (2/3)
OS-level discovery: NOT STARTED (SSH blocked on all nodes)

P0 cannot be submitted as PASS until:
  1. SSH access is provided for all three nodes.
  2. 172.100.10.39 is back online and inventoried.
  3. OS-level data (Astra version, kernel, disk by-id, network config, time sync) is collected.
  4. Node mapping (serial -> node-01/02/03) is confirmed.
