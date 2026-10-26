# P8C RV-02 — TC-01…04 acceptance and base inventory gate

Date: 2026-10-26 (Europe/Moscow).
Reviewed source: 9a98b385c5a484b0a8f79086b432b8b72289ccee.
Reviewed evidence/main: b805dffe77b2ad5f936f4b8380514eac778cbaf5.
Governing targeted review: docs/architecture/P8C_RV02_REVIEW_a532bf7_20261026.md.

## Decision
TC-01…04=CLOSED / INDEPENDENTLY VERIFIED.
RV02_BASE_INVENTORY_SOURCE_REVIEW=PASS (bounded read-only collector scope).
OWNER_INVENTORY_SCRIPT_APPROVED=YES, ONLY for the exact script bytes below, base collection, and an existing authorized operator session.
OWNER_INVENTORY_HANDOFF_ALLOWED=YES.
This decision supersedes the earlier NO for this exact script only. It is not acceptance of live inventory, a NetworkPolicy plan/apply, the full Portal source/release, or P8C final acceptance.

## Source-of-truth audit
Connector main matched b805dff. Relative to f95f9c2: 2 ahead / 0 behind; six changed files limited to helper/tests/handoff plus three new evidence files.
Source9a98b38 -> evidence b805dff: only three NEW evidence files; script/test bytes unchanged.
No application runtime code, policy model, historical evidence, workflow or production manifest changes in this package.
Application runtime source remains the prior817f0ece reference; native PG17 evidence acceptance is preserved and was not rerun.

## Independent verification
Exact Connector bytes were checked before execution:
- inventory.py Git blob: 5f0e2450358bfd9b08b542f013be5a914b9195a4
- inventory.py SHA256: 7806f494bcee93f31eb2cb0348d2cd8f7cbbf5743261336226a251643d8988a2
- inventory_test.py Git blob: be985eb78a1b7f437d154a40b3564cab99243d07
- inventory_test.py SHA256: 6354b829de785472ca6ffd633456f3e6289ceff8fc4cdc6abb22c485e94244dd

| Requirement | Code | Actual independent evidence |
|---|---|---|
| TC-01 required objects/lists | _dict_req, _list_or_empty, required selector | All12 prior TC cases reject; sibling ingress/egress/listeners reject false/0/empty-string/empty-object; explicit empty rule/peer/selector/list accepted |
| TC-02 identity | _nonempty_str, _meta(namespaced) | Empty name/namespaced identity rejected; GatewayClass may omit namespace |
| TC-03 required enum members | _enum with explicit allow_none | Missing condition.status / expression.operator rejected; optional absent status and protocol behavior preserved |
| TC-04 range | numeric port required for endPort, bounds/order | Missing/named port with endPort rejected; named port without range and valid numeric range accepted |
| Prior typed leaves/output boundary | typed primitives and explicit nested projection | All23 prior invalid leaf cases reject, unknown expression member drops safely, no canary retained |
| URL/main/error logging | sanitize_url and main | 14 URL variants across both fields through main; 3 error categories with exact argv and parsed chronological UTC timestamps |
| Existing regressions | inventory_test.py | 42/42 tests PASS; no-overwrite, no-kubectl, malformed JSON, canary, timeout/OSError and per-kind projected facts preserved |

Executed, all exit0:
- python3 inventory_test.py -v — 42 tests PASS (includes table-driven23 malformed-leaf cases and12 TC cases).
- python3 prior_reproduce.py — prior defects closed; no canary retained.
- python3 remaining_cases.py — all12 observations PARSE_ERROR, empty output, exit1 from collector.
- python3 assurance_test.py -v — 4 tests PASS; parameterized URLs, sibling invalid list shapes, legitimate empty rule/peer, error timestamp/argv checks.
The observation scripts themselves exit0 to report observations; acceptance is based on their recorded collector results.
Only mocks/synthetic data were used; no actual cluster access. No Go/native PG/full Portal reruns were necessary.

