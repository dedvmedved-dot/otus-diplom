# P8C RV-02 — operator handoff (APPROVED, pinned read-only inventory)

OWNER_INVENTORY_SCRIPT_APPROVED=YES / OWNER_INVENTORY_HANDOFF_ALLOWED=YES for the
exact script bytes below, base collection only, in an already authorized operator
session. Acceptance gate:
`docs/architecture/P8C_RV02_ACCEPTANCE_b805dff_20261026.md`.

Hermes has NO reachable authorized kubectl context (kubectl and kubeconfig are
absent on the host; PAK nodes are not reachable over SSH). Per the task, do not
create access, scan, or bypass via BMC. An operator with an existing authorized
session runs this pinned package and returns only the sanitized non-secret result.

## Exact reviewed artifact (pinned, literal)
- Source commit: `9a98b385c5a484b0a8f79086b432b8b72289ccee`
- Script: `portal/networkpolicy/inventory.py`
- Git blob SHA-1: `5f0e2450358bfd9b08b542f013be5a914b9195a4`
- File SHA-256: `7806f494bcee93f31eb2cb0348d2cd8f7cbbf5743261336226a251643d8988a2`
- Offline mock tests: `portal/networkpolicy/inventory_test.py`
  (git blob `be985eb78a1b7f437d154a40b3564cab99243d07`, SHA-256 `6354b829…`); 42/42 PASS.

## Command (from the checked-out repo root, in the authorized session)
Verify the exact script hash FIRST, then run. If the hash differs, STOP — a
different script version is not authorized by this gate.
```sh
printf '%s  %s\n' \
  '7806f494bcee93f31eb2cb0348d2cd8f7cbbf5743261336226a251643d8988a2' \
  'portal/networkpolicy/inventory.py' |
sha256sum --check --strict - &&
python3 portal/networkpolicy/inventory.py \
  --context "<approved-context>" \
  --output "<new-nonexistent-local-directory>"
```
- Replace `<approved-context>` with the operator's own approved kube-context name.
- Replace `<new-nonexistent-local-directory>` with a NEW, not-yet-existing local
  path (the script refuses to overwrite an existing one).
- Do NOT run inside a Portal pod or via production `kubectl exec`.
- Do not use arbitrary latest-main bytes on the strength of this approval.

## What the script does (allowlist projection)
- Issues ONLY fixed `kubectl get` / `--raw` discovery reads (GET/LIST) with a
  15s request timeout and a 20s per-command cap.
- Full objects (NetworkPolicy / GatewayClass / Gateway / EnvoyProxy / CNPG Cluster /
  ObjectStore) are projected to an explicit per-kind field allowlist: identity,
  labels, selectors, ports, endpoints, and safe conditions only. Kind/name and
  every nested field type are validated; arbitrary spec/status fields, embedded
  pod templates, env, inline config and credentials never enter the output. URL
  facts keep origin only (scheme://host[:port]); unsupported scheme/type, bad
  authority/port and non-string values are omitted (never raw); IPv6 brackets are
  preserved. ObjectStore endpointURL/destinationPath are origin-sanitized; only
  the secret-ref NAME is kept (never content).
- Malformed JSON or wrong object shape fails closed (PARSE_ERROR, empty output,
  nonzero exit) — no raw-body fallback.
- Records per-command: UTC start/end, exact argv (including `--raw`), exit code,
  projected stdout, and a safe error category (PARSE_ERROR / TIMEOUT / FORBIDDEN /
  API_NOT_SERVED / CONNECTION / GET_FAILED).

## What this resolves vs what stays UNKNOWN
- The base inventory resolves: existing workload identities/labels, Services/
  EndpointSlices, namespace labels, NetworkPolicy union, Gateway/EnvoyProxy
  object conditions, CNPG Cluster/ObjectStore declared config, PodMonitor/
  ServiceMonitor discovery, and node name/addresses/podCIDRs (no annotations).
- It does NOT prove observed traffic, packet DNAT enforcement, or CNI behavior.
  The eight UNKNOWN gaps (Barman plugin direction, API DNAT, monitoring scrape
  identity, DNS, S3 routing, Envoy ownership, baseline union, CNI semantics) are
  mapped in `flow-matrix.md` / `gaps.md`; each closes only when the corresponding
  raw record is returned AND reviewed. inventory.jsonl + server version alone does
  not close them.

## What to return (sanitized, non-secret only)
1. The generated `inventory.jsonl` (re-check it contains no `annotations`/
   `managedFields`/`secret`/`token`/`password`/`credential` values).
2. Source SHA + the actually verified script SHA-256 (the `sha256sum --check`
   output line).
3. UTC start/end time and the process exit code.
4. `kubectl version` — client and server version strings from the SAME context.
5. If exit != 0: retain the safe per-command categories (PARSE_ERROR / TIMEOUT /
   FORBIDDEN / API_NOT_SERVED / CONNECTION / GET_FAILED) and the partial result;
   report the failing read + category, do NOT hide the nonzero exit or relabel it
   PASS, and do not send raw stderr or credential-bearing text.

## Excluded (never return these)
- kubeconfig, tokens, passwords, private keys, `.env`, full CNI config files,
  full Secret/ConfigMap data, `kubectl config view` output, SSH/VPN configs,
  raw full objects.

## Review path
Paste the sanitized `inventory.jsonl` + version lines into the Architect review
channel (or commit them into a new evidence dir as non-secret facts). Hermes uses
them only to reconcile PLAN/manifests/flow-matrix for review; Hermes cannot and
does not advance the apply gate.
