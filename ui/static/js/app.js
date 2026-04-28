/* ── BitAgent Dashboard — app.js ─────────────────────────────────────── */

const API = '';
let currentTab = 'dashboard';
let libOffset = 0, libLimit = 50, libTotal = 0, libView = 'grid';
let evOffset = 0, evLimit = 50;

/* ── Theme ────────────────────────────────────────────────────────────── */
function initTheme() {
  const saved = localStorage.getItem('bitagent-theme');
  if (saved === 'dark' || (!saved && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
    document.documentElement.setAttribute('data-theme', 'dark');
  }
}
function toggleTheme() {
  const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
  document.documentElement.setAttribute('data-theme', isDark ? 'light' : 'dark');
  localStorage.setItem('bitagent-theme', isDark ? 'light' : 'dark');
}
initTheme();

/* ── Navigation ───────────────────────────────────────────────────────── */
const TAB_META = {
  dashboard:  { title: 'Dashboard',  subtitle: 'System overview and live metrics' },
  library:    { title: 'Library',    subtitle: 'Indexed torrents and poster gallery' },
  wants:      { title: 'Wants',      subtitle: 'Operator-defined search targets' },
  evidence:   { title: 'Evidence',   subtitle: 'Webhook events from *arr applications' },
  settings:   { title: 'Settings',   subtitle: 'Configuration, auth, and integrations' },
  system:     { title: 'System',     subtitle: 'Health checks, diagnostics, and tools' },
};

function switchTab(tab) {
  currentTab = tab;
  document.querySelectorAll('.nav-item').forEach(n => n.classList.toggle('active', n.dataset.tab === tab));
  document.querySelectorAll('.page-body > .tab-panel').forEach(p => p.classList.toggle('active', p.id === `tab-${tab}`));
  const meta = TAB_META[tab] || {};
  document.getElementById('pageTitle').textContent = meta.title || tab;
  document.getElementById('pageSubtitle').textContent = meta.subtitle || '';
  document.getElementById('sidebar').classList.remove('open');
  refreshCurrentTab();
}

function refreshCurrentTab() {
  const loaders = { dashboard: loadDashboard, library: loadLibrary, wants: loadWants, evidence: loadEvidence, settings: loadSettings, system: loadSystem };
  (loaders[currentTab] || (() => {}))();
}

/* ── Utility ──────────────────────────────────────────────────────────── */
async function api(path, opts = {}) {
  try {
    const resp = await fetch(API + path, {
      headers: { 'Content-Type': 'application/json', ...opts.headers },
      ...opts,
    });
    if (!resp.ok) throw new Error(`${resp.status} ${resp.statusText}`);
    return await resp.json();
  } catch (e) {
    console.error(`API ${path}:`, e);
    return null;
  }
}

let _debounceTimers = {};
function debounce(fn, ms) {
  const key = fn.name || 'default';
  return function (...args) {
    clearTimeout(_debounceTimers[key]);
    _debounceTimers[key] = setTimeout(() => fn.apply(this, args), ms);
  };
}
const debouncedLoadLibrary = debounce(loadLibrary, 400);

function fmtNum(n) {
  if (n == null || isNaN(n)) return '--';
  return Number(n).toLocaleString();
}
function fmtBytes(b) {
  if (!b) return '--';
  const u = ['B', 'KB', 'MB', 'GB', 'TB'];
  let i = 0;
  while (b >= 1024 && i < u.length - 1) { b /= 1024; i++; }
  return `${b.toFixed(1)} ${u[i]}`;
}
function fmtTime(secs) {
  if (!secs) return '--';
  const d = Math.floor(secs / 86400), h = Math.floor((secs % 86400) / 3600), m = Math.floor((secs % 3600) / 60);
  if (d > 0) return `${d}d ${h}h`;
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}
function fmtDate(ts) {
  if (!ts) return '--';
  const d = typeof ts === 'number' ? new Date(ts * 1000) : new Date(ts);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}
function fmtAgo(ts) {
  if (!ts) return '--';
  const d = typeof ts === 'number' ? new Date(ts * 1000) : new Date(ts);
  const diff = (Date.now() - d.getTime()) / 1000;
  if (diff < 60) return 'just now';
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}
function escHtml(s) {
  const d = document.createElement('div');
  d.textContent = s || '';
  return d.innerHTML;
}
function typePill(type) {
  const map = { movie: 'pill-info', tv_show: 'pill-accent', music: 'pill-success', ebook: 'pill-warning', unknown: 'pill-neutral' };
  return `<span class="pill ${map[type] || 'pill-neutral'}">${escHtml(type || 'unknown')}</span>`;
}
function resultPill(result) {
  if (!result) return '<span class="pill pill-neutral">--</span>';
  const r = result.toLowerCase();
  if (r.includes('success') || r.includes('grab')) return `<span class="pill pill-success"><span class="pill-dot"></span>${escHtml(result)}</span>`;
  if (r.includes('fail') || r.includes('error')) return `<span class="pill pill-danger"><span class="pill-dot"></span>${escHtml(result)}</span>`;
  return `<span class="pill pill-warning"><span class="pill-dot"></span>${escHtml(result)}</span>`;
}

function toast(message, type = 'info') {
  const container = document.getElementById('toasts');
  const icons = {
    success: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
    error: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>',
    info: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>',
  };
  const el = document.createElement('div');
  el.className = `toast toast-${type}`;
  el.innerHTML = `<span class="toast-icon">${icons[type] || icons.info}</span><span>${escHtml(message)}</span>`;
  container.appendChild(el);
  setTimeout(() => { el.style.opacity = '0'; setTimeout(() => el.remove(), 300); }, 4000);
}

/* ── Dashboard ────────────────────────────────────────────────────────── */
async function loadDashboard() {
  const stats = await api('/api/stats');
  if (stats) {
    document.getElementById('statPeers').textContent = fmtNum(stats.dhtPeerCount);
    document.getElementById('statTorrents').textContent = fmtNum(stats.totalTorrents);
    document.getElementById('statEvidence').textContent = fmtNum(stats.totalEvidence);
    // Crawl rate (DHT requests per minute, sliding window)
    document.getElementById('statCrawlRate').textContent = fmtNum(stats.crawlRatePerMin);
    // Success rate + Dead Blocked (liveness pipeline; zero until the core ships
    // the new metrics — see kleos/bitmagnet feat/liveness-blocklist)
    const liveness = stats.liveness || {};
    const success = liveness.successRate || 0;
    const successEl = document.getElementById('statSuccessRate');
    if (successEl) {
      successEl.textContent = (liveness.observationsAlive + liveness.observationsSuspect) > 0
        ? `${(success * 100).toFixed(1)}%` : '—';
    }
    const successBar = document.getElementById('successBar');
    if (successBar) successBar.style.width = `${success * 100}%`;
    const blEl = document.getElementById('statBlacklist');
    if (blEl) blEl.textContent = fmtNum(liveness.blacklistSize || 0);
    const blockRateEl = document.getElementById('statBlockRate');
    if (blockRateEl) blockRateEl.textContent = fmtNum(liveness.blockRatePerMin || 0);
    document.getElementById('statUptime').textContent = fmtTime(stats.uptimeSeconds);
    document.getElementById('statLastCrawl').textContent = fmtDate(stats.lastCrawlAt);

    const chart = document.getElementById('categoryChart');
    if (stats.categoryBreakdown && stats.categoryBreakdown.length > 0) {
      // Sort largest first so the bar lengths form a clean visual descent
      const breakdown = [...stats.categoryBreakdown].sort((a, b) => b.count - a.count);
      const total = breakdown.reduce((s, c) => s + c.count, 0);
      // Bars are scaled relative to the largest slice (not the total) so even
      // small categories get a visible bar; the percent column carries the
      // share-of-total reading.
      const max = Math.max(...breakdown.map(c => c.count), 1);
      chart.innerHTML = breakdown.map(c => {
        const pct = ((c.count / total) * 100).toFixed(1);
        const barW = ((c.count / max) * 100).toFixed(1);
        const meta = categoryMeta(c.category);
        return `<div class="cat-row">
          <div class="cat-icon" style="color:${meta.color}">${meta.svg}</div>
          <div class="cat-label">${escHtml(meta.label)}</div>
          <div class="cat-bar"><div class="cat-bar-fill" style="width:${barW}%;background:${meta.color}"></div></div>
          <div class="cat-count">${fmtNum(c.count)}</div>
          <div class="cat-pct">${pct}%</div>
        </div>`;
      }).join('');
    }
  }
  loadRecentActivity();
}

// Media type → icon + display label + color. Single source of truth so the
// Library tab, Wants tab, and Dashboard chart all show consistent visuals.
function categoryMeta(cat) {
  const ICONS = {
    movie:     '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18"/><line x1="7" y1="2" x2="7" y2="22"/><line x1="17" y1="2" x2="17" y2="22"/><line x1="2" y1="12" x2="22" y2="12"/><line x1="2" y1="7" x2="7" y2="7"/><line x1="2" y1="17" x2="7" y2="17"/><line x1="17" y1="17" x2="22" y2="17"/><line x1="17" y1="7" x2="22" y2="7"/></svg>',
    tv_show:   '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="7" width="20" height="15" rx="2"/><polyline points="17 2 12 7 7 2"/></svg>',
    music:     '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg>',
    ebook:     '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 016.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z"/></svg>',
    audiobook: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 18v-6a9 9 0 0118 0v6"/><path d="M21 19a2 2 0 01-2 2h-1v-6h3v4zM3 19a2 2 0 002 2h1v-6H3v4z"/></svg>',
    software:  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>',
    game:      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="6" y1="11" x2="10" y2="11"/><line x1="8" y1="9" x2="8" y2="13"/><line x1="15" y1="12" x2="15.01" y2="12"/><line x1="18" y1="10" x2="18.01" y2="10"/><path d="M17.32 5H6.68a4 4 0 00-3.978 3.59c-.006.052-.01.101-.017.152C2.604 9.416 2 14.456 2 16a3 3 0 003 3c1 0 1.5-.5 2-1l1.414-1.414A2 2 0 019.828 16h4.344a2 2 0 011.414.586L17 18c.5.5 1 1 2 1a3 3 0 003-3c0-1.545-.604-6.584-.685-7.258-.007-.05-.011-.1-.017-.151A4 4 0 0017.32 5z"/></svg>',
    porn:      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="4.93" y1="4.93" x2="19.07" y2="19.07"/></svg>',
    unknown:   '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 015.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
  };
  const LABELS = {
    movie: 'Movie',
    tv_show: 'TV Show',
    music: 'Music',
    ebook: 'eBook',
    audiobook: 'Audiobook',
    software: 'Software',
    game: 'Game',
    porn: 'Adult',
    unknown: 'Unknown',
  };
  const COLORS = {
    movie:     'var(--color-info)',
    tv_show:   'var(--color-accent)',
    music:     'var(--color-success)',
    ebook:     'var(--color-warning)',
    audiobook: '#a78bfa',
    software:  '#94a3b8',
    game:      '#f87171',
    porn:      '#9ca3af',
    unknown:   'var(--color-fg-subtle)',
  };
  return {
    svg: ICONS[cat] || ICONS.unknown,
    label: LABELS[cat] || cat,
    color: COLORS[cat] || COLORS.unknown,
  };
}

async function loadRecentActivity() {
  const data = await api('/api/evidence?limit=10');
  const tbody = document.getElementById('activityTable');
  if (data && data.items && data.items.length > 0) {
    tbody.innerHTML = data.items.map(e =>
      `<tr>
        <td class="font-mono text-xs">${fmtAgo(e.timestamp)}</td>
        <td>${escHtml(e.source || '--')}</td>
        <td class="truncate" style="max-width:300px">${escHtml(e.torrentName || e.infoHash || '--')}</td>
        <td>${typePill(e.contentType)}</td>
        <td>${resultPill(e.result)}</td>
      </tr>`
    ).join('');
  } else {
    tbody.innerHTML = '<tr><td colspan="5" class="text-muted text-sm" style="text-align:center;padding:var(--space-6)">No recent activity. Events appear when *arr webhooks fire.</td></tr>';
  }
}

/* ── Library ──────────────────────────────────────────────────────────── */
async function loadLibrary() {
  const q = document.getElementById('libSearch').value;
  const ct = document.getElementById('libFilter').value;
  const data = await api(`/api/torrents?q=${encodeURIComponent(q)}&content_type=${ct}&limit=${libLimit}&offset=${libOffset}`);
  if (!data) return;
  libTotal = data.totalCount || 0;
  document.getElementById('libCount').textContent = fmtNum(libTotal);
  document.getElementById('libPaginationInfo').textContent = `Showing ${libOffset + 1}–${Math.min(libOffset + libLimit, libTotal)} of ${fmtNum(libTotal)}`;
  document.getElementById('libPrev').disabled = libOffset === 0;
  document.getElementById('libNext').disabled = libOffset + libLimit >= libTotal;

  const items = data.items || [];
  if (libView === 'grid') renderLibGrid(items);
  else renderLibTable(items);
}

const POSTER_ICONS = {
  movie: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18"/><line x1="7" y1="2" x2="7" y2="22"/><line x1="17" y1="2" x2="17" y2="22"/><line x1="2" y1="12" x2="22" y2="12"/><line x1="2" y1="7" x2="7" y2="7"/><line x1="2" y1="17" x2="7" y2="17"/><line x1="17" y1="7" x2="22" y2="7"/><line x1="17" y1="17" x2="22" y2="17"/></svg>',
  tv_show: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="2" y="7" width="20" height="15" rx="2" ry="2"/><polyline points="17 2 12 7 7 2"/></svg>',
  music: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg>',
  ebook: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M4 19.5A2.5 2.5 0 016.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z"/></svg>',
  software: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>',
  unknown: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 015.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
};
function renderLibGrid(items) {
  document.getElementById('libraryGrid').style.display = '';
  document.getElementById('libraryTable').style.display = 'none';
  const grid = document.getElementById('libraryGrid');
  if (items.length === 0) {
    grid.innerHTML = '<div class="empty-state" style="grid-column:1/-1"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1"><path d="M4 19.5A2.5 2.5 0 016.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z"/></svg><h3>No torrents found</h3><p>Adjust your search or wait for the DHT crawler to index content.</p></div>';
    return;
  }
  grid.innerHTML = items.map(t => {
    const title = t.release?.title || t.name || 'Unknown';
    const year = t.release?.year || '';
    const score = t.classifierScore != null ? `${(t.classifierScore * 100).toFixed(0)}%` : '--';
    const ct = t.contentType || 'unknown';
    const icon = POSTER_ICONS[ct] || POSTER_ICONS.unknown;
    const label = ct.replace('_', ' ');
    return `<div class="poster-card" onclick="openTorrentDetail('${escHtml(t.infoHash)}')">
      <div class="poster-placeholder ${ct}">${icon}<span>${label}</span></div>
      <div class="poster-info">
        <div class="poster-title">${escHtml(title)}</div>
        <div class="poster-meta">
          ${typePill(ct)}
          <span>${year}</span>
          <span>${fmtBytes(t.size)}</span>
        </div>
        <div class="poster-meta mt-2">
          <span class="pill pill-success pill-sm" style="font-size:10px">${t.seeders || 0} seeds</span>
          <span class="text-xs text-subtle">Score: ${score}</span>
        </div>
      </div>
    </div>`;
  }).join('');
}

function renderLibTable(items) {
  document.getElementById('libraryGrid').style.display = 'none';
  document.getElementById('libraryTable').style.display = '';
  const tbody = document.getElementById('libTableBody');
  if (items.length === 0) {
    tbody.innerHTML = '<tr><td colspan="6" class="text-muted text-sm" style="text-align:center;padding:var(--space-8)">No torrents found</td></tr>';
    return;
  }
  tbody.innerHTML = items.map(t => {
    const title = t.release?.title || t.name || 'Unknown';
    const score = t.classifierScore != null ? `${(t.classifierScore * 100).toFixed(0)}%` : '--';
    return `<tr style="cursor:pointer" onclick="openTorrentDetail('${escHtml(t.infoHash)}')">
      <td class="truncate" style="max-width:350px"><strong>${escHtml(title)}</strong></td>
      <td>${typePill(t.contentType)}</td>
      <td>${fmtBytes(t.size)}</td>
      <td><span class="pill pill-success" style="font-size:10px">${t.seeders || 0}</span></td>
      <td>${score}</td>
      <td class="text-xs text-subtle">${fmtAgo(t.discoveredAt)}</td>
    </tr>`;
  }).join('');
}

function setLibView(view) {
  libView = view;
  document.getElementById('viewGrid').style.color = view === 'grid' ? 'var(--color-accent)' : '';
  document.getElementById('viewList').style.color = view === 'list' ? 'var(--color-accent)' : '';
  loadLibrary();
}
function libPage(dir) { libOffset = Math.max(0, libOffset + dir * libLimit); loadLibrary(); }

async function openTorrentDetail(hash) {
  document.getElementById('torrentModal').classList.add('open');
  document.getElementById('torrentDetail').innerHTML = '<div class="skeleton" style="height:200px"></div>';
  const data = await api(`/api/torrents/${hash}`);
  if (!data) { document.getElementById('torrentDetail').innerHTML = '<p class="text-muted">Could not load details.</p>'; return; }
  const score = data.classifierScore != null ? `${(data.classifierScore * 100).toFixed(0)}%` : '--';
  document.getElementById('torrentDetail').innerHTML = `
    <div class="flex flex-col gap-4">
      <div>
        <h3 style="font-size:var(--text-lg);font-weight:var(--weight-semibold)">${escHtml(data.release?.title || data.name)}</h3>
        <div class="flex items-center gap-3 mt-2">
          ${typePill(data.contentType)}
          <span class="text-sm text-muted">${fmtBytes(data.size)}</span>
          <span class="pill pill-success"><span class="pill-dot"></span> ${data.seeders || 0} seeders</span>
        </div>
      </div>
      <div class="divider" style="margin:0"></div>
      <div class="grid-2">
        <div class="input-group"><span class="input-label">Info Hash</span><span class="font-mono text-xs">${escHtml(data.infoHash)}</span></div>
        <div class="input-group"><span class="input-label">Classifier Score</span><span>${score}</span></div>
        <div class="input-group"><span class="input-label">Quality</span><span>${escHtml(data.release?.quality || '--')}</span></div>
        <div class="input-group"><span class="input-label">Source</span><span>${escHtml(data.release?.source || '--')}</span></div>
        <div class="input-group"><span class="input-label">IMDB</span><span class="font-mono text-xs">${escHtml(data.release?.imdbId || '--')}</span></div>
        <div class="input-group"><span class="input-label">TMDB</span><span class="font-mono text-xs">${escHtml(data.release?.tmdbId || '--')}</span></div>
        <div class="input-group"><span class="input-label">Discovered</span><span>${fmtDate(data.discoveredAt)}</span></div>
        <div class="input-group"><span class="input-label">Leechers</span><span>${data.leechers || 0}</span></div>
      </div>
      ${data.magnetUri ? `<div class="input-group"><span class="input-label">Magnet URI</span><div class="code-block" style="word-break:break-all;font-size:10px">${escHtml(data.magnetUri)}</div></div>` : ''}
      ${data.files && data.files.length > 0 ? `
        <div><span class="input-label mb-2" style="display:block">Files (${data.files.length})</span>
        <div style="max-height:200px;overflow-y:auto">
          ${data.files.map(f => `<div class="flex items-center justify-between" style="padding:var(--space-1) 0;border-bottom:1px solid var(--color-border-subtle)"><span class="text-xs truncate" style="max-width:400px">${escHtml(f.path)}</span><span class="text-xs text-muted">${fmtBytes(f.size)}</span></div>`).join('')}
        </div></div>` : ''}
      ${data.evidence && data.evidence.length > 0 ? `
        <div><span class="input-label mb-2" style="display:block">Evidence (${data.evidence.length})</span>
        <table><thead><tr><th>Source</th><th>Result</th><th>Time</th></tr></thead><tbody>
          ${data.evidence.map(e => `<tr><td>${escHtml(e.source)}</td><td>${resultPill(e.result)}</td><td class="text-xs">${fmtAgo(e.timestamp)}</td></tr>`).join('')}
        </tbody></table></div>` : ''}
    </div>`;
}
function closeTorrentModal() { document.getElementById('torrentModal').classList.remove('open'); }

/* ── Wants ────────────────────────────────────────────────────────────── */
async function loadWants() {
  const data = await api('/api/wants');
  const tbody = document.getElementById('wantsTable');
  if (!data || data.length === 0) {
    tbody.innerHTML = '<tr><td colspan="7" class="text-muted text-sm" style="text-align:center;padding:var(--space-8)">No wants defined. Click "Add Want" to create search targets.</td></tr>';
    return;
  }
  tbody.innerHTML = data.map(w => {
    const statusPill = w.status === 'active' ? 'pill-success' : w.status === 'paused' ? 'pill-warning' : 'pill-neutral';
    return `<tr>
      <td><strong>${escHtml(w.title)}</strong></td>
      <td class="font-mono text-xs">${escHtml(w.query)}</td>
      <td>${typePill(w.content_type)}</td>
      <td><span class="font-mono">${w.priority}</span></td>
      <td><span class="pill ${statusPill}"><span class="pill-dot"></span>${escHtml(w.status)}</span></td>
      <td class="text-xs text-subtle">${fmtDate(w.created_at)}</td>
      <td>
        <div class="flex gap-2">
          <button class="btn btn-ghost btn-sm" onclick="toggleWantStatus(${w.id}, '${w.status}')">${w.status === 'active' ? 'Pause' : 'Resume'}</button>
          <button class="btn btn-ghost btn-sm" style="color:var(--color-danger)" onclick="deleteWant(${w.id})">Delete</button>
        </div>
      </td>
    </tr>`;
  }).join('');
}

function openWantModal() {
  document.getElementById('wantModal').classList.add('open');
  document.getElementById('wantTitle').value = '';
  document.getElementById('wantQuery').value = '';
  document.getElementById('wantNotes').value = '';
  document.getElementById('wantPriority').value = '50';
  document.getElementById('wantType').value = 'any';
}
function closeWantModal() { document.getElementById('wantModal').classList.remove('open'); }

async function saveWant() {
  const body = {
    title: document.getElementById('wantTitle').value,
    query: document.getElementById('wantQuery').value,
    content_type: document.getElementById('wantType').value,
    priority: parseInt(document.getElementById('wantPriority').value) || 50,
    notes: document.getElementById('wantNotes').value,
  };
  if (!body.title || !body.query) { toast('Title and query are required', 'error'); return; }
  const r = await api('/api/wants', { method: 'POST', body: JSON.stringify(body) });
  if (r) { toast('Want created', 'success'); closeWantModal(); loadWants(); }
  else toast('Failed to create want', 'error');
}

async function toggleWantStatus(id, current) {
  const newStatus = current === 'active' ? 'paused' : 'active';
  await api(`/api/wants/${id}`, { method: 'PUT', body: JSON.stringify({ status: newStatus }) });
  loadWants();
}
async function deleteWant(id) {
  if (!confirm('Delete this want?')) return;
  await api(`/api/wants/${id}`, { method: 'DELETE' });
  toast('Want deleted', 'success');
  loadWants();
}

/* ── Evidence ─────────────────────────────────────────────────────────── */
async function loadEvidence() {
  const data = await api(`/api/evidence?limit=${evLimit}&offset=${evOffset}`);
  const tbody = document.getElementById('evidenceTable');
  if (!data || !data.items || data.items.length === 0) {
    tbody.innerHTML = '<tr><td colspan="5" class="text-muted text-sm" style="text-align:center;padding:var(--space-8)">No evidence events. Events appear when *arr sends download webhooks.</td></tr>';
    document.getElementById('evPaginationInfo').textContent = 'Showing 0 of 0';
    return;
  }
  const total = data.totalCount || 0;
  document.getElementById('evPaginationInfo').textContent = `Showing ${evOffset + 1}–${Math.min(evOffset + evLimit, total)} of ${fmtNum(total)}`;
  document.getElementById('evPrev').disabled = evOffset === 0;
  document.getElementById('evNext').disabled = evOffset + evLimit >= total;
  tbody.innerHTML = data.items.map(e =>
    `<tr>
      <td class="font-mono text-xs">${fmtAgo(e.timestamp)}</td>
      <td>${escHtml(e.source || '--')}</td>
      <td class="truncate" style="max-width:350px">${escHtml(e.torrentName || e.infoHash || '--')}</td>
      <td>${typePill(e.contentType)}</td>
      <td>${resultPill(e.result)}</td>
    </tr>`
  ).join('');
}
function evPage(dir) { evOffset = Math.max(0, evOffset + dir * evLimit); loadEvidence(); }

/* ── Settings ─────────────────────────────────────────────────────────── */
async function loadSettings() {
  const data = await api('/api/settings');
  if (!data) return;
  const grid = document.getElementById('settingsGrid');
  const descriptions = {
    bitagent_graphql_url: 'GraphQL endpoint for the BitAgent core service',
    bitagent_metrics_url: 'Prometheus metrics endpoint',
    tmdb_api_key: 'TMDB API key for poster art in Library',
    log_level: 'Logging verbosity (debug, info, warn, error)',
    trust_npm_headers: 'Trust X-Auth-User from Nginx Proxy Manager',
    trust_forwarded_user: 'Trust X-Forwarded-User / Remote-User headers',
    sso_cookie_name: 'Cookie name for SSO session auth',
    torznab_api_key: 'API key for Torznab endpoint auth',
  };
  grid.innerHTML = Object.entries(data.fields).map(([key, f]) => {
    const isSecret = key.includes('key') || key.includes('secret');
    return `<div class="setting-item">
      <div class="setting-item-header">
        <span class="setting-key">${escHtml(key)}</span>
        ${f.overridden ? '<span class="pill pill-info setting-override-pill">overridden</span>' : ''}
      </div>
      <div class="setting-default">Default: <code>${isSecret ? '********' : escHtml(f.default)}</code></div>
      <p class="text-xs text-muted mb-4">${descriptions[key] || ''}</p>
      <div class="flex gap-2">
        <input class="input font-mono" id="setting-${key}" type="${isSecret ? 'password' : 'text'}" value="${escHtml(f.current)}" style="flex:1" placeholder="${escHtml(f.default)}">
      </div>
      <div class="setting-actions">
        <button class="btn btn-primary btn-sm" onclick="saveSetting('${key}')">Save</button>
        ${f.overridden ? `<button class="btn btn-ghost btn-sm" style="color:var(--color-danger)" onclick="resetSetting('${key}')">Reset</button>` : ''}
      </div>
    </div>`;
  }).join('');

  loadAuditLog();
  loadAuthStatus();
}

async function saveSetting(key) {
  const value = document.getElementById(`setting-${key}`).value;
  const r = await api(`/api/settings/overrides/${key}`, { method: 'PUT', body: JSON.stringify({ value }) });
  if (r) { toast(`Setting "${key}" saved`, 'success'); loadSettings(); }
  else toast(`Failed to save "${key}"`, 'error');
}
async function resetSetting(key) {
  const r = await api(`/api/settings/overrides/${key}`, { method: 'DELETE' });
  if (r) { toast(`Setting "${key}" reset to default`, 'success'); loadSettings(); }
  else toast(`Failed to reset "${key}"`, 'error');
}

async function loadAuditLog() {
  const data = await api('/api/settings/audit?limit=50');
  const container = document.getElementById('auditLog');
  if (!data || data.length === 0) {
    container.innerHTML = '<p class="text-sm text-muted" style="text-align:center;padding:var(--space-6)">No configuration changes recorded yet.</p>';
    return;
  }
  container.innerHTML = data.map(a =>
    `<div class="audit-entry">
      <div class="audit-dot"></div>
      <div style="flex:1">
        <div class="flex items-center justify-between">
          <span class="text-sm"><strong>${escHtml(a.key)}</strong> changed by <em>${escHtml(a.actor)}</em></span>
          <span class="audit-time">${fmtDate(a.at)}</span>
        </div>
        <div class="text-xs text-muted mt-2">
          ${a.old != null ? `<span style="color:var(--color-danger)">- ${escHtml(a.old.length > 40 ? a.old.slice(0, 40) + '...' : a.old)}</span><br>` : ''}
          ${a.new != null ? `<span style="color:var(--color-success)">+ ${escHtml(typeof a.new === 'string' && a.new.length > 40 ? a.new.slice(0, 40) + '...' : (a.new || '(deleted)'))}</span>` : '<span style="color:var(--color-danger)">(deleted)</span>'}
        </div>
      </div>
    </div>`
  ).join('');
}

function loadAuthStatus() {
  // These are display-only based on current config
  const updatePill = (id, active) => {
    document.getElementById(id).innerHTML = active
      ? '<span class="pill pill-success"><span class="pill-dot"></span>Active</span>'
      : '<span class="pill pill-neutral">Disabled</span>';
  };
  updatePill('authTierApi', true);
  updatePill('authTierNpm', false);
  updatePill('authTierFwd', false);
  updatePill('authTierSso', false);
}

function switchSettingsTab(tab) {
  document.querySelectorAll('#tab-settings .tab-btn').forEach(b => b.classList.toggle('active', b.dataset.stab === tab));
  document.querySelectorAll('#tab-settings .tab-panel').forEach(p => {
    if (p.id && p.id.startsWith('stab-')) p.classList.toggle('active', p.id === `stab-${tab}`);
  });
  if (tab === 'audit') loadAuditLog();
  if (tab === 'classifier') loadClassifierRules();
  if (tab === 'liveness') loadLivenessOps();
  if (tab === 'filters') loadFiltersStatus();
  if (tab === 'blocklists') loadBlockLists();
}

async function loadFiltersStatus() {
  const data = await api('/api/filters/status');
  if (!data) return;
  const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
  const drops = data.drops || {};
  set('filterNsfwCount', fmtNum(drops.nsfw_keyword || 0));
  set('filterNonLatinCount', fmtNum(drops.non_latin_script || 0));
  set('filterExtCount', fmtNum(drops.blocked_extension || 0));
  set('filterExamined', fmtNum(data.examined || 0));
  // Toggle states reflect activity (cumulative > 0). The bitagent core
  // doesn't expose env-var snapshots in /metrics, so this is the closest
  // signal we have without parsing the container's environment.
  const togglePill = (id, active) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.innerHTML = active
      ? '<span class="pill pill-success">enabled</span>'
      : '<span class="pill pill-neutral">no activity</span>';
  };
  togglePill('filterNsfwToggle', (drops.nsfw_keyword || 0) > 0);
  togglePill('filterNonLatinToggle', (drops.non_latin_script || 0) > 0);
  togglePill('filterExtToggle', (drops.blocked_extension || 0) > 0);
  // Per-extension breakdown
  const exts = data.blockedExtensions || [];
  const ext = document.getElementById('filterExtBreakdown');
  if (ext) {
    if (exts.length === 0) {
      ext.innerHTML = '<div class="empty-state" style="padding:var(--space-6)"><p class="text-sm text-muted">No extensions blocked yet.</p></div>';
    } else {
      ext.innerHTML = exts.map(e => `
        <div class="ext-cell">
          <span class="ext-name font-mono">.${escHtml(e.ext)}</span>
          <span class="ext-count font-mono">${fmtNum(e.count)}</span>
        </div>`).join('');
    }
    set('filterExtTotal', `${exts.length} extension${exts.length === 1 ? '' : 's'} on the list`);
  }
}

