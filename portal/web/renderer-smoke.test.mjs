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
    if (url.includes('/backups')) return resp(envelope({ velero: { health: 'healthy', locations: [{ namespace: 'velero', name: 'default', phase: 'Available', health: 'healthy' }], backups: [], restores: [] }, postgresql: { cluster: 'portal-db', health: 'unknown', schedule: '0 30 2 * * *', expectedSchedule: '0 0 2 * * *', backups: [], wal: { state: 'healthy', continuousArchiving: { status: 'True' }, expectedArchiveTimeoutSeconds: 300 }, barman: { scope: 'single_exporter_sample', firstRecoverabilityPointTimestamp: 1792469710, lastAvailableBackupTimestamp: 1792469710, lastFailedBackupTimestamp: null } }, policyGaps: [] }));
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
  assert.ok(meta.includes('firstRecoverabilityPoint=1792469710'), `actual recoverability timestamp must render, got "${meta}"`);
  assert.ok(meta.includes('lastFailed=—'), `null lastFailed must render as "—", got "${meta}"`);
  assert.ok(meta.includes('schedule=0 30 2 * * *'), `observed schedule must take precedence, got "${meta}"`);
  assert.ok(meta.includes('WAL state=healthy'), 'WAL state must render');
  const backupTable = dom.window.document.getElementById('table-backups').innerHTML;
  assert.ok(backupTable.includes('healthy'), 'backup Health cell must show health value');
  dom.window.close();
}

await testStaleHealthyNotGreen();
await testFailedListShowsUnavailable();
await testBackupHealthCellShowsHealth();
console.log('renderer-smoke: PASS (stale-not-green, failed=unavailable, backup-health+Barman/WAL)');


async function testFreshnessAndNavigation() {
  let expired = false;
  const requests = [];
  const dom = run(url => {
    requests.push(url);
    if (url.includes('/events') && url.includes('cursor=cursor-one')) {
      if (expired) return Promise.resolve({ok:false,status:400,json:async()=>({code:'CURSOR_EXPIRED'})});
      return resp(envelope({items:[{ingestedAt:'2026-10-21T00:00:00Z',source:'portal-status',severity:'normal',reasonCode:'SECOND_PAGE',message:'fixture',occurrenceCount:1}]}));
    }
    if (url.includes('/events')) return resp(envelope({items:[]}, 'fresh', [], 'cursor-one'));
    if (url.includes('/summary')) return resp(envelope({...summaryHealthy.data,overall:'critical'},'stale'));
    if (url.includes('/database')) return resp(envelope({readyInstances:3,desiredInstances:3,health:'healthy'},'stale'));
    if (url.includes('/backups')) return resp(envelope({velero:{health:'healthy'},postgresql:{health:'healthy'}},'stale'));
    if (url.includes('/storage')) return resp(envelope({items:[{health:'healthy'}]},'stale'));
    return resp(envelope({items:[]}));
  });
  await settle();
  const document = dom.window.document;
  assert.ok(document.getElementById('overall-status').className.includes('critical'));
  assert.equal(document.querySelectorAll('#cards .healthy').length,0);
  assert.ok(!document.getElementById('alerts').textContent.includes('нет предупреждений'));
  dom.window.eval('renderEvents()'); await settle();
  document.querySelector('#table-events-navigation button:last-child').click(); await settle();
  assert.ok(requests.some(url => url.includes('/events?limit=200&cursor=cursor-one')));
  assert.ok(document.getElementById('table-events').textContent.includes('SECOND_PAGE'));
  expired = true;
  dom.window.eval('renderEvents()'); await settle();
  assert.ok(document.getElementById('table-events-navigation').textContent.includes('Страница устарела'));
  document.querySelector('#table-events-navigation button:first-of-type').click(); await settle();
  assert.equal(requests.at(-1),'/api/v1/events?limit=200');
  dom.window.close();
}
await testFreshnessAndNavigation();
console.log('renderer freshness/navigation: PASS (critical preserved, all stale cards non-green, real next/reset request, expired cursor)');

async function testUnavailablePartialAndTrustedEmpty() {
  for (const state of ['unavailable','partial','error']) {
    const dom=run(url=>{
      if(state==='error')return fail();
      const freshness=state==='unavailable'?'unavailable':'fresh';
      let data={items:[]};
      if(url.includes('/summary'))data=summaryHealthy.data;
      if(url.includes('/database'))data={readyInstances:3,desiredInstances:3,health:'healthy'};
      if(url.includes('/backups'))data={velero:{health:'healthy'},postgresql:{health:'healthy'}};
      if(url.includes('/storage'))data={items:[{health:'healthy'}]};
      const result=envelope(data,freshness);result.partial=state==='partial';return resp(result);
    });
    await settle();
    assert.equal(dom.window.document.querySelectorAll('#cards .healthy').length,0,state);
    assert.ok(!dom.window.document.getElementById('alerts').textContent.includes('нет предупреждений'),state);
    dom.window.close();
  }
  const dom=run(()=>resp(envelope({items:[]})));
  await dom.window.eval('renderKubernetes()');
  assert.ok(dom.window.document.getElementById('table-pods').textContent.includes('Нет данных'));
  assert.ok(!dom.window.document.getElementById('table-pods').textContent.includes('источник недоступен'));
  dom.window.close();
}
await testUnavailablePartialAndTrustedEmpty();
console.log('renderer availability: PASS (unavailable/partial/error overview, trusted empty distinct from failure)');
