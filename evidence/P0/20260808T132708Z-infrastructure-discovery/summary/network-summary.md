# Network Summary
RUN_ID: 20260808T132708Z

## Observed endpoints
| Endpoint | Reachable | BMC accessible | SSH |
| --- | --- | --- | --- |
| 172.100.10.38 | YES (ping 47ms) | YES (Redfish) | NO |
| 172.100.10.39 | NO | NO | NO |
| 172.100.10.40 | YES (ping 47ms) | YES (Redfish) | NO |

## Role of 172.100.10.x addresses
ROLE OF 172.100.10.x ADDRESSES: NOT VERIFIED
These are NOT the management/DRBD/BMC reference addresses (which are 172.30.x.x).
Possibilities: temporary deployment addresses, NAT/VPN translated addresses, or service addresses.
Determination requires OS-level access (hostname, IP configuration) — not available without SSH.

## Observed vs Reference
No OS-level networking data available (no SSH). All OBSERVED network values remain NOT VERIFIED.
Reference network (TR v4.0):
- Management: 172.30.140.101/.102/.103 (REFERENCE)
- DRBD: 172.30.141.101/.102/.103 (REFERENCE)
- BMC: 172.30.142.101/.102/.103 (REFERENCE)
