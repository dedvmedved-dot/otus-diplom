TASK: P8C-R1 RESUME-R3 coherent snapshot (final source closure)
INITIAL_MAIN_SHA: c3cfec621f87fb496f35099b08bc3feeb00ba309
SOURCE_SHA: 60e200795debcec5c375a48e52e7c25d44ddaa05
coherent snapshot: DONE (single snapshot per request; snapID threaded through
cursor/filter/pagination/data/envelope/nextCursor; deterministic swap test)
events filters+backend binding: DONE (preserved; round-trip + fallback 2nd page)
regression: TestCoherentSnapshotUnderSwap PASS; race -count=1 PASS
HERMES_RESULT: PASS (source package; CI release/runtime NOT_EXECUTED)
P8C: NOT_FINAL_ACCEPTED; P8D-P8G/P9: NOT_AUTHORIZED