async function loadBlockLists() {
  // Top half — automatic lists (liveness + CSAM) read from /api/stats and /api/filters/status
  const [stats, filters] = await Promise.all([api('/api/stats'), api('/api/filters/status')]);
  const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
  if (stats) {
    const liv = stats.liveness || {};
    set('blListLivenessSize', fmtNum(liv.blacklistSize || 0));
    set('blListLivenessExcluded', fmtNum(liv.totalExcluded || 0));
    set('blListLivenessRate', fmtNum(liv.blockRatePerMin || 0));
  }
  if (filters && filters.csam) {
    set('blListCsamEntries', fmtNum(filters.csam.blocklistEntries || 0));
    set('blListCsamLookups', fmtNum(filters.csam.lookups || 0));
    set('blListCsamExports', fmtNum(filters.csam.exports || 0));
  }
  // Bottom — operator phrases
  await loadBlockPhrasesTable();
}

async function loadBlockPhrasesTable() {
  const data = await api('/api/block-phrases');
  const tbody = document.getElementById('blockPhraseTable');
  if (!tbody) return;
  if (!data || !data.items || data.items.length === 0) {
    tbody.innerHTML = `<tr><td colspan="5"><div class="empty-state" style="padding:var(--space-6)">
      <p class="text-sm text-muted">No phrases yet. Add a phrase above and it'll be filtered out of the Library tab on the next refresh.</p>
    </div></td></tr>`;
    return;
  }
  tbody.innerHTML = data.items.map(p => `
    <tr>
      <td><code class="font-mono text-sm">${escHtml(p.pattern)}</code></td>
      <td class="text-sm text-muted">${escHtml(p.note || '—')}</td>
      <td class="font-mono text-sm" style="text-align:right">${fmtNum(p.hits)}</td>
      <td class="text-xs text-subtle">${fmtAgo(p.createdAt)}</td>
      <td style="text-align:right">
        <button class="btn btn-secondary btn-sm" onclick="deleteBlockPhrase(${p.id})">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>
        </button>
      </td>
    </tr>`).join('');
}

