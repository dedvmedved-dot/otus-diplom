Coherent snapshot closure (SOURCE_SHA below):

Each HTTP request now captures the snapshot EXACTLY ONCE at handler entry and
threads that single snapshot (or its stable id) through every stage:
- parseListQuery(r, allowed, endpoint, snapID): cursor snapshot-binding
  validates against the captured id, not the latest snapshot.
- paginate(items, limit, offset, ns, endpoint, snapID): nextCursor is encoded
  with the captured id.
- handleEvents: snap + snapID captured once; cursor validation, fallback data,
  paginate, encodeEventsCursor and envelope all use the captured snapshot/id.
- envelope(snap) already received the captured snapshot.

Deterministic regression: swappingProvider returns snapA on first Latest() and
snapB afterward; TestCoherentSnapshotUnderSwap proves data.items, observedAt
and nextCursor.snapshotID are ALL from snapA (t1), never mixed with snapB (t2).

Events cursor retains binding to all filters (namespace/since/severity) and
backend mode (postgresql|memory-fallback). PostgreSQL stability under
concurrent updates is governed by the store's SQL-level ORDER BY + OFFSET
pagination; the in-memory fallback paginates the captured snapshot's slice.
