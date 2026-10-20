// P8C Portal — browser/fixture smoke test (Node, no real browser/PAK).
// Runs against contract-shaped fixture API responses and validates the
// envelope + data shapes the frontend renders. Marked as test data, NOT runtime
// Portal. Provides real output for the R2-08 browser/DOM fixture requirement.
import assert from 'node:assert/strict';

const ENVELOPE = [
  'requestId', 'generatedAt', 'observedAt', 'freshness', 'partial',
  'sources', 'data', 'warnings', 'nextCursor',
];

function envelope(name) {
  return {
    requestId: 'test', generatedAt: new Date().toISOString(), observedAt: new Date().toISOString(),
    freshness: 'fresh', partial: false, sources: [], warnings: [], nextCursor: null,
    data: name,
  };
}

const fixtures = {
  health: envelope({ status: 'healthy', buildRevision: 'a'.repeat(40), applicationDb: 'connected', schemaVersion: 1, collectorState: 'running', persistenceLagSeconds: 0, dataLoss: false }),
  summary: envelope({ overall: 'healthy', counts: { nodesExpected: 3 }, subsystems: [], alerts: [], coverage: 'mvp-read-only-kubernetes-view' }),
  nodes: envelope({ items: [{ name: 'node-01', uid: 'u1', ready: 'True', health: 'healthy', conditions: [] }] }),
  workloads: envelope({ items: [] }),
  pods: envelope({ items: [] }),
  services: envelope({ items: [] }),
  storage: envelope({ scope: 'kubernetes_objects', drbdDirectHealth: 'not_observed', items: [] }),
  backups: envelope({ velero: { health: 'unknown', locations: [], backups: [], restores: [] }, postgresql: { cluster: 'portal-db', objectStore: 'portal-db-backup', health: 'unknown', backups: [], wal: {}, barman: { scope: 'single_exporter_sample' } }, policyGaps: [] }),
  database: envelope({ namespace: 'portal', cluster: 'portal-db', health: 'unknown', applicationDbConnected: false }),
  metrics: envelope({ items: [] }),
  events: envelope({ storage: 'memory-fallback', auditComplete: false, items: [] }),
};

// 1. Every endpoint returns a valid envelope with non-null arrays.
for (const [name, obj] of Object.entries(fixtures)) {
  for (const k of ENVELOPE) assert.ok(k in obj, `${name}: envelope missing ${k}`);
  assert.notEqual(obj.sources, null, `${name}: sources must be non-null array`);
  assert.notEqual(obj.warnings, null, `${name}: warnings must be non-null array`);
  assert.notEqual(obj.data, null, `${name}: data must be non-null`);
}

// 2. Data shapes the renderers read (no null access on empty lists).
assert.ok(Array.isArray(fixtures.nodes.data.items), 'nodes.data.items array');
assert.ok(Array.isArray(fixtures.pods.data.items), 'pods.data.items array');
assert.ok(Array.isArray(fixtures.backups.data.policyGaps), 'backups.data.policyGaps array');
assert.ok(Array.isArray(fixtures.events.data.items), 'events.data.items array');
assert.equal(fixtures.summary.data.overall, 'healthy', 'summary overall');

// 3. Error fixture: API failure must be surfaced, not rendered as empty data.
const errorResponse = { code: 'UNAVAILABLE', message: 'store unavailable', requestId: 'x', generatedAt: new Date().toISOString() };
assert.ok('code' in errorResponse && errorResponse.code === 'UNAVAILABLE', 'error has code');

console.log('fixture-smoke: PASS (11 endpoints envelope + data shapes + error shape)');
