import './style.css';

const app = document.querySelector('#app');
const fmt = new Intl.NumberFormat('en', { notation: 'compact', maximumFractionDigits: 1 });
const fullFmt = new Intl.NumberFormat('en');
const dateFmt = new Intl.DateTimeFormat('en', { month: 'short', day: 'numeric', year: 'numeric' });

const state = {
  repos: [], meta: null,
  tab: 'leaderboard', query: '', language: 'All', license: 'All', activity: 'All', trend: 'All',
  sort: 'rank', page: 1, pageSize: Number(localStorage.getItem('pageSize') || 100), density: localStorage.getItem('density') || 'compact', selected: null,
};

const periods = ['daily', 'weekly', 'monthly'];
const periodLabels = { daily: 'Today', weekly: 'Week', monthly: 'Month' };

function n(v) { return Number.isFinite(v) ? v : 0; }
function daysSince(iso) { return iso ? Math.max(0, Math.floor((Date.now() - new Date(iso).getTime()) / 86400000)) : 99999; }
function repoAgeDays(r) { return r.created_at ? Math.max(1, Math.floor((Date.now() - new Date(r.created_at).getTime()) / 86400000)) : 3650; }
function pushedLabel(iso) { const d = daysSince(iso); if (d === 0) return 'today'; if (d === 1) return '1d'; if (d < 30) return `${d}d`; if (d < 365) return `${Math.round(d/30)}mo`; return `${Math.round(d/365)}y`; }
function esc(s = '') { return String(s).replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c])); }
function countBy(rows, fn) { const m = new Map(); for (const row of rows) m.set(fn(row), (m.get(fn(row)) || 0) + 1); return [...m.entries()].sort((a,b) => b[1]-a[1] || a[0].localeCompare(b[0])); }

function bestTrend(r) {
  const t = r.trending || {};
  const order = ['daily', 'weekly', 'monthly'];
  for (const p of order) if (t[p]) return { period: p, ...t[p] };
  return null;
}
function trendGain(r) {
  const t = r.trending || {};
  return Math.max(...periods.map(p => n(t[p]?.stars_gained)), 0);
}
function recencyScore(r) { return Math.exp(-daysSince(r.pushed_at) / 90); }
function hotScore(r) {
  const gain = trendGain(r);
  const periodBoost = r.trending?.daily ? 4 : r.trending?.weekly ? 2.4 : r.trending?.monthly ? 1.3 : 0;
  // Reddit/HN-inspired: recent velocity dominates; old total stars are a small tie-breaker.
  return (Math.log10(gain + 1) * 6) + periodBoost + (recencyScore(r) * 2) + (Math.log10(r.stars + 1) * 0.22) - (repoAgeDays(r) / 3650);
}
function gravityScore(r) {
  const gain = Math.max(1, trendGain(r));
  return gain / Math.pow((daysSince(r.pushed_at) + 2), 1.35);
}

function repoMatches(repo) {
  const q = state.query.trim().toLowerCase();
  if (q) {
    const hay = `${repo.full_name} ${repo.description || ''} ${repo.language || ''} ${(repo.topics || []).join(' ')}`.toLowerCase();
    if (!hay.includes(q)) return false;
  }
  if (state.language !== 'All' && (repo.language || 'Unknown') !== state.language) return false;
  if (state.license !== 'All' && (repo.license || 'NOASSERTION') !== state.license) return false;
  if (state.trend !== 'All') {
    if (state.trend === 'Any trend' && !repo.trending) return false;
    if (periods.includes(state.trend) && !repo.trending?.[state.trend]) return false;
  }
  if (state.activity === 'Pushed in 30d' && daysSince(repo.pushed_at) > 30) return false;
  if (state.activity === 'Pushed in 90d' && daysSince(repo.pushed_at) > 90) return false;
  if (state.activity === 'Pushed this year' && daysSince(repo.pushed_at) > 366) return false;
  if (state.activity === 'Archived only' && !repo.archived) return false;
  if (state.activity === 'Active only' && repo.archived) return false;
  return true;
}

