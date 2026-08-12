# node-02 NIC Mapping Table

| Linux NIC | Permanent MAC | PCI | Driver | Carrier | Speed | Kernel Master | NM Profile | NM Active | Runtime Role |
|---|---|---|---|---|---|---|---|---|---|
| ens2f0 | 6C:B3:11:61:D3:20 | 0000:18:00.0 | i40e | 1 | 10000 | NO_MASTER | none | — | **FREE** (UP, no master) |
| ens2f1 | 6C:B3:11:61:D3:22 | 0000:18:00.1 | i40e | 1 | 10000 | NO_MASTER | none | — | **FREE** (UP, no master) |
| ens2f2 | 6C:B3:11:61:D3:24 | 0000:18:00.2 | i40e | 1 | 10000 | bond0 | bond0 port 1 | ACTIVE | **Management (VLAN700 via bond0)** |
| ens2f3 | 6C:B3:11:61:D3:26 | 0000:18:00.3 | i40e | 1 | 10000 | bond0 | bond0 port 2 | ACTIVE | **Management (VLAN700 via bond0)** |

### NM Profile Conflicts

| Profile | interface-name | master | Active |
|---|---|---|---|
| bond0 port 1 | **ens2f2** | bond0 | ✅ ACTIVE |
| bond0 port 2 | **ens2f3** | bond0 | ✅ ACTIVE |
| bond1 port 1 | **ens2f2** | bond1 | ❌ INACTIVE |
| bond1 port 2 | **ens2f3** | bond1 | ❌ INACTIVE |

⚠️ bond1 port profiles reference the SAME physical interfaces (ens2f2, ens2f3) that currently serve management via bond0.
