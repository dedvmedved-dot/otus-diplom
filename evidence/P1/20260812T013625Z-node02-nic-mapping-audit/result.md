# TASK-007-NODE02-NIC-MAPPING-AUDIT — result

TASK: TASK-007-NODE02-NIC-MAPPING-AUDIT
RUN_ID: 20260812T013625Z
NODE: node-02
READ-ONLY: YES
CONFIG CHANGES: NONE

BOND0 RUNTIME SLAVES: ens2f2 ens2f3
BOND0 NM PROFILE SLAVES: ens2f2 (bond0 port 1), ens2f3 (bond0 port 2)
BOND1 RUNTIME SLAVES: NONE
BOND1 NM PROFILE SLAVES: ens2f2 (bond1 port 1), ens2f3 (bond1 port 2)

ENS2F0: MAC=6C:B3:11:61:D3:20 MASTER=NO_MASTER PROFILE=none CARRIER=1
ENS2F1: MAC=6C:B3:11:61:D3:22 MASTER=NO_MASTER PROFILE=none CARRIER=1
ENS2F2: MAC=6C:B3:11:61:D3:24 MASTER=bond0 PROFILE=bond0 port 1 CARRIER=1
ENS2F3: MAC=6C:B3:11:61:D3:26 MASTER=bond0 PROFILE=bond0 port 2 CARRIER=1

VLAN700 PARENT: bond0
MANAGEMENT PATH: 192.168.194.40 → bond0.700 → bond0 (802.3ad) → ens2f2 + ens2f3

SOURCE OF TRUTH EXPECTED: bond0=ens2f0+ens2f1, bond1=ens2f2+ens2f3
RUNTIME MATCH: NO

MISMATCH:
- ens2f0 and ens2f1 are FREE (UP, carrier=1, NO_MASTER, no NM profile)
- ens2f2 and ens2f3 currently serve bond0 as management path
- NM bond1 profiles reference ens2f2+ens2f3 (conflict — same interfaces as bond0)

Q1 — Bond0 slaves: ens2f2 ens2f3
Q2 — Bond0 NM profiles: bond0 port 1=ens2f2, bond0 port 2=ens2f3
Q3 — Bond1 NM profiles: bond1 port 1=ens2f2, bond1 port 2=ens2f3
Q4 — Management path: ens2f2+ens2f3 (bond0 → VLAN700 → 192.168.194.40)
Q5 — Runtime matches Source of Truth: NO
Q6 — Specific mismatch: bond0 uses ens2f2+ens2f3 instead of ens2f0+ens2f1; ens2f0/ens2f1 are FREE
Q7 — LLDP: NOT AVAILABLE
Q8 — ens2f0+ens2f1 free for future bond: PROVEN YES (kernel NO_MASTER, no NM profile, free)

NETWORK ACTIVATION D: NOT EXECUTED
NETWORK CHANGES: NONE
STORAGE CHANGES: NONE
REBOOT: NO
SECRET AUDIT: (pending)