function sortRepos(a, b) {
  const sort = state.tab === 'whatsup' && state.sort === 'rank' ? 'hot' : state.sort;
  switch (sort) {
    case 'hot': return hotScore(b) - hotScore(a) || b.stars - a.stars;
    case 'velocity': return trendGain(b) - trendGain(a) || hotScore(b) - hotScore(a);
    case 'gravity': return gravityScore(b) - gravityScore(a) || trendGain(b) - trendGain(a);
    case 'stars': return b.stars - a.stars || a.full_name.localeCompare(b.full_name);
    case 'forks': return b.forks - a.forks || b.stars - a.stars;
    case 'issues': return b.open_issues - a.open_issues || b.stars - a.stars;
    case 'recent': return new Date(b.pushed_at || 0) - new Date(a.pushed_at || 0) || b.stars - a.stars;
    case 'name': return a.full_name.localeCompare(b.full_name);
    case 'rank':
    default: return a.rank - b.rank;
  }
}
function filteredRepos() { return state.repos.filter(repoMatches).sort(sortRepos); }

function renderShell() {
  app.innerHTML = `
    <header class="topbar">
      <div class="brand"><span class="mark">★</span><div><b>GitHub 10k+ Star Atlas</b><small>readable repo intelligence</small></div></div>
      <nav class="tabs" role="tablist">
        ${tabButton('leaderboard','Leaderboard')}${tabButton('whatsup',"What's up")}${tabButton('method','Method')}
      </nav>
      <a class="link" href="https://github.com/trending" target="_blank" rel="noreferrer">GitHub Trending ↗</a>
    </header>
    <main class="layout">
      <aside class="sidebar" id="sidebar"></aside>
      <section class="workspace">
        <section class="controls" id="controls"></section>
        <section id="content"></section>
      </section>
    </main>`;
}
function tabButton(id, label) { return `<button class="tab ${state.tab === id ? 'active' : ''}" data-tab="${id}">${label}</button>`; }

function renderSidebar(filtered) {
  const active90 = state.repos.filter(r => daysSince(r.pushed_at) <= 90 && !r.archived).length;
  const trending = state.repos.filter(r => r.trending).length;
  const topLangs = countBy(state.repos, r => r.language || 'Unknown').slice(0, 8);
  const generated = state.meta?.generated_at ? dateFmt.format(new Date(state.meta.generated_at)) : 'Unknown';
  document.querySelector('#sidebar').innerHTML = `
    <div class="metric"><span>Repos</span><strong>${fullFmt.format(state.repos.length)}</strong><em>${fullFmt.format(filtered.length)} shown</em></div>
    <div class="metric"><span>Trend matched</span><strong>${fullFmt.format(trending)}</strong><em>from GitHub daily/week/month</em></div>
    <div class="metric"><span>Active</span><strong>${fullFmt.format(active90)}</strong><em>pushed in 90d</em></div>
    <div class="metric"><span>Snapshot</span><strong>${generated}</strong><em>GitHub Search API</em></div>
    <div class="panel small"><h3>Top languages</h3>${topLangs.map(([k,v]) => `<button class="langFilter" data-lang="${esc(k)}"><span>${esc(k)}</span><b>${v}</b></button>`).join('')}</div>
  `;
  document.querySelectorAll('.langFilter').forEach(btn => btn.addEventListener('click', () => { state.language = btn.dataset.lang; state.page = 1; render(); }));
}

function renderControls() {
  if (state.tab === 'method') { document.querySelector('#controls').innerHTML = ''; return; }
  const languages = ['All', ...countBy(state.repos, r => r.language || 'Unknown').map(([k]) => k)];
  const licenses = ['All', ...countBy(state.repos, r => r.license || 'NOASSERTION').map(([k]) => k).slice(0, 42)];
  const sortOptions = state.tab === 'whatsup'
    ? [['hot','Hot'], ['velocity','Velocity'], ['gravity','HN gravity'], ['recent','Recently pushed'], ['stars','Stars']]
    : [['rank','Rank'], ['stars','Stars'], ['recent','Recently pushed'], ['forks','Forks'], ['issues','Issues'], ['name','Name']];
  document.querySelector('#controls').innerHTML = `
    <label class="search"><span>Search</span><input id="q" value="${esc(state.query)}" placeholder="repo, owner, topic, language…" /></label>
    <label><span>Language</span><select id="language">${opts(languages, state.language)}</select></label>
    <label><span>Trend</span><select id="trend">${opts(['All','Any trend','daily','weekly','monthly'], state.trend)}</select></label>
    <label><span>Activity</span><select id="activity">${opts(['All','Active only','Pushed in 30d','Pushed in 90d','Pushed this year','Archived only'], state.activity)}</select></label>
    <label><span>License</span><select id="license">${opts(licenses, state.license)}</select></label>
    <label><span>Rows</span><select id="pageSize">${[25,50,100,250,500,'All'].map(v => `<option value="${v}" ${String(v)===String(state.pageSize) || (v==='All' && state.pageSize===99999) ? 'selected' : ''}>${v}</option>`).join('')}</select></label>
    <label><span>Sort</span><select id="sort">${sortOptions.map(([v,l]) => `<option value="${v}" ${v===state.sort?'selected':''}>${l}</option>`).join('')}</select></label>
    <button class="density" id="density">${state.density === 'compact' ? 'Compact' : 'Comfort'}</button>`;
  for (const id of ['q','language','trend','activity','license','sort','pageSize']) {
    document.querySelector(`#${id}`).addEventListener('input', e => {
      if (id === 'pageSize') {
        state.pageSize = e.target.value === 'All' ? 99999 : Number(e.target.value);
        localStorage.setItem('pageSize', String(state.pageSize));
      } else {
        state[id === 'q' ? 'query' : id] = e.target.value;
      }
      state.page = 1; render();
    });
  }
  document.querySelector('#density').addEventListener('click', () => {
    state.density = state.density === 'compact' ? 'comfort' : 'compact';
    localStorage.setItem('density', state.density); render();
  });
}
function opts(values, selected) { return values.map(v => `<option value="${esc(v)}" ${v === selected ? 'selected' : ''}>${esc(v[0]?.toUpperCase()+v.slice(1))}</option>`).join(''); }