async function addBlockPhrase() {
  const input = document.getElementById('blockPhraseInput');
  const noteInput = document.getElementById('blockPhraseNote');
  const errEl = document.getElementById('blockPhraseError');
  const pattern = (input.value || '').trim();
  const note = (noteInput.value || '').trim();
  if (!pattern) { input.focus(); return; }
  errEl.style.display = 'none';
  errEl.textContent = '';
  try {
    const resp = await fetch(API + '/api/block-phrases', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pattern, note }),
    });
    if (!resp.ok) {
      const body = await resp.json().catch(() => ({}));
      errEl.textContent = body.detail || `${resp.status} ${resp.statusText}`;
      errEl.style.display = 'block';
      return;
    }
    input.value = '';
    noteInput.value = '';
    await loadBlockPhrasesTable();
  } catch (e) {
    errEl.textContent = String(e);
    errEl.style.display = 'block';
  }
}

async function deleteBlockPhrase(id) {
  await fetch(API + '/api/block-phrases/' + id, { method: 'DELETE' });
  await loadBlockPhrasesTable();
}

async function loadLivenessOps() {
  // Reuses /api/stats since the liveness counters are emitted there.
  const stats = await api('/api/stats');
  if (!stats) return;
  const liv = stats.liveness || {};
  const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
  set('livenessObsAlive', fmtNum(liv.observationsAlive || 0));
  set('livenessObsSuspect', fmtNum(liv.observationsSuspect || 0));
  set('livenessBlacklist', fmtNum(liv.blacklistSize || 0));
  set('livenessExcluded', fmtNum(liv.totalExcluded || 0));
  const reval = liv.revalidations || {};
  const haveReval = (reval.aliveAgain + reval.stillDead) > 0;
  set('livenessRecoveryRate', haveReval ? `${(reval.recoveryRate * 100).toFixed(1)}%` : '—');
  set('livenessRevalidAlive', fmtNum(reval.aliveAgain || 0));
  set('livenessRevalidDead', fmtNum(reval.stillDead || 0));
}

