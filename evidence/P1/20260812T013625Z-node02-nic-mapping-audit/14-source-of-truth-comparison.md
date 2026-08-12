# Source of Truth vs Runtime — node-02

REPOSITORY EXPECTED:

bond0:
  ens2f0
  ens2f1

bond1:
  ens2f2
  ens2f3

RUNTIME OBSERVED (kernel + NM active):

bond0:
  ens2f2 (active)
  ens2f3 (active)

bond1:
  NONE (no slaves, kernel object exists)

ens2f0:
  FREE (carrier=1, NO_MASTER, no NM profile)

ens2f1:
  FREE (carrier=1, NO_MASTER, no NM profile)

MATCH:
NO — bond0 uses ens2f2+ens2f3, expected ens2f0+ens2f1

MISMATCH:
- ens2f0, ens2f1 are FREE (not in any bond)
- ens2f2, ens2f3 serve bond0 (management path)
- NM bond1 profiles reference ens2f2+ens2f3 (conflict with active bond0)
- Management path: 192.168.194.40 → bond0.700 → bond0 → ens2f2+ens2f3