function renderContent(filtered) {
  if (state.tab === 'method') return renderMethod();
  renderTable(filtered);
}
function renderTable(filtered) {
  const pages = Math.max(1, Math.ceil(filtered.length / state.pageSize));
  state.page = Math.min(state.page, pages);
  const start = (state.page - 1) * state.pageSize;
  const rows = filtered.slice(start, start + state.pageSize);
  const intro = state.tab === 'whatsup'
    ? `<div class="intro"><b>What's up</b><span>Recent velocity first: GitHub Trending stars gained + Reddit/HN-style time decay + push freshness. Totals are tie-breakers, not the story.</span></div>`
    : `<div class="intro"><b>Leaderboard</b><span>One-line scan view of the full 10k+ universe. Click a row for full metadata.</span></div>`;
  if (!state.selected && rows[0]) state.selected = rows[0];
  document.querySelector('#content').innerHTML = `
    ${intro}
    <div class="tableShell ${state.density}">
      <div class="tableMeta"><span>${fullFmt.format(filtered.length)} matches</span><span>page ${state.page} / ${pages}</span><div class="pager"><button id="prev" ${state.page===1?'disabled':''}>←</button><button id="next" ${state.page===pages?'disabled':''}>→</button></div></div>
      <div class="repoTable" role="table">
        <div class="thead" role="row">${headers()}</div>
        ${rows.map(rowHtml).join('') || '<div class="empty">No repositories match these filters.</div>'}
      </div>
    </div>`;
  document.querySelector('#prev')?.addEventListener('click', () => { state.page--; render(); });
  document.querySelector('#next')?.addEventListener('click', () => { state.page++; render(); });
  document.querySelectorAll('.repoRow').forEach(row => row.addEventListener('click', () => { state.selected = state.repos.find(r => r.id == row.dataset.id); render(); }));
}
function headers() {
  return ['#','Repository','Description','Stars','Δ trend','Lang','Pushed','Signal'].map(h => `<div>${h}</div>`).join('');
}
function trendPills(r) {
  const t = r.trending || {};
  const pills = periods.filter(p => t[p]).map(p => `<span class="pill trend ${p}">${periodLabels[p]} #${t[p].rank}</span>`);
  if (r.archived) pills.push('<span class="pill muted">Archived</span>');
  return pills.join('') || `<span class="mutedText">—</span>`;
}
function rowHtml(r) {
  const trend = bestTrend(r);
  const gain = trendGain(r);
  const signal = state.tab === 'whatsup' ? hotScore(r).toFixed(1) : (trend ? `${periodLabels[trend.period]} #${trend.rank}` : 'steady');
  return `<div class="repoRow ${state.selected?.id === r.id ? 'selected' : ''}" role="row" data-id="${r.id}">
    <div class="rank">${r.rank}</div>
    <div class="repoName"><a href="${r.html_url}" target="_blank" rel="noreferrer">${esc(r.full_name)}</a></div>
    <div class="descCell" title="${esc(r.description || 'No description')}">${esc(r.description || 'No description')}</div>
    <div class="num">${fmt.format(r.stars)}</div>
    <div class="num ${gain ? 'gain' : ''}">${gain ? '+' + fullFmt.format(gain) : '—'}</div>
    <div><span class="lang">${esc(r.language || 'Unknown')}</span></div>
    <div>${pushedLabel(r.pushed_at)}</div>
    <div>${trendPills(r)}</div>
  </div>`;
}
function detailsHtml(r) {
  const t = r.trending || {};
  const trendLines = periods.filter(p => t[p]).map(p => `<span>${periodLabels[p]}: #${t[p].rank}${t[p].stars_gained ? ` · +${fullFmt.format(t[p].stars_gained)} stars` : ''}</span>`).join('');
  return `<div class="detailHeader"><span class="eyebrow">Repository profile</span><h3><a href="${r.html_url}" target="_blank" rel="noreferrer">${esc(r.full_name)} ↗</a></h3></div>
    <section class="fullDescription"><b>Description</b><p>${esc(r.description || 'No description provided by GitHub.')}</p></section>
    <div class="detailGrid"><span>Hot ${hotScore(r).toFixed(2)}</span><span>Gravity ${gravityScore(r).toFixed(2)}</span><span>${fullFmt.format(r.stars)} stars</span><span>${fullFmt.format(r.forks)} forks</span><span>Created ${r.created_at ? dateFmt.format(new Date(r.created_at)) : '—'}</span><span>Pushed ${r.pushed_at ? dateFmt.format(new Date(r.pushed_at)) : '—'}</span>${trendLines || '<span>No GitHub Trending hit in current snapshot</span>'}</div>
    <div class="topics">${(r.topics || []).slice(0, 12).map(t => `<span>${esc(t)}</span>`).join('')}</div>`;
}

