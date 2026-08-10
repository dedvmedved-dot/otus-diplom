# Node Mapping
RUN_ID: 20260810T141413Z

NODE MAPPING: PARTIALLY VERIFIED

| Endpoint | BMC Serial | DMI Serial | Hostname | Vendor (BMC) | Vendor (DMI) | Target |
| --- | --- | --- | --- | --- | --- | --- |
| 172.100.10.38 | 0112220E3D | DENIED (no root) | astra-38 | YADRO | YADRO X2-205 | node-01 |
| 172.100.10.39 | UNREACHABLE | UNREACHABLE | UNREACHABLE | UNREACHABLE | UNREACHABLE | node-03 (TBD) |
| 172.100.10.40 | 7490778100035 | DENIED (no root) | astra-40 | COMPAL | YADRO X2-205 | node-02 |

NOTE: 172.100.10.40 — BMC reports COMPAL, but OS-level DMI (sys_vendor/product_name)
reports YADRO X2-205. This discrepancy needs Owner clarification. The BMC serial
7490778100035 is the authoritative identifier until resolved.

Basis for mapping:
- astra-38 = node-01 (lowest hostname number, YADRO serial 0112220E3D)
- astra-40 = node-02 (YADRO X2-205 per DMI, COMPAL serial per BMC)
- astra-39 = node-03 (presumed, UNREACHABLE)
