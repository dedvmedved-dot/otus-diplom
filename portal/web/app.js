// ПАК Портал — frontend (native ES modules, no external framework).
// Fetches only same-origin read-only API; never stores or displays credentials.
const API = '/api/v1';

const state = { summary: null, database: null, freshness: 'unknown' };

async function getJSON(path) {
  const r = await fetch(path, { headers: { Accept: 'application/json' } });
  if (r.status === 401) { showUnauthenticated(); throw new Error('unauthenticated'); }
  if (!r.ok) throw new Error(`${path}: HTTP ${r.status}`);
  return r.json();
}

function setOverall(health, freshness) {
  const el = document.getElementById('overall-status');
  el.className = 'status ' + (health || 'unknown');
  document.getElementById('overall-text').textContent = health || '—';
  const f = document.getElementById('freshness');
  f.textContent = 'обновление: ' + (freshness || '—');
  if (freshness === 'stale') f.classList.add('stale'); else f.classList.remove('stale');
}

function showUnauthenticated() {
  document.getElementById('overall-text').textContent = 'unauthenticated';
  document.getElementById('overall-status').className = 'status critical';
}

function pill(text, kind) {
  return `<span class="pill ${kind}">${escapeHtml(text)}</span>`;
}

function escapeHtml(s) {
  return String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

function rowsToTable(elId, headers, rows) {
  const el = document.getElementById(elId);
  const head = '<thead><tr>' + headers.map(h => `<th>${h}</th>`).join('') + '</tr></thead>';
  const body = '<tbody>' + rows.map(r => `<tr>${r.map(c => `<td>${c}</td>`).join('')}</tr>`).join('') + '</tbody>';
  el.innerHTML = rows.length ? head + body : `<p class="empty">Нет данных</p>`;
}

async function renderOverview() {
  const [summary, database] = await Promise.all([
    getJSON(`${API}/summary`).catch(() => null),
    getJSON(`${API}/database`).catch(() => null),
  ]);
  state.summary = summary; state.database = database;
  setOverall(summary?.data?.overallHealth || 'unknown', summary?.freshness);

  const c = summary?.data?.counts || {};
  const db = database?.data || {};
  const cards = [
    ['Nodes', `${c.nodes ?? '—'}/3`, 'observed/expected', nodeHealth(c.nodes)],
    ['PostgreSQL', `${db.ready ?? '—'}/${db.desired ?? '—'}`, db.phase || '', db.ready === db.desired && db.ready > 0 ? 'healthy' : 'warning'],
    ['Workloads', `${c.workloads ?? '—'}`, 'deploy/sts/ds/rs/job/cronjob', 'healthy'],
    ['Storage (k8s view)', `${c.storage ?? '—'}`, 'pvc/pv/sc/snapshot', 'healthy'],
    ['Velero backup', '—', 'BSL domain', 'healthy'],
    ['PostgreSQL backup/WAL', db.walArchiving || '—', 'CNPG + Barman', db.walArchiving === 'healthy' ? 'healthy' : 'unknown'],
  ];
  document.getElementById('cards').innerHTML = cards.map(([t, v, s, kind]) =>
    `<div class="card ${kind}"><h3>${t}</h3><div class="value">${escapeHtml(v)}</div><div class="sub">${escapeHtml(s)}</div></div>`
  ).join('');

  document.getElementById('alerts').innerHTML = (summary?.data?.alerts || []).map(a => `<li>${escapeHtml(a)}</li>`).join('') || '<li class="empty">нет предупреждений</li>';
  document.getElementById('policy-gaps').innerHTML = (summary?.data?.policyGaps || []).map(g => `<li>${escapeHtml(g)}</li>`).join('') || '<li class="empty">нет</li>';
}

function nodeHealth(count) { return count >= 3 ? 'healthy' : 'warning'; }

async function renderKubernetes() {
  const [nodes, pods, workloads, services] = await Promise.all([
    getJSON(`${API}/nodes`).catch(() => null),
    getJSON(`${API}/pods`).catch(() => null),
    getJSON(`${API}/workloads`).catch(() => null),
    getJSON(`${API}/services`).catch(() => null),
  ]);
  rowsToTable('table-nodes', ['Имя', 'Ready', 'Roles', 'CPU alloc', 'Memory alloc'],
    (nodes?.data || []).map(n => [escapeHtml(n.name), pill(n.ready ? 'Ready' : 'NotReady', n.ready ? 'healthy' : 'critical'), escapeHtml((n.roles || []).join(',')), escapeHtml(n.cpuAllocatable), escapeHtml(n.memoryAllocatable)]));
  rowsToTable('table-pods', ['Namespace', 'Имя', 'Phase', 'Ready', 'Restarts', 'Node'],
    (pods?.data || []).map(p => [escapeHtml(p.namespace), escapeHtml(p.name), pill(p.phase, phaseKind(p.phase)), escapeHtml(p.ready), escapeHtml(String(p.restarts)), escapeHtml(p.nodeName)]));
  rowsToTable('table-workloads', ['Kind', 'Namespace', 'Имя', 'Ready', 'Desired'],
    (workloads?.data || []).map(w => [escapeHtml(w.kind), escapeHtml(w.namespace), escapeHtml(w.name), escapeHtml(w.ready), escapeHtml(String(w.desired))]));
  rowsToTable('table-services', ['Namespace', 'Имя', 'Type', 'Ports'],
    (services?.data || []).map(s => [escapeHtml(s.namespace), escapeHtml(s.name), escapeHtml(s.type), escapeHtml((s.ports || []).join(', '))]));
}

function phaseKind(p) { return p === 'Running' || p === 'Succeeded' ? 'healthy' : p === 'Pending' ? 'warning' : p === 'Failed' ? 'critical' : 'muted'; }

async function renderStorage() {
  const storage = await getJSON(`${API}/storage`).catch(() => null);
  rowsToTable('table-storage', ['Kind', 'Namespace', 'Имя', 'Phase', 'Capacity', 'StorageClass'],
    (storage?.data || []).map(s => [escapeHtml(s.kind), escapeHtml(s.namespace), escapeHtml(s.name), pill(s.phase, kindPill(s.phase)), escapeHtml(s.capacity), escapeHtml(s.storageClass)]));
}

function kindPill(p) {
  if (p === 'Bound' || p === 'Available') return 'healthy';
  if (p === 'Pending') return 'warning';
  if (p === 'Failed' || p === 'Released') return 'critical';
  return 'muted';
}

async function renderBackups() {
  const backups = await getJSON(`${API}/backups`).catch(() => null);
  rowsToTable('table-backups', ['Domain', 'Kind', 'Namespace', 'Имя', 'Phase', 'Available'],
    (backups?.data || []).map(b => [escapeHtml(b.domain), escapeHtml(b.kind), escapeHtml(b.namespace), escapeHtml(b.name), pill(b.phase, kindPill(b.phase)), escapeHtml(b.available ? 'да' : '—')]));
}

async function renderDatabase() {
  const db = await getJSON(`${API}/database`).catch(() => null);
  const d = db?.data || {};
  document.getElementById('database-panel').innerHTML = `
    <h2>CloudNativePG / PostgreSQL</h2>
    <table class="data-table">
      <tbody>
        <tr><th>Cluster</th><td>${escapeHtml(d.name)}</td></tr>
        <tr><th>Ready / desired</th><td>${escapeHtml(String(d.ready))} / ${escapeHtml(String(d.desired))}</td></tr>
        <tr><th>Primary</th><td>${escapeHtml(d.currentPrimary)}</td></tr>
        <tr><th>Replicas</th><td>${escapeHtml(String(d.replicas))}${d.replicaInferred ? ' (inferred)' : ''}</td></tr>
        <tr><th>Phase</th><td>${escapeHtml(d.phase)}</td></tr>
        <tr><th>WAL archiving</th><td>${escapeHtml(d.walArchiving)}</td></tr>
      </tbody>
    </table>`;
}

async function renderMetrics() {
  const m = await getJSON(`${API}/metrics`).catch(() => null);
  rowsToTable('table-metrics', ['Kind', 'Namespace', 'Имя', 'CPU', 'Memory', 'Window'],
    (m?.data || []).map(x => [escapeHtml(x.kind), escapeHtml(x.namespace), escapeHtml(x.name), escapeHtml(x.cpu), escapeHtml(x.memory), escapeHtml(x.window)]));
}

async function renderEvents() {
  const e = await getJSON(`${API}/events`).catch(() => null);
  rowsToTable('table-events', ['Ingested', 'Source', 'Severity', 'Object', 'Reason', 'Count', 'Message'],
    (e?.data || []).map(ev => [escapeHtml(ev.ingestedAt), escapeHtml(ev.source), pill(ev.severity, ev.severity === 'critical' ? 'critical' : ev.severity === 'warning' ? 'warning' : 'muted'), escapeHtml(ev.objectName), escapeHtml(ev.reasonCode), escapeHtml(String(ev.occurrenceCount)), escapeHtml(ev.message)]));
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
  const fn = renderers[name];
  if (fn) fn().catch(() => {});
}

document.querySelectorAll('.tab').forEach(t => t.addEventListener('click', () => activateTab(t.dataset.tab)));

// live refresh (15s) without resetting filters/focus
setInterval(() => {
  const active = document.querySelector('.tab.active')?.dataset?.tab;
  if (active) renderers[active]?.().catch(() => {});
}, 15000);

// initial load
renderOverview().catch(() => {});
