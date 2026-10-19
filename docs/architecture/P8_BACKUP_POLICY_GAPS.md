# P8 Backup Policy Gaps (TR v4.0 traceability)

Known final-P8/P9 policy items. They do NOT invalidate P8B native backup
functionality and MUST NOT disappear from future acceptance documentation.

```text
TR_PG_WAL_14D                        = IMPLEMENTED_POLICY
TR_PG_FULL_8_COPIES                  = IMPLEMENTED_POLICY_CAPABLE
TR_PG_INCREMENTAL_DIFFERENTIAL_14    = NOT_IMPLEMENTED_IN_SELECTED_PLUGIN_PATH
TR_MONTHLY_CONTROL_12                = DEFERRED_TO_P8G_P9_POLICY_CLOSURE
```

## Notes

- WAL recovery window 14d: implemented via Barman recovery window.
- Daily full physical backup: daily schedule + 14d retention is capable of
  retaining >= 8 successful full backup recovery points at steady state
  (POLICY_CAPABLE_NOT_TIME_AGED — not 8 actual historical copies after one day).
- 14 incremental/differential copies: not implemented in the selected
  Barman Cloud plugin path (barman-cloud-backup is full/physical + WAL).
- 12 monthly control copies: deferred to P8G/P9 policy closure.

These gaps are explicitly recorded and carried forward. They do not block P8B.
