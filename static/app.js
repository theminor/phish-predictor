const $ = (id) => document.getElementById(id);
let state = { view: 'predict', meta: null };

const WEIGHT_ORDER = ['freq', 'trend', 'repeat_penalty', 'overdue', 'venue', 'tour', 'dow', 'season'];
const WEIGHT_INFO = {
  freq: 'Frequency — long-term play rate (dominant signal)',
  trend: 'Trend — recent momentum, plays in the last 25 shows',
  repeat_penalty: 'Repeat penalty — subtracted when played in the last 5 shows',
  overdue: 'Overdue — shows since last played vs the song’s usual gap',
  venue: 'Venue — how often played here (recurring venues, target date only)',
  tour: 'Tour — played on that tour (target date only)',
  dow: 'Day of week (target date only)',
  season: 'Quarter of the year (target date only)',
};

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

// ---- Weights tab ----

function renderWeightsForm(weights) {
  let html = '';
  for (const key of WEIGHT_ORDER) {
    if (!(key in weights)) continue;
    html += '<label class="weight-row">' +
      '<span class="weight-name"><span class="wkey">' + esc(key) + '</span>' +
      '<span class="hint">' + esc(WEIGHT_INFO[key] || '') + '</span></span>' +
      '<input class="weight-input" data-key="' + esc(key) + '" type="number" step="0.05" min="0" value="' + weights[key] + '">' +
      '</label>';
  }
  $('weights-form').innerHTML = html;
}

function collectWeights() {
  const w = {};
  for (const input of document.querySelectorAll('.weight-input')) {
    const val = parseFloat(input.value);
    if (!isNaN(val) && val >= 0) w[input.dataset.key] = val;
  }
  return w;
}

async function loadWeights() {
  const data = await api('/api/weights');
  renderWeightsForm(data.weights);
  $('w-status').textContent = data.has_overrides
    ? 'Using saved weights from weights.json' : 'Using default weights';
}

function setWStatus(msg) { $('w-status').textContent = msg; }

function refreshCurrentView() {
  if (state.view === 'predict') loadPredict();
  else if (state.view === 'backtest') loadBacktest();
}

async function saveWeights() {
  try {
    const w = collectWeights();
    await api('/api/weights', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ weights: w }) });
    setWStatus('Saved — now used by Predict, Backtest, and the CLI');
    refreshCurrentView();
  } catch (e) { setWStatus('Save failed: ' + e.message); }
}

async function resetWeights() {
  try {
    const data = await api('/api/weights', { method: 'DELETE' });
    renderWeightsForm(data.weights);
    setWStatus('Reset to defaults');
    refreshCurrentView();
  } catch (e) { setWStatus('Reset failed: ' + e.message); }
}

async function evaluateWeights() {
  $('w-loading').classList.remove('hidden');
  $('w-result').textContent = '';
  try {
    const n = parseInt($('w-n').value, 10) || 20;
    const data = await api('/api/weights/evaluate', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ weights: collectWeights(), n_shows: n, top_n: 20 }),
    });
    let bars = '';
    for (const p of data.per_show.slice().reverse()) {
      const pct = Math.round((p.hits / data.top_n) * 100);
      bars += '<div class="ev-row"><span class="ev-date">' + esc(p.date) + '</span>' +
        '<div class="ev-bar-wrap"><div class="ev-bar" style="width:' + pct + '%"></div></div>' +
        '<span class="ev-hits">' + p.hits + '</span></div>';
    }
    $('w-result').innerHTML =
      'These weights average <b>' + data.avg_hits + '</b> hits in the top ' + data.top_n +
      ' over the last ' + data.n_shows + ' shows.' +
      '<div class="ev-list">' + bars + '</div>';
  } catch (e) { setWStatus('Evaluate failed: ' + e.message); }
  finally { $('w-loading').classList.add('hidden'); }
}

// ---- view / events ----

function setView(view) {
  state.view = view;
  $('tab-predict').classList.toggle('active', view === 'predict');
  $('tab-backtest').classList.toggle('active', view === 'backtest');
  $('tab-weights').classList.toggle('active', view === 'weights');
  $('view-predict').classList.toggle('hidden', view !== 'predict');
  $('view-backtest').classList.toggle('hidden', view !== 'backtest');
  $('view-weights').classList.toggle('hidden', view !== 'weights');
  $('date-label').querySelector('.hint').textContent =
    view === 'predict' ? '(optional)' : '(defaults to last show)';
  if (view === 'predict') loadPredict();
  else if (view === 'backtest') loadBacktest();
  else loadWeights();
}

async function doRefresh() {
  clearError();
  const btn = $('refresh');
  btn.disabled = true; btn.textContent = 'Refreshing…';
  try {
    await api('/api/refresh', { method: 'POST' });
    await loadStatus(true);
    if (state.view !== 'weights') refreshCurrentView();
  } catch (e) { showError('Refresh failed: ' + e.message); }
  finally { btn.disabled = false; btn.textContent = 'Refresh data'; }
}

function init() {
  $('tab-predict').addEventListener('click', () => setView('predict'));
  $('tab-backtest').addEventListener('click', () => setView('backtest'));
  $('tab-weights').addEventListener('click', () => setView('weights'));
  $('refresh').addEventListener('click', doRefresh);
  $('w-save').addEventListener('click', saveWeights);
  $('w-reset').addEventListener('click', resetWeights);
  $('w-evaluate').addEventListener('click', evaluateWeights);
  $('top-n').addEventListener('change', () => { if (state.view !== 'weights') refreshCurrentView(); });
  $('date').addEventListener('change', () => { if (state.view !== 'weights') refreshCurrentView(); });

  loadStatus().then(() => loadPredict()).catch((e) => showError(e.message));
}

init();
