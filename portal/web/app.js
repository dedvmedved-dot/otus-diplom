// ПАК Портал — frontend (native ES modules, no external framework).
// Maps the approved OpenAPI contract: envelopes carry data.items / data.overall
// / structured warnings / backup domains / events. No hardcoded "healthy".
const API = '/api/v1';

function escapeHtml(s) {
  return String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

function healthClass(h) {
  return ({healthy:'healthy', warning:'warning', critical:'critical'}[h]) || 'unknown';
}

function pill(text, kind) {
  return `<span class="pill ${kind || 'muted'}">${escapeHtml(text)}</span>`;
}

function setOverall(health, freshness) {
  const el = document.getElementById('overall-status');
  el.className = 'status ' + (healthClass(health));
  document.getElementById('overall-text').textContent = health || '—';
  const f = document.getElementById('freshness');
  f.textContent = 'обновление: ' + (freshness || '—');
  f.classList.toggle('stale', freshness === 'stale' || freshness === 'unavailable');
}

async function getJSON(path) {
  const r = await fetch(path, { headers: { Accept: 'application/json' } });
  if (r.status === 401) { document.getElementById('overall-text').textContent = 'unauthenticated'; throw new Error('unauthenticated'); }
  if (!r.ok) throw new Error(`${path}: HTTP ${r.status}`);
  return r.json();
}

function rowsToTable(elId, headers, rows) {
  const el = document.getElementById(elId);
  if (!el) return;
  const head = '<thead><tr>' + headers.map(h => `<th>${h}</th>`).join('') + '</tr></thead>';
  const body = '<tbody>' + rows.map(r => `<tr>${r.map(c => `<td>${c}</td>`).join('')}</tr>`).join('') + '</tbody>';
  el.innerHTML = rows.length ? head + body : `<p class="empty">Нет данных</p>`;
}

async function renderOverview() {
  const [summary, database, backups, events] = await Promise.all([
    getJSON(`${API}/summary`).catch(() => null),
    getJSON(`${API}/database`).catch(() => null),
    getJSON(`${API}/backups`).catch(() => null),
    getJSON(`${API}/events?limit=10`).catch(() => null),
  ]);
  const s = summary?.data || {};
  setOverall(s.overall || 'unknown', summary?.freshness);

  const c = s.counts || {};
  const db = database?.data || {};
  const b = backups?.data || {};
  const cards = [
    ['Nodes', `${c.nodesReady ?? '—'}/${c.nodesExpected ?? '—'}`, 'ready/expected', c.nodesReady === c.nodesExpected && c.nodesObserved != null ? 'healthy' : 'unknown'],
    ['PostgreSQL', `${db.readyInstances ?? '—'}/${db.desiredInstances ?? '—'}`, db.phase || '', db.readyInstances === db.desiredInstances && db.readyInstances > 0 ? 'healthy' : 'unknown'],
    ['Velero backup', b.velero?.health || '—', 'velero domain', healthClass(b.velero?.health)],
    ['PostgreSQL backup/WAL', b.postgresql?.health || '—', 'CNPG + Barman', healthClass(b.postgresql?.health)],
    ['Storage (k8s view)', `${c.pvcBound ?? '—'}/${c.pvcObserved ?? '—'}`, 'pvc bound/observed; DRBD not observed', 'unknown'],
    ['Pods', `${c.podsReady ?? '—'}/${c.podsObserved ?? '—'}`, 'ready/observed', 'unknown'],
  ];
  document.getElementById('cards').innerHTML = cards.map(([t, v, sub, kind]) =>
    `<div class="card ${kind}"><h3>${t}</h3><div class="value">${escapeHtml(v)}</div><div class="sub">${escapeHtml(sub)}</div></div>`
  ).join('');

  const alerts = s.alerts || [];
  document.getElementById('alerts').innerHTML = alerts.length
    ? alerts.map(a => `<li>[${escapeHtml(a.severity)}] ${escapeHtml(a.message)} <span class="muted">(${escapeHtml(a.source)})</span></li>`).join('')
    : (summary ? '<li class="empty">нет предупреждений</li>' : '<li class="empty warning">источник недоступен — предупреждения неизвестны</li>');

  const evItems = events?.data?.items || [];
  document.getElementById('recent-events').innerHTML = evItems.length
    ? evItems.map(e => `<li>[${escapeHtml(e.severity)}] ${escapeHtml(e.reasonCode)} — ${escapeHtml(e.objectName || '')} (${escapeHtml(e.message)})</li>`).join('')
    : (events ? '<li class="empty">событий нет</li>' : '<li class="empty warning">события недоступны</li>');
}

async function renderKubernetes() {
  const [nodes, pods, workloads, services] = await Promise.all([
    getJSON(`${API}/nodes`).catch(() => null),
    getJSON(`${API}/pods`).catch(() => null),
    getJSON(`${API}/workloads`).catch(() => null),
    getJSON(`${API}/services`).catch(() => null),
  ]);
  rowsToTable('table-nodes', ['Имя', 'Ready', 'Health', 'CPU alloc', 'Memory alloc'],
    (nodes?.data?.items || []).map(n => [escapeHtml(n.name), pill(n.ready, n.ready === 'True' ? 'healthy' : n.ready === 'False' ? 'critical' : 'muted'), pill(n.health, healthClass(n.health)), escapeHtml(n.allocatableCpuCores ?? '—'), escapeHtml(n.allocatableMemoryBytes ?? '—')]));
  rowsToTable('table-pods', ['Namespace', 'Имя', 'Phase', 'Ready', 'Restarts', 'Health'],
    (pods?.data?.items || []).map(p => [escapeHtml(p.namespace), escapeHtml(p.name), pill(p.phase, p.phase === 'Running' ? 'healthy' : p.phase === 'Failed' ? 'critical' : p.phase === 'Pending' ? 'warning' : 'muted'), escapeHtml(`${p.readyContainers}/${p.totalContainers}`), escapeHtml(String(p.restartCount)), pill(p.health, healthClass(p.health))]));
  rowsToTable('table-workloads', ['Kind', 'Namespace', 'Имя', 'Ready', 'Desired', 'Health'],
    (workloads?.data?.items || []).map(w => [escapeHtml(w.kind), escapeHtml(w.namespace), escapeHtml(w.name), escapeHtml(w.ready ?? '—'), escapeHtml(w.desired ?? '—'), pill(w.health, healthClass(w.health))]));
  rowsToTable('table-services', ['Namespace', 'Имя', 'Type', 'Ready endpoints', 'Health'],
    (services?.data?.items || []).map(sv => [escapeHtml(sv.namespace), escapeHtml(sv.name), escapeHtml(sv.type), escapeHtml(sv.readyEndpoints ?? '—'), pill(sv.health, healthClass(sv.health))]));
}

async function renderStorage() {
  const storage = await getJSON(`${API}/storage`).catch(() => null);
  const d = storage?.data || {};
  rowsToTable('table-storage', ['Kind', 'Namespace', 'Имя', 'Phase', 'ReadyToUse', 'Health'],
    (d.items || []).map(s => [escapeHtml(s.kind), escapeHtml(s.namespace ?? '—'), escapeHtml(s.name), escapeHtml(s.phase ?? '—'),
      s.kind === 'VolumeSnapshot' ? escapeHtml(s.snapshotReadyToUse ?? 'unknown') : '—',
      pill(s.health, healthClass(s.health))]));
}

async function renderBackups() {
  const backups = await getJSON(`${API}/backups`).catch(() => null);
  const b = backups?.data || {};
  const vel = b.velero || {};
  const pg = b.postgresql || {};
  const rows = [
    ...(vel.locations || []).map(x => ['velero', 'Location', x.namespace, x.name, x.phase, healthClass(x.health)]),
    ...(vel.backups || []).map(x => ['velero', 'Backup', x.namespace, x.name, x.phase, healthClass(x.health)]),
    ...(vel.restores || []).map(x => ['velero', 'Restore', x.namespace, x.name, x.phase, healthClass(x.health)]),
    ...(pg.backups || []).map(x => ['postgresql', 'Backup', x.namespace, x.name, x.phase, healthClass(x.health)]),
  ];
  rowsToTable('table-backups', ['Domain', 'Kind', 'Namespace', 'Имя', 'Phase', 'Health'],
    rows.map(r => [escapeHtml(r[0]), escapeHtml(r[1]), escapeHtml(r[2]), escapeHtml(r[3]), pill(r[4], healthClass(r[4])), pill(r[4], r[5])]));
  document.getElementById('pg-backup-meta').innerHTML =
    `schedule=${escapeHtml(pg.schedule ?? '—')} target=${escapeHtml(pg.target ?? '—')} observed=${pg.scheduledBackupObserved ? 'да' : 'нет'} lastSuccess=${escapeHtml(pg.lastSuccessfulBackupAt ?? '—')}`;
}

async function renderDatabase() {
  const db = await getJSON(`${API}/database`).catch(() => null);
  const d = db?.data || {};
  document.getElementById('database-panel').innerHTML = `
    <h2>CloudNativePG / PostgreSQL</h2>
    <table class="data-table"><tbody>
      <tr><th>Cluster</th><td>${escapeHtml(d.cluster)}</td></tr>
      <tr><th>Ready / desired</th><td>${escapeHtml(String(d.readyInstances ?? '—'))} / ${escapeHtml(String(d.desiredInstances ?? '—'))}</td></tr>
      <tr><th>Primary</th><td>${escapeHtml(d.primaryName ?? '—')}</td></tr>
      <tr><th>Replicas</th><td>${escapeHtml(String(d.replicasObserved ?? '—'))}${d.replicasInferred ? ' (inferred)' : ''}</td></tr>
      <tr><th>Phase</th><td>${escapeHtml(d.phase ?? '—')}</td></tr>
      <tr><th>Health</th><td>${pill(d.health, healthClass(d.health))}</td></tr>
      <tr><th>Application DB</th><td>${d.applicationDbConnected ? 'connected' : 'disconnected'}</td></tr>
    </tbody></table>`;
}

async function renderMetrics() {
  const m = await getJSON(`${API}/metrics`).catch(() => null);
  rowsToTable('table-metrics', ['Kind', 'Namespace', 'Имя', 'CPU (cores)', 'Memory (bytes)'],
    (m?.data?.items || []).map(x => [escapeHtml(x.kind), escapeHtml(x.namespace ?? '—'), escapeHtml(x.name), escapeHtml(x.cpuCores ?? '—'), escapeHtml(x.memoryBytes ?? '—')]));
}

async function renderEvents() {
  const e = await getJSON(`${API}/events?limit=200`).catch(() => null);
  const d = e?.data || {};
  rowsToTable('table-events', ['Ingested', 'Source', 'Severity', 'Object', 'Reason', 'Count', 'Message'],
    (d.items || []).map(ev => [escapeHtml(ev.ingestedAt), escapeHtml(ev.source), pill(ev.severity, ev.severity === 'critical' ? 'critical' : ev.severity === 'warning' ? 'warning' : 'muted'), escapeHtml(ev.objectName ?? '—'), escapeHtml(ev.reasonCode), escapeHtml(String(ev.occurrenceCount)), escapeHtml(ev.message)]));
}

const renderers = {
  overview: renderOverview,
  kubernetes: renderKubernetes,
  storage: renderStorage,
  backups: renderBackups,
  database: renderDatabase,
  metrics: renderMetrics,
  events: renderEvents,
};

function activateTab(name) {
  document.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t.dataset.tab === name));
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.toggle('active', p.id === `tab-${name}`));
  renderers[name]?.().catch(() => {});
}

document.querySelectorAll('.tab').forEach(t => t.addEventListener('click', () => activateTab(t.dataset.tab)));
setInterval(() => { const a = document.querySelector('.tab.active')?.dataset?.tab; if (a) renderers[a]?.().catch(() => {}); }, 15000);
renderOverview().catch(() => {});