function toggleKeyVisibility(id) {
  const inp = document.getElementById(id);
  inp.type = inp.type === 'password' ? 'text' : 'password';
}

async function saveTmdbKey() {
  const value = document.getElementById('tmdbKeyInput').value;
  if (!value) { toast('Enter a TMDB API key', 'error'); return; }
  const r = await api('/api/settings/overrides/tmdb_api_key', { method: 'PUT', body: JSON.stringify({ value }) });
  if (r) { toast('TMDB key saved', 'success'); document.getElementById('tmdbStatus').textContent = 'Configured'; document.getElementById('tmdbStatus').className = 'pill pill-success'; }
}

/* ── System ────────────────────────────────────────────────────────────── */
function loadSystem() { loadRawMetrics(); }

function switchSystemTab(tab) {
  document.querySelectorAll('#tab-system .tab-btn').forEach(b => b.classList.toggle('active', b.dataset.systab === tab));
  document.querySelectorAll('#tab-system > .tab-panel, #tab-system .tab-panel').forEach(p => {
    if (p.id && p.id.startsWith('systab-')) p.classList.toggle('active', p.id === `systab-${tab}`);
  });
  if (tab === 'metrics') loadRawMetrics();
}

async function runHealthChecks() {
  const container = document.getElementById('healthCheckResults');
  container.innerHTML = '<div class="skeleton" style="height:100px"></div>';
  const checks = [
    { name: 'Dashboard API', url: '/healthz' },
    { name: 'Auth Endpoint', url: '/api/me' },
    { name: 'GraphQL Proxy', url: '/api/stats' },
    { name: 'Metrics Proxy', url: '/api/metrics' },
  ];
  const results = await Promise.all(checks.map(async c => {
    const t0 = performance.now();
    try {
      const r = await fetch(c.url);
      const ms = (performance.now() - t0).toFixed(0);
      return { ...c, ok: r.ok, status: r.status, ms };
    } catch (e) {
      return { ...c, ok: false, status: 'ERR', ms: '--' };
    }
  }));
  container.innerHTML = results.map(r =>
    `<div class="flex items-center justify-between" style="padding:var(--space-3) 0;border-bottom:1px solid var(--color-border-subtle)">
      <div class="flex items-center gap-3">
        <span class="pill ${r.ok ? 'pill-success' : 'pill-danger'}"><span class="pill-dot"></span>${r.ok ? 'OK' : 'FAIL'}</span>
        <span class="text-sm">${r.name}</span>
      </div>
      <div class="flex items-center gap-3">
        <span class="font-mono text-xs">${r.status}</span>
        <span class="text-xs text-subtle">${r.ms}ms</span>
      </div>
    </div>`
  ).join('');
}