function renderMethod() {
  const trendCounts = state.meta?.trending_snapshot?.periods || {};
  document.querySelector('#content').innerHTML = `
    <section class="methodGrid">
      <article class="methodCard"><h2>Readable table principles applied</h2><ul>
        <li><b>One fact per row:</b> repo identity, trend signal, key metrics, freshness.</li>
        <li><b>Fixed scan columns:</b> numbers right-aligned; text truncated, not wrapped.</li>
        <li><b>Progressive disclosure:</b> row details live in the drawer, not in every row.</li>
        <li><b>Density control:</b> compact for scanning, comfort for review.</li>
        <li><b>Color is semantic:</b> trend and freshness only; no decorative gradients.</li>
      </ul></article>
      <article class="methodCard"><h2>Trend models integrated</h2><ul>
        <li><b>GitHub:</b> daily / weekly / monthly trending scrape. Current scrape sizes: daily ${trendCounts.daily || 0}, weekly ${trendCounts.weekly || 0}, monthly ${trendCounts.monthly || 0}.</li>
        <li><b>Reddit-style hot:</b> velocity dominates, recent push activity boosts, old age decays; total stars are only a tie-breaker.</li>
        <li><b>HN gravity:</b> period stars gained divided by age/freshness decay, surfacing newer fast movers.</li>
        <li><b>Longitudinal-ready:</b> the dataset keeps stable repo IDs so future snapshots can add true star deltas over time.</li>
      </ul></article>
      <article class="methodCard"><h2>Data source</h2><p>${esc(state.meta?.method || '')}</p><p>${esc(state.meta?.trending_snapshot?.note || '')}</p><a href="/data.json" download>Download full JSON snapshot</a></article>
    </section>`;
}

function bindShellEvents() {
  document.querySelectorAll('[data-tab]').forEach(btn => btn.addEventListener('click', () => {
    state.tab = btn.dataset.tab;
    state.sort = state.tab === 'whatsup' ? 'hot' : 'rank';
    state.page = 1; render();
  }));
}

function render() {
  document.body.dataset.density = state.density;
  renderShell(); bindShellEvents();
  const filtered = filteredRepos();
  renderSidebar(filtered); renderControls(); renderContent(filtered);
}

async function init() {
  app.innerHTML = '<div class="loading">Loading GitHub Star Atlas…</div>';
  const res = await fetch('/data.json', { cache: 'no-store' });
  if (!res.ok) throw new Error(`data.json returned ${res.status}`);
  const data = await res.json();
  state.meta = data;
  state.repos = data.repos || [];
  render();
}

init().catch(err => { app.innerHTML = `<div class="loading error">${esc(err.message)}</div>`; });
