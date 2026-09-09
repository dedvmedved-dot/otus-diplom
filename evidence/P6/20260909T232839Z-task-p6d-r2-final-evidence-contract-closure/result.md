# TASK-P6D-R2 — result

TASK: TASK-P6D-R2
RUN_ID: 20260909T232839Z
BASELINE: daf492ff1152f09eea16611e157a1d1c45a39269
MODE: FINAL EVIDENCE CONTRACT CLOSURE / REPRODUCIBLE NEGATIVE-TEST PROOF

## Итог: PASS

P6D-R1 infrastructure result remains historical and unchanged.
R2 closes missing raw evidence files (LB Service, HTTPRoute raw JSON) and
replaces summary-only negative-test claims with reproducible executable evidence.

## Raw evidence closed (R1 gaps)
- 22-gateway-status-raw.json (raw Gateway JSON) + 23-summary (Accepted/Programmed True).
- 25-loadbalancer-service.txt (command/timestamp/type/LB IP/exit) + 25a-raw.json.
- 27-httproute-status.txt (Accepted=True ResolvedRefs=True observedGeneration=1) + 27a-raw.json.
- LB IP = 172.30.140.110 (approved pool .110-.119).
- data-plane digest envoy@sha256:9e24a3b4... (pinned, no drift).
- MetalLB L2 announcer node-03 (speaker-d956q), BGP/BFD=0.

## External E2E re-validated (raw source proof)
- atlas-1.brest.local / 172.30.20.51 (raw source proof in each probe).
- Probe 1/2/3: SOURCE_IP=172.30.20.51, CURL_EXIT=0, HTTP 200 + P6D_R2_EXTERNAL_E2E_OK.
- Negative path: HTTP 404 (marker absent).
- Internal control: HTTP 200 + marker (INTERNAL CONTROL ONLY).

## Reproducible negative-test harness
- ansible/tests/p6d_verifier_negative_tests.py (committed, inspectable).
- 14 tests, synthetic inputs only, no cluster/production mutation.
- Run: TESTS_TOTAL=14, TESTS_EXPECTED_RESULT_MATCH=14, TESTS_FAILED=0, HARNESS_EXIT=0.
- Static safety: no kubectl/nmcli/ip route calls.

## Cleanup + residue
- p6d-r2-validation deleted (NotFound). Residue counters ALL zero:
  P6D_R2_NAMESPACE_COUNT=0, GATEWAY_COUNT=0, HTTPROUTE_COUNT=0,
  LB_SERVICE_COUNT=0, ENVOY_DATAPLANE_COUNT=0, VALIDATION_RESIDUE_TOTAL=0.
- Post-cleanup: HTTP=000, marker absent.

## Final production foundation (unchanged)
- Kubernetes v1.36.2; Envoy 1.9.1 1/1; GatewayClass eg Accepted; MetalLB 3/3;
  BGP/BFD=0; kube-vip .100 svc_enable=false; persistent route preserved.

Hermes НЕ присваивает статусы. Ждёт независимый GitHub Connector audit.