async function runTorznabTest() {
  const type = document.getElementById('tzSearchType').value;
  const q = document.getElementById('tzQuery').value;
  const result = document.getElementById('tzResult');
  result.style.display = 'block';
  result.textContent = 'Executing...';
  const data = await api(`/api/torrents?q=${encodeURIComponent(q)}&limit=10`);
  result.textContent = JSON.stringify(data, null, 2);
}

async function runGqlQuery() {
  const q = document.getElementById('gqlQuery').value;
  let vars = {};
  try { vars = JSON.parse(document.getElementById('gqlVars').value || '{}'); } catch (e) {}
  const result = document.getElementById('gqlResult');
  result.textContent = 'Executing...';
  const data = await api('/api/graphql', { method: 'POST', body: JSON.stringify({ query: q, variables: vars }) });
  result.textContent = JSON.stringify(data, null, 2);
}

async function loadRawMetrics() {
  const data = await api('/api/metrics');
  document.getElementById('rawMetrics').textContent = data ? JSON.stringify(data, null, 2) : 'Could not fetch metrics. Ensure BitAgent core is running.';
}

/* ── Notifications ────────────────────────────────────────────────────── */
let notifPanelOpen = false;
async function toggleNotifications() {
  const panel = document.getElementById('notifPanel');
  notifPanelOpen = !notifPanelOpen;
  panel.classList.toggle('open', notifPanelOpen);
  if (notifPanelOpen) await loadNotifications();
}
async function loadNotifications() {
  const data = await api('/api/notifications');
  const list = document.getElementById('notifList');
  const dot = document.getElementById('notifDot');
  if (!data || data.length === 0) {
    list.innerHTML = '<p class="text-sm text-muted" style="padding:var(--space-6);text-align:center">No notifications yet</p>';
    dot.style.display = 'none';
    return;
  }
  const unread = data.filter(n => !n.read).length;
  dot.style.display = unread > 0 ? '' : 'none';
  const icons = {
    info: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>',
    success: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
    warning: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
    error: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>',
  };
  list.innerHTML = data.map(n =>
    `<div class="notif-entry ${n.read ? '' : 'unread'}" onclick="markNotifRead(${n.id})">
      <div class="notif-entry-icon ${n.level}">${icons[n.level] || icons.info}</div>
      <div class="notif-entry-text">
        <div class="notif-entry-title">${escHtml(n.title)}</div>
        ${n.message ? `<div class="notif-entry-msg">${escHtml(n.message)}</div>` : ''}
        <div class="notif-entry-time">${fmtAgo(n.at)}</div>
      </div>
    </div>`
  ).join('');
}
async function markNotifRead(id) {
  await api(`/api/notifications/${id}/read`, { method: 'PUT' });
  loadNotifications();
}
async function markAllRead() {
  const data = await api('/api/notifications');
  if (data) {
    await Promise.all(data.filter(n => !n.read).map(n => api(`/api/notifications/${n.id}/read`, { method: 'PUT' })));
    loadNotifications();
    toast('All notifications marked as read', 'success');
  }
}
// Close notif panel when clicking outside
document.addEventListener('click', e => {
  const panel = document.getElementById('notifPanel');
  const btn = e.target.closest('.notif-btn');
  if (notifPanelOpen && !panel.contains(e.target) && !btn) {
    notifPanelOpen = false;
    panel.classList.remove('open');
  }
});

