# P7C Chat Handoff — 2026-09-15

## Source of Truth

GitHub repository `dedvmedved-dot/otus-diplom`, branch `main`, is the only Source of Truth.

Pre-handoff HEAD verified by Connector:

`f2c9f332852d66a8b2504f5459f51c2d2cc80036`

On a new chat, do not trust this SHA blindly: independently read exact `main` HEAD first, then read this file.

## Accepted stage status

```text
P0-P6                 = FINAL ACCEPTED
P7A                   = FINAL ACCEPTED
P7B1                  = FINAL ACCEPTED
P7B2                  = FINAL ACCEPTED
P7C-A                  = FINAL ACCEPTED
P7C-B1                 = BLOCKED / NOT ACCEPTED
P7C-B2                 = NOT AUTHORIZED
P7C-C                  = NOT AUTHORIZED
P8                     = NOT AUTHORIZED
P9                     = NOT AUTHORIZED
```

Lean Gate principle applies: minimum process sufficient to prove technical correctness. Do not recreate long remediation chains for cosmetic/evidence-format issues.

## What P7C-B1 proved before rollback

CSI snapshot foundation itself worked through snapshot creation:

```text
snapshot-controller v8.6.0 x2 = Ready
VolumeSnapshot readyToUse     = true
LINSTOR backend snapshot      = Successful
```

Restore failed in the LINSTOR/DRBD path. Full rollback was completed and independently verified. Snapshot CRDs/controller/VSC/canary objects are absent. P1-P7B2 remained PASS.

Canonical blocker evidence starts at:

`evidence/P7/20260914T153507Z-task-p7c-b1-blocked-rollback/`

## Important diagnostic shift

Later valid-source testing proved the problem exists before snapshot restore:

- a fresh `piraeus-r2` PVC can remain with one diskful `UpToDate` and the second diskful `Inconsistent`;
- DRBD connection to node-02 can remain `Connecting` and non-progressing;
- therefore snapshot/CSI investigation is paused until base DRBD replication is healthy.

Relevant evidence:

- `evidence/P7/20260914T213111Z-task-p7c-b1-lab-r2/`
- `evidence/P7/20260914T220841Z-task-p7c-drbd-connection-diagnostic/`
- `evidence/P7/20260914T225847Z-task-p7c-drbd-endpoint-remediation/`
- `evidence/P7/20260915T075228Z-task-p7c-drbd-satellite-restart/`

## Current proven runtime facts

Accepted P5C2 architecture expects DRBD replication over VLAN141 only:

```text
node-01 = 172.30.141.101
node-02 = 172.30.141.102
node-03 = 172.30.141.103
protocol C
satellites hostNetwork=true
```

Current host/VLAN state is healthy and matches P5C2. `drbd141` interfaces exist in LINSTOR and `LinstorNodeConnection/p5c2-drbd-vlan141` is `Configured=True` with `Paths/drbd141/... = drbd141` for node pairs.

However, actual DRBD listeners for a fresh test resource remained asymmetric even after declarative reconcile and controlled restarts of satellite pods on node-01 and node-03:

```text
node-01 = 172.30.140.101:7000  # VLAN140
node-02 = 172.30.141.102:7000  # VLAN141
node-03 = 172.30.140.103:7000  # VLAN140
```

The restarts did not change this state. Fresh replication again failed to obtain a healthy VLAN141 mesh; node-02 could remain `Connecting` / `Inconsistent`.

Latest result:

`evidence/P7/20260915T075228Z-task-p7c-drbd-satellite-restart/result.md`

## New source-level finding — NOT YET an accepted remediation

Current LINSTOR node properties show:

`Aux/piraeus.io/configured-interfaces = ["default-ipv4"]`

on all three nodes, while `drbd141` exists as an additional LINSTOR interface.

Important caution: do **not** jump directly to a new `LinstorSatelliteConfiguration.spec.interfaces` field. Independent inspection of Piraeus Operator `v2.10.6` shows that `LinstorSatelliteConfigurationSpec` / `LinstorSatelliteSpec` do not expose such a field. Operator-managed interface ownership is tracked through `Aux/piraeus.io/configured-interfaces`, and the operator normally manages interfaces it derives from satellite Pod IPs.

Therefore the previous intuitive idea "just declare drbd141 as a managed interface in LinstorSatelliteConfiguration" is **not proven and may be invalid for v2.10.6**.

## First unfinished technical step

Before any further runtime mutation, perform one narrow read-only Piraeus/LINSTOR path-semantics audit for the exact versions:

```text
Piraeus Operator 2.10.6
LINSTOR 1.33.2
DRBD 9.3.2
```

Answer only these questions:

1. Is `Aux/piraeus.io/configured-interfaces=["default-ipv4"]` relevant to DRBD replication path selection, or only to operator ownership/control-plane interfaces?
2. Given that `LinstorNodeConnection` contains `Paths/drbd141/... = drbd141`, why do actual DRBD listeners on node-01/node-03 still use VLAN140?
3. What exact supported object/API controls the generated DRBD local/peer endpoint for a resource in LINSTOR 1.33.2?
4. Is the present `LinstorNodeConnection` representation complete, partially applied, stale, or semantically different from what the project assumed?
5. What is the smallest supported fix that restores VLAN141 for all DRBD resource connections without weakening quorum or redesigning the network?

Use source code/API/docs plus current GitHub evidence. If one small runtime read-only reproduction is needed, keep it isolated. Do not apply a fix until the Architect reviews the answer.

## Explicitly forbidden until that audit is accepted

```text
P7C-B1 retry
snapshot CRD/controller redeploy
Velero / P7C-B2 / P7C-C / P8
CSI patch/fork
quorum or TieBreaker weakening
network/routing/firewall redesign
manual drbdadm repair
invented Piraeus CR fields
```

## Governance

Read `docs/governance/project-governance.md` before issuing a Hermes task.

Hermes executes only explicitly authorized scope and never accepts its own work. Final acceptance is by ChatGPT after independent Connector audit.

## Start rule for the next chat

1. Independently verify exact `main` HEAD.
2. Read this handoff.
3. Read only the latest evidence files needed for the unresolved DRBD path question.
4. Do not re-run already completed experiments.
5. Continue from the read-only path-semantics audit described above.
