# Node Mapping
RUN_ID: 20260808T132708Z

NODE MAPPING: NOT VERIFIED

Hostnames are unknown (no SSH access, no OS-level discovery).
Serial numbers are known from BMC but cannot be matched to node-01/02/03 names
without either:
  - inventory document from Owner assigning serials to node names
  - OS-level hostname discovery (blocked: SSH not available)

Known serials:
  172.100.10.38 -> YADRO 0112220E3D (chassis: 7490001200475)
  172.100.10.39 -> UNREACHABLE
  172.100.10.40 -> COMPAL 7490778100035

IP addresses 172.100.10.x do NOT match the reference management subnet 172.30.140.0/24.
Their role in the PAK architecture is NOT VERIFIED.