/* ── Classifier Rules ─────────────────────────────────────────────────── */
function loadClassifierRules() {
  const rules = [
    { priority: 1, name: 'Evidence Preempt', category: 'any', expression: 'evidence.hasGroundTruth(torrent.infoHash)', action: 'Use evidence label directly', description: 'Ground-truth from *arr webhooks bypasses all classification rules.' },
    { priority: 2, name: 'TV Season Pack', category: 'tv_show', expression: 'torrent.name.matches("(?i)s\\\\d{2}") && !torrent.name.matches("(?i)s\\\\d{2}e\\\\d{2}")', action: 'Classify as tv_show', description: 'Matches season packs (S01, S02) without episode numbers.' },
    { priority: 3, name: 'TV Episode', category: 'tv_show', expression: 'torrent.name.matches("(?i)s\\\\d{2}e\\\\d{2}")', action: 'Classify as tv_show', description: 'Matches standard episode naming (S01E01 pattern).' },
    { priority: 4, name: 'Movie Year', category: 'movie', expression: 'torrent.name.matches("(?i)\\\\(?(19|20)\\\\d{2}\\\\)?") && torrent.name.matches("(?i)(720p|1080p|2160p|bluray|remux)")', action: 'Classify as movie', description: 'Year + quality tag pattern typical of movie releases.' },
    { priority: 5, name: 'Music FLAC', category: 'music', expression: 'torrent.name.matches("(?i)flac") || torrent.files.any(f, f.path.endsWith(".flac"))', action: 'Classify as music', description: 'FLAC keyword or file extension detection.' },
    { priority: 6, name: 'Music MP3', category: 'music', expression: 'torrent.name.matches("(?i)mp3|320kbps|v0") || torrent.files.any(f, f.path.endsWith(".mp3"))', action: 'Classify as music', description: 'MP3 keyword or file extension detection.' },
    { priority: 7, name: 'Ebook Detection', category: 'ebook', expression: 'torrent.files.any(f, f.path.endsWith(".epub") || f.path.endsWith(".mobi") || f.path.endsWith(".pdf"))', action: 'Classify as ebook', description: 'Book file extensions in torrent file list.' },
    { priority: 8, name: 'Software ISO/EXE', category: 'software', expression: 'torrent.files.any(f, f.path.endsWith(".iso") || f.path.endsWith(".exe") || f.path.endsWith(".dmg"))', action: 'Classify as software', description: 'Installer file extensions in torrent file list.' },
    { priority: 9, name: 'Video Resolution Fallback', category: 'movie', expression: 'torrent.name.matches("(?i)(720p|1080p|2160p|4k|uhd)") && !hasLabel(torrent)', action: 'Classify as movie (low confidence)', description: 'Resolution tag without other signals defaults to movie.' },
    { priority: 10, name: 'Catch-all', category: 'unknown', expression: 'true', action: 'Classify as unknown', description: 'Default catch-all for unmatched torrents.' },
  ];
  const container = document.getElementById('classifierRulesList');
  const categoryColors = { any: 'var(--color-fg-subtle)', tv_show: 'var(--color-accent)', movie: 'var(--color-info)', music: 'var(--color-success)', ebook: 'var(--color-warning)', software: 'var(--color-danger)', unknown: 'var(--color-fg-subtle)' };
  container.innerHTML = rules.map(r =>
    `<div class="rule-card">
      <div class="rule-header">
        <div class="flex items-center gap-3">
          <div class="rule-priority">${r.priority}</div>
          <div>
            <div style="font-weight:var(--weight-semibold);font-size:var(--text-sm)">${escHtml(r.name)}</div>
            <div class="text-xs text-muted">${escHtml(r.description)}</div>
          </div>
        </div>
        <div class="flex items-center gap-2">
          ${typePill(r.category)}
          <span class="text-xs text-subtle">${escHtml(r.action)}</span>
        </div>
      </div>
      <div class="rule-expression mt-2">${escHtml(r.expression)}</div>
    </div>`
  ).join('');
}

