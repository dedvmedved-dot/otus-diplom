# P8C RV-02 — operator handoff (run in the authorized session)

Hermes has NO reachable authorized kubectl context (kubectl and kubeconfig are
absent on the host; PAK nodes are not reachable over SSH). Per the task, do not
create access, scan, or bypass via BMC. Instead, an operator with an existing
authorized session runs the reviewed read-only package below and returns only the
sanitized non-secret result.

## Exact reviewed artifact
- Script: `portal/networkpolicy/inventory.py`
- SHA (git blob): `$(git hash-object portal/networkpolicy/inventory.py)` — recorded
  in the evidence `recovery.txt`, pinned before run.
- Offline mock tests: `portal/networkpolicy/inventory_test.py` (11/11 PASS),
  proving safe projection (managedFields/annotations stripped) + error categories.

## Command (from the checked-out repo root, in the authorized session)
```
python3 portal/networkpolicy/inventory.py \
  --context "<approved-context>" \
  --output "<new-empty-local-directory>"
```
- The output directory must NOT pre-exist (script refuses to overwrite).
- Replace `<approved-context>` with the operator's own approved kube-context name.
- Do NOT run inside a Portal pod or via production `kubectl exec`.

## What the script does
- Issues ONLY fixed `kubectl get` / `--raw` discovery reads (GET/LIST) with a
  15s request timeout and a 20s per-command cap.
- Projects every full object (NetworkPolicy/Gateway/GatewayClass/EnvoyProxy) to
  strip `managedFields` and `annotations` (including last-applied-configuration),
  keeping only identity/labels/spec/safe-status.
- Records per-command: UTC start/end, safe argv, exit code, projected stdout, and
  a safe error category (TIMEOUT / FORBIDDEN / API_NOT_SERVED / CONNECTION /
  GET_FAILED). No credentials, no tracebacks.

## What to return (sanitized, non-secret only)
- The generated `inventory.jsonl` (already projected; re-check it contains no
  `annotations`/`managedFields`/`secret`/`token`/`password`/`credential`).
- `kubectl version --client -o yaml` client version line and the server version
  line (`kubectl version -o yaml` is optional; return only version strings, never
  the full kubeconfig).

## Excluded (never return these)
- kubeconfig, tokens, passwords, private keys, `.env`, full CNI config files,
  full Secret/ConfigMap data, `kubectl config view` output, SSH/VPN configs.

## Review path
Paste the sanitized `inventory.jsonl` + version lines into the Architect review
channel (or commit them into a new evidence dir as non-secret facts). Hermes will
then reconcile PLAN/manifests/flow-matrix and advance the apply gate.