## Authorized operator step
Hermes may now provide this pinned handoff to Owner without another source rework cycle.
Use portal/networkpolicy/operator-handoff.md from source9a98b38 together with this gate.
This is an inventory helper, not either provisioning helper.

In an already authorized operator session with Python3, kubectl and the approved context:
1. Obtain the script from source9a98b385c5a484b0a8f79086b432b8b72289ccee using an existing permitted repository access route. No new credentials are requested or transferred.
2. Verify the exact script hash before running. If hash differs, STOP. Do not run arbitrary latest-main bytes on the strength of this approval.
3. From repo root, substitute the approved context and a NEW, nonexistent local output directory:

~~~sh
printf '%s  %s\n' '7806f494bcee93f31eb2cb0348d2cd8f7cbbf5743261336226a251643d8988a2' 'portal/networkpolicy/inventory.py' | sha256sum --check --strict - &&
python3 portal/networkpolicy/inventory.py --context "<approved-context>" --output "<new-nonexistent-local-directory>"
~~~

4. Record UTC start/end, process exit code, script SHA256/source reference and client/server version strings from that same authorized context. Return the generated inventory.jsonl after local review for sensitive values.
5. Return only projected records and safe version/status metadata. Never return kubeconfig, credential/token/private-key material, raw full objects, Secret/ConfigMap data or credential-bearing logs.
If the command returns nonzero, retain its safe per-command categories and partial result; do not relabel it PASS or invent empty/healthy facts. Report the failing read and category, without raw stderr/credentials. No access repair or alternate bypass is authorized.

The script has no platform mutation calls; its output-file creation is local only. Do not run via production exec or inside the Portal pod.
No authorized session available -> remain BLOCKED_EXTERNAL; do not rerun offline development or access scans merely to produce a new STOP.

## Hermes continuation after receipt
- Verify source/script binding, exit/categories, timestamps, inventory completeness and secret-safe output.
- Reconcile base observations into the existing14 FLOW-IDs and8 gaps, preserving UNKNOWN where data does not prove the claim.
- Keep optional API absent/forbidden/timeout distinct from empty resource lists.
- Do not interpret the base collection as proof of traffic, DNAT/CNI enforcement, monitoring completeness or plugin direction.
- Phase2 CNI/plugin/monitoring/Gateway reads remain NOT_DEFINED/NOT_APPROVED until the collected discovery identifies an exact version-specific read/projection for separate review. No generic ConfigMap/spec dumps.
- Prepare any needed candidate PLAN/flow-matrix/manifests offline, with targeted tests only when changed; publish NEW sanitized evidence fast-forward/no force. Do not change historical evidence.
- STOP for Architect review of actual inventory and resulting policy candidate. Hermes cannot advance the apply gate.

## Unchanged gates/status
ACCESS_PATH=NONE on the reported Hermes host; an authorized operator session is still externally required.
NETPOL_LIVE_INVENTORY=NOT_EXECUTED / BLOCKED_EXTERNAL.
FLOW_MATRIX_COMPLETE=NO.
NETPOL_APPROVED_FOR_APPLY=NO.
CI_RELEASE / workflow publication/dispatch / real Owner provisioning helpers / production migration/deployment=NOT_EXECUTED and NOT AUTHORIZED by this decision.
Workflow token must not be used.
P8C=NOT_FINAL_ACCEPTED; P8D-P8G/P9=NOT_AUTHORIZED.
No access bypass/BMC/credential guessing, destructive tests, or accepted backup/restore/PITR/failover reruns.

## Reproduction
New evidence:
- evidence/P8/20261026-p8c-rv02-b805dff-acceptance/execution.json
- evidence/P8/20261026-p8c-rv02-b805dff-acceptance/assurance_test.py

For offline replay place exact source inventory.py/inventory_test.py beside assurance_test.py and the unchanged prior_reproduce.py/remaining_cases.py from evidence/P8/20261026-p8c-rv02-a532bf7-review/. Source and evidence refs are pinned above.
This is targeted collector acceptance, not a claim of comprehensive Kubernetes schema validation or live platform verification.
