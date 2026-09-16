const $ = (id) => document.getElementById(id);
let state = { view: 'predict', meta: null };

function showError(msg) {
  const e = $('error');
  e.textContent = msg;
  e.classList.remove('hidden');
}
function clearError() { $('error').classList.add('hidden'); }

async function api(path, opts) {
  const res = await fetch(path, opts);
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.detail || ('HTTP ' + res.status));
  return body;
}

function renderStatus(meta) {
  state.meta = meta;
  $('status').textContent =
    'Data as of ' + meta.last_show_date +
    ' · ' + meta.total_shows + ' shows · ' + meta.song_count + ' songs';
}

async function loadStatus(refresh) {
  const meta = await api('/api/status' + (refresh ? '?refresh=true' : ''));
  renderStatus(meta);
  return meta;
}

function esc(s) {
  return String(s).replace(/[&<>"]/g, (c) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;',
  }[c]));
}

function renderPredict(songs, maxScore) {
  const t = $('predict-table');
  if (!songs.length) { t.innerHTML = ''; return; }
  const max = maxScore || songs[0].score || 1;
  let html = '<thead><tr>' +
    '<th class="num">#</th><th>Song</th><th class="num">Score</th>' +
    '<th></th><th class="num">Gap</th><th class="num">Plays</th>' +
    '<th class="num">Overdue</th><th class="num">Last 25</th><th class="num">In 5</th>' +
    '</tr></thead><tbody>';
  for (const s of songs) {
    const pct = Math.max(0, Math.min(100, (s.score / max) * 100));
    html += '<tr>' +
      '<td class="num">' + s.rank + '</td>' +
      '<td>' + esc(s.song) + '</td>' +
      '<td class="num">' + s.score.toFixed(3) + '</td>' +
      '<td><div class="bar-wrap"><div class="bar" style="width:' + pct.toFixed(0) + '%"></div></div></td>' +
      '<td class="num">' + s.gap + '</td>' +
      '<td class="num">' + s.times_played + '</td>' +
      '<td class="num">' + s.overdue.toFixed(1) + 'x</td>' +
      '<td class="num">' + s.trend_25 + '</td>' +
      '<td class="num">' + s.played_last_5 + '</td>' +
      '</tr>';
  }
  html += '</tbody>';
  t.innerHTML = html;
}

async function loadPredict() {
  clearError();
  $('predict-loading').classList.remove('hidden');
  try {
    const params = new URLSearchParams({ top_n: $('top-n').value });
    const d = $('date').value;
    if (d) params.set('date', d);
    const data = await api('/api/predict?' + params.toString());
    renderPredict(data.songs);
    if (data.meta) renderStatus(data.meta);
  } catch (e) { showError('Predict failed: ' + e.message); }
  finally { $('predict-loading').classList.add('hidden'); }
}

function renderBacktest(data) {
  $('backtest-summary').innerHTML =
    'Show on <b>' + esc(data.show_date) + '</b> · ' +
    '<b>' + data.hits_in_top_n + '</b> of top ' + data.top_n +
    ' predicted hit the actual setlist (' + data.actual_count + ' songs played)';
  $('bt-n').textContent = data.top_n;

  const actualSet = new Set(data.actual);
  let predHtml = '';
  for (const s of data.predicted) {
    const hit = actualSet.has(s.song);
    predHtml += '<li class="' + (hit ? 'hit' : '') + '">' + esc(s.song) +
      (hit ? ' &#10003;' : '') + '</li>';
  }
  $('bt-predicted').innerHTML = predHtml || '<li>none</li>';

  const predSet = new Set(data.predicted.map((s) => s.song));
  let actHtml = '';
  for (const s of data.actual) {
    const hit = predSet.has(s);
    actHtml += '<li class="' + (hit ? 'hit' : '') + '">' + esc(s) +
      (hit ? ' &#10003;' : '') + '</li>';
  }
  $('bt-actual').innerHTML = actHtml || '<li>none</li>';
}

async function loadBacktest() {
  clearError();
  $('backtest-loading').classList.remove('hidden');
  try {
    let d = $('date').value;
    if (!d && state.meta) d = state.meta.last_show_date;
    const params = new URLSearchParams({ top_n: $('top-n').value });
    if (d) params.set('date', d);
    const data = await api('/api/backtest?' + params.toString());
    renderBacktest(data);
  } catch (e) { showError('Backtest failed: ' + e.message); }
  finally { $('backtest-loading').classList.add('hidden'); }
}

function setView(view) {
  state.view = view;
  $('tab-predict').classList.toggle('active', view === 'predict');
  $('tab-backtest').classList.toggle('active', view === 'backtest');
  $('view-predict').classList.toggle('hidden', view !== 'predict');
  $('view-backtest').classList.toggle('hidden', view !== 'backtest');
  $('date-label').querySelector('.hint').textContent =
    view === 'predict' ? '(optional)' : '(defaults to last show)';
  if (view === 'predict') loadPredict(); else loadBacktest();
}

async function doRefresh() {
  clearError();
  const btn = $('refresh');
  btn.disabled = true; btn.textContent = 'Refreshing…';
  try {
    await api('/api/refresh', { method: 'POST' });
    await loadStatus(true);
    if (state.view === 'predict') loadPredict(); else loadBacktest();
  } catch (e) { showError('Refresh failed: ' + e.message); }
  finally { btn.disabled = false; btn.textContent = 'Refresh data'; }
}

function init() {
  $('tab-predict').addEventListener('click', () => setView('predict'));
  $('tab-backtest').addEventListener('click', () => setView('backtest'));
  $('refresh').addEventListener('click', doRefresh);
  $('top-n').addEventListener('change', () =>
    state.view === 'predict' ? loadPredict() : loadBacktest());
  $('date').addEventListener('change', () =>
    state.view === 'predict' ? loadPredict() : loadBacktest());

  loadStatus().then(() => loadPredict()).catch((e) => showError(e.message));
}

init();
