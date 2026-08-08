# TASK-003 Result — P0 Technical Hardening

Task: TASK-003 — technical hardening of P0 before infrastructure connection
Model: anthropic/claude-opus-4.8
Stage: P0 (local repository changes only)
Documentation Correction Counter: 0/3 (NOT changed — this is a technical task)

## Three defects fixed

1. **Overly broad `.gitignore`** — removed `*secret*`, `*Secret*`, `*token*`,
   `*password*`, `*credentials*`. Now blocks concrete secret-bearing files
   (`.env`, `*.key`, `*.pem`, `*.p12/.pfx`, `id_rsa/ed25519/ecdsa`, `*.kubeconfig`,
   `admin.conf`, `vault-password*`, `*.vault`, `*.tfstate*`). Explicitly allows
   Secret-reference manifests (`external-secret*.yaml`, `secret-store*.yaml`,
   `cluster-secret-store*.yaml`, `*-secret-reference*.yaml`) and templates
   (`*.example`, `*.sample`, `.env.example`). Verified via `git check-ignore`
   (14/14 cases OK) — see gitignore-validation.txt.

2. **P0 preflight evidence** — `p0-readonly-preflight.yml` now captures full
   per-node evidence (rc + stdout + stderr for each approved read-only command),
   records missing LVM tooling as a factual result (`failable: true`, stderr
   kept), and writes ALL evidence on the controller via `delegate_to: localhost`.
   No evidence file is created on any target node. No target-mutating module is
   used. Directory layout: `evidence/P0/<ts>-infrastructure-discovery/node-XX/`
   plus `summary/`. Logic is prepared but does NOT pre-create a fake timestamped
   directory. See ansible-syntax-check.txt and readonly-static-check.txt.

3. **REFERENCE vs OBSERVED** — `docs/p0/infrastructure-passport.md` now uses
   REFERENCE / OBSERVED / MATCH columns for all per-node (incl. BMC .101/.102/.103)
   and cluster-wide network parameters. OBSERVED and MATCH remain `NOT VERIFIED`;
   REFERENCE was NOT copied into OBSERVED.

## Validation

- `.gitignore`: git check-ignore — 14/14 PASS.
- Ansible: `--syntax-check` rc=0 → SYNTAX VERIFIED. TARGET EXECUTION: NOT VERIFIED
  (no node access; not run against nodes).
- Static analysis: no target-mutating modules; all remote-facing file/copy tasks
  delegated to localhost; no remote shell for evidence.
- Secret scan (git grep whole tree + staged diff): PASS — no real values.

## Standing blockers (unchanged)

```text
TR v4.0 SOURCE FILE: NOT PRESENT — OWNER ACTION REQUIRED
PAT ROTATION REQUIRED — old compromised PAT must not be used for real P0
```

## Boundary

Did not connect to nodes. Did not modify infrastructure. Did not start P1.
Did not change the LLM model. P0 GATE: NOT READY.
