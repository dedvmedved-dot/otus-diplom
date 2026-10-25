# P8C RV-02 — operator handoff (run in the authorized session)

Hermes has NO reachable authorized kubectl context (kubectl and kubeconfig are
absent on the host; PAK nodes are not reachable over SSH). Per the task, do not
create access, scan, or bypass via BMC. An operator with an existing authorized
session runs the reviewed read-only package below and returns only the sanitized
non-secret result.

## Exact reviewed artifact (pinned, literal)
- Script: `portal/networkpolicy/inventory.py`
- Git blob SHA-1: `a39aca5c8f7c614cb8990339de1d84430a935800`
- File SHA-256: `b6f6b1d2d6ea909ce72268fbd3d85d391551da9a3e073e532220c2fb60959fc5`
- Offline mock tests: `portal/networkpolicy/inventory_test.py`
  (git blob `1a49577f02d3dab317125b2f624630524d85cec0`, SHA-256 `221daddb…`); 27/27 PASS.
- Immutable source commit/reference is recorded in the delivery report (not a
  computed expression).

## Command (from the checked-out repo root, in the authorized session)
```
python3 portal/networkpolicy/inventory.py \
  --context "<approved-context>" \
  --output "<new-empty-local-directory>"
```
- The output directory must NOT pre-exist (script refuses to overwrite).
- Replace `<approved-context>` with the operator's own approved kube-context name.
- Do NOT run inside a Portal pod or via production `kubectl exec`.

## What the script does (allowlist projection)
- Issues ONLY fixed `kubectl get` / `--raw` discovery reads (GET/LIST) with a
  15s request timeout and a 20s per-command cap.
- Full objects (NetworkPolicy / GatewayClass / Gateway / EnvoyProxy / CNPG Cluster /
  ObjectStore) are projected to an explicit per-kind field allowlist: identity,
  labels, selectors, ports, endpoints, and safe conditions only. Arbitrary
  spec/status fields, embedded pod templates, env, inline config and credentials
  never enter the output. URL facts keep only scheme/host[:port]/path (userinfo,
  query and fragment removed). ObjectStore endpoints are sanitized; only the
  secret-ref NAME is kept (never content).
- Malformed JSON or wrong object shape fails closed (PARSE_ERROR, empty output,
  nonzero exit) — no raw-body fallback.
- Records per-command: UTC start/end, exact argv (including `--raw`), exit code,
  projected stdout, and a safe error category (PARSE_ERROR / TIMEOUT / FORBIDDEN /
  API_NOT_SERVED / CONNECTION / GET_FAILED).

## What this resolves vs what stays UNKNOWN
- The base inventory resolves: existing workload identities/labels, Services/
  EndpointSlices, namespace labels, NetworkPolicy union, Gateway/EnvoyProxy
  object conditions, CNPG Cluster/ObjectStore declared config, PodMonitor/
  ServiceMonitor discovery, and node CNI annotations.
- It does NOT prove observed traffic, packet DNAT enforcement, or CNI behavior.
  The eight UNKNOWN gaps (Barman plugin direction, API DNAT, monitoring scrape
  identity, DNS, S3 routing, Envoy ownership, baseline union, CNI semantics) are
  mapped in `flow-matrix.md` / `gaps.md`; each closes only when the corresponding
  raw record is returned AND reviewed. inventory.jsonl + server version alone does
  not close them.

## What to return (sanitized, non-secret only)
- The generated `inventory.jsonl` (re-check it contains no `annotations`/
  `managedFields`/`secret`/`token`/`password`/`credential` values).
- `kubectl version -o yaml` — client + server version strings only.

## Excluded (never return these)
- kubeconfig, tokens, passwords, private keys, `.env`, full CNI config files,
  full Secret/ConfigMap data, `kubectl config view` output, SSH/VPN configs.

## Review path
Paste the sanitized `inventory.jsonl` + version lines into the Architect review
channel (or commit them into a new evidence dir as non-secret facts). Hermes uses
them only to reconcile PLAN/manifests/flow-matrix for review; Hermes cannot and
does not advance the apply gate.
