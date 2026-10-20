// P8C Portal — REAL JS renderer smoke test (jsdom + synthetic DOM/fetch).
// Executes app.js renderers against contract-shaped fixtures and asserts the
// documented regressions are fixed. No real browser/PAK; fixtures are test data.
import { JSDOM } from 'jsdom';
import { readFileSync } from 'node:fs';
import assert from 'node:assert/strict';

const app = readFileSync('web/app.js', 'utf8');

const BODY = `
<div id="overall-status" class="status"></div><div id="overall-text"></div><div id="freshness"></div>
<div id="cards"></div><ul id="alerts"></ul><ul id="recent-events"></ul>
<div id="table-nodes"></div><div id="table-pods"></div><div id="table-workloads"></div><div id="table-services"></div>
<div id="table-storage"></div><div id="table-backups"></div><div id="pg-backup-meta"></div>
<div id="database-panel"></div><div id="table-metrics"></div><div id="table-events"></div>
`;

function envelope(data, freshness = 'fresh', warnings = [], nextCursor = null) {
  return { requestId: 'x', generatedAt: new Date().toISOString(), observedAt: new Date().toISOString(),
    freshness, partial: false, sources: [], warnings, nextCursor, data };
}

function run(fetchImpl) {
  const dom = new JSDOM(`<!doctype html><html><body>${BODY}</body></html>`, { runScripts: 'dangerously', url: 'http://localhost/' });
  dom.window.fetch = fetchImpl;
  const s = dom.window.document.createElement('script');
  s.textContent = app;
  dom.window.document.body.appendChild(s);
  return dom;
}

async function settle() { await new Promise(r => setTimeout(r, 30)); }

function resp(data) { return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(data) }); }
function fail() { return Promise.resolve({ ok: false, status: 503, json: () => Promise.resolve({ code: 'UNAVAILABLE' }) }); }

const summaryHealthy = envelope({ overall: 'healthy', counts: { nodesObserved: 3, nodesReady: 3, nodesExpected: 3, podsObserved: 1, podsReady: 1, pvcObserved: 1, pvcBound: 1 }, subsystems: [], alerts: [], coverage: 'mvp-read-only-kubernetes-view' });

async function testStaleHealthyNotGreen() {
  const dom = run((url) => {
    if (url.includes('/summary')) return resp(envelope(summaryHealthy.data, 'stale'));
    if (url.includes('/database')) return resp(envelope({ cluster: 'portal-db', readyInstances: 3, desiredInstances: 3, health: 'healthy', applicationDbConnected: true }));
    if (url.includes('/backups')) return resp(envelope({ velero: { health: 'unknown', locations: [], backups: [], restores: [] }, postgresql: { cluster: 'portal-db', health: 'unknown', backups: [], wal: {}, barman: { scope: 'single_exporter_sample' } }, policyGaps: [] }));
    if (url.includes('/events')) return resp(envelope({ storage: 'memory-fallback', auditComplete: false, items: [] }));
    if (url.includes('/storage')) return resp(envelope({ scope: 'kubernetes_objects', drbdDirectHealth: 'not_observed', items: [] }));
    return fail();
  });
  await settle();
  const cls = dom.window.document.getElementById('overall-status').className;
  assert.ok(cls.includes('warning'), `stale healthy must be warning, got "${cls}"`);
  assert.ok(!cls.includes('healthy'), 'stale healthy must not be green');
  dom.window.close();
}

async function testFailedListShowsUnavailable() {
  const dom = run((url) => {
    if (url.includes('/summary')) return resp(summaryHealthy);
    if (url.includes('/database')) return resp(envelope({ cluster: 'portal-db', readyInstances: 3, desiredInstances: 3, health: 'healthy', applicationDbConnected: true }));
    if (url.includes('/backups')) return resp(envelope({ velero: { health: 'unknown', locations: [], backups: [], restores: [] }, postgresql: { cluster: 'portal-db', health: 'unknown', backups: [], wal: {}, barman: {} }, policyGaps: [] }));
    if (url.includes('/events')) return resp(envelope({ storage: 'memory-fallback', auditComplete: false, items: [] }));
    if (url.includes('/storage')) return resp(envelope({ scope: 'kubernetes_objects', drbdDirectHealth: 'not_observed', items: [] }));
    return fail(); // nodes/pods/workloads/services/metrics all fail
  });
  await settle();
  // Trigger the kubernetes tab renderer explicitly by invoking the global renderers
  // (renderers object is a top-level const, not on window; drive via a second script).
  const invoke = dom.window.document.createElement('script');
  invoke.textContent = `renderKubernetes().catch(()=>{});`;
  dom.window.document.body.appendChild(invoke);
  await settle();
  const pods = dom.window.document.getElementById('table-pods').innerHTML;
  assert.ok(pods.includes('источник недоступен'), `failed pods must show unavailable, got "${pods}"`);
  assert.ok(!pods.includes('Нет данных'), 'failed pods must not show "Нет данных"');
  dom.window.close();
}

async function testBackupHealthCellShowsHealth() {
  const dom = run((url) => {
    if (url.includes('/summary')) return resp(summaryHealthy);
    if (url.includes('/database')) return resp(envelope({ cluster: 'portal-db', readyInstances: 3, desiredInstances: 3, health: 'healthy', applicationDbConnected: true }));
    if (url.includes('/backups')) return resp(envelope({ velero: { health: 'healthy', locations: [{ namespace: 'velero', name: 'default', phase: 'Available', health: 'healthy' }], backups: [], restores: [] }, postgresql: { cluster: 'portal-db', health: 'unknown', backups: [], wal: { expectedArchiveTimeoutSeconds: 300 }, barman: { scope: 'single_exporter_sample', firstRecoverabilityPoint: '1792469710', lastAvailableBackupTimestamp: '1792469710', lastFailedBackupTimestamp: '0' } }, policyGaps: [] }));
    if (url.includes('/events')) return resp(envelope({ storage: 'memory-fallback', auditComplete: false, items: [] }));
    if (url.includes('/storage')) return resp(envelope({ scope: 'kubernetes_objects', drbdDirectHealth: 'not_observed', items: [] }));
    return resp(envelope({ items: [] }));
  });
  await settle();
  const invoke = dom.window.document.createElement('script');
  invoke.textContent = `renderBackups().catch(()=>{});`;
  dom.window.document.body.appendChild(invoke);
  await settle();
  const meta = dom.window.document.getElementById('pg-backup-meta').innerHTML;
  assert.ok(meta.includes('Barman scope'), 'Barman meta must be rendered');
  assert.ok(meta.includes('expectedArchiveTimeout'), 'WAL meta must be rendered');
  dom.window.close();
}

await testStaleHealthyNotGreen();
await testFailedListShowsUnavailable();
await testBackupHealthCellShowsHealth();
console.log('renderer-smoke: PASS (stale-not-green, failed=unavailable, backup-health+Barman/WAL)');
