# Evidence — P0

Factual evidence for the P0 stage. Evidence is append-only in spirit: failures
and incomplete results are preserved, never edited to look successful. No secrets
may appear in any evidence file.

## Layout

```text
evidence/P0/<timestamp>-<activity>/
├── request.json      # what was asked
├── precheck.txt      # state before
├── before/           # captured state before (if applicable)
├── action.json       # what was done
├── timeline.csv      # timestamped steps (for failure tests)
├── after/            # captured state after
├── screenshots/      # if applicable, secret-free
└── result.md         # FACT / OBSERVATION / result: PASS/FAIL/INCOMPLETE/NOT VERIFIED
```

## Current contents

- `*-repository-bootstrap/` — evidence for TASK-002 repository bootstrap.

Actual node discovery evidence will appear only after authorized P0 access.
