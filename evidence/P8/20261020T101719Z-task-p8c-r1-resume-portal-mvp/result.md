TASK: P8C-R1 RESUME PORTAL MVP
INITIAL_REMOTE_MAIN_SHA: 8f7acffd05b7814a56a03e5feaaf82cbeeb87eae
APPLICATION_SOURCE_SHA: 1a0fa3ed88ecd380ac4a08475e5d40bbab866202
PREP_COMMIT_SHA: ded607d9868b575df382b8e3c75350139e4710c2
RELEASE_WORKFLOW_RUN: NOT_RUN
IMAGE_DIGEST: NOT_VERIFIED
FINAL_REMOTE_MAIN_SHA: <after-push>
F01-F10_CLOSURE: YES (build/vet/test/race PASS)
G0: PASS
G1: PASS (source rework closes all findings)
G2: PARTIAL (toolchain pinned; CI build/sign/push NOT executed)
G3: BLOCKED (requires R3 workflow run + R4 Owner provisioning)
G4-G8: NOT_EXECUTED
PORTAL_UI: NOT_DEPLOYED
PORTAL_API: NOT_DEPLOYED
PORTAL_DB: NOT_CONNECTED
PLATFORM_STATUS: NOT_VISIBLE
PORTAL_URL: NONE
BLOCKERS:
  1. R3: dispatch+verify p8c-portal-release.yml, obtain verified image digest
  2. R4: Owner runs provision-ui-auth.py + provision-registry-pull.py (credentials OUT_OF_BAND)
  3. R2: live NetworkPolicy rollout (after R3/R4)
HERMES_RESULT: BLOCKED
P8C: NOT_FINAL_ACCEPTED
P8D-P8G/P9: NOT_AUTHORIZED