/* ── Seed Demo Data ───────────────────────────────────────────────────── */
async function seedDemo() {
  const r = await api('/api/seed-demo', { method: 'POST' });
  if (r) toast(`Demo data seeded: ${r.wants} wants, ${r.notifications} notifications`, 'success');
  refreshCurrentTab();
  loadNotifications();
}

/* ── Init ─────────────────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  loadDashboard();
  // Auto-refresh dashboard every 30s
  setInterval(() => { if (currentTab === 'dashboard') loadDashboard(); }, 30000);
});

// Close modals on backdrop click
document.querySelectorAll('.modal-overlay').forEach(overlay => {
  overlay.addEventListener('click', e => {
    if (e.target === overlay) overlay.classList.remove('open');
  });
});

// Keyboard shortcuts
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') {
    document.querySelectorAll('.modal-overlay.open').forEach(m => m.classList.remove('open'));
    if (notifPanelOpen) { notifPanelOpen = false; document.getElementById('notifPanel').classList.remove('open'); }
  }
  // Alt+number for tab switching
  if (e.altKey && !e.ctrlKey && !e.shiftKey) {
    const tabs = ['dashboard', 'library', 'wants', 'evidence', 'settings', 'system'];
    const idx = parseInt(e.key) - 1;
    if (idx >= 0 && idx < tabs.length) { e.preventDefault(); switchTab(tabs[idx]); }
  }
  // Ctrl+K for search focus
  if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
    e.preventDefault();
    if (currentTab === 'library') document.getElementById('libSearch').focus();
    else { switchTab('library'); setTimeout(() => document.getElementById('libSearch').focus(), 100); }
  }
  // R for refresh (when not in input)
  if (e.key === 'r' && !e.ctrlKey && !e.metaKey && !['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement.tagName)) {
    refreshCurrentTab();
  }
});

// Seed demo data on first load if DB is empty
(async () => {
  const wants = await api('/api/wants');
  if (wants && wants.length <= 1) {
    await api('/api/seed-demo', { method: 'POST' });
    loadDashboard();
    loadNotifications();
  } else {
    loadNotifications();
  }
})();
