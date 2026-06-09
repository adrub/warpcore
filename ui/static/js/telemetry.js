// Polls /telemetry and /history every second/five seconds and re-renders the tables.
// Depends on fmt, fmtTime, carColor, colorMap from utils.js.

async function refreshTelemetry() {
  try {
    const data = await fetch('/telemetry').then(r => r.json());
    const entries = Object.values(data);
    if (!entries.length) return;
    // Sort by race position so leader is on top
    entries.sort((a, b) => (a.race_pos || 99) - (b.race_pos || 99));
    document.getElementById('tel-body').innerHTML = entries.map(e => {
      const col = carColor(e.name);
      return `<tr>
        <td class="td-name" style="border-left:3px solid ${col};padding-left:9px">${e.name}</td>
        <td>${fmt(e.speed, 1)}</td>
        <td>${e.gear ?? '—'}</td>
        <td>${fmt(e.rpm, 0)}</td>
        <td>${fmtTime(e.lap_time)}</td>
        <td class="td-best">${e.best_lap ? fmtTime(e.best_lap) : '—'}</td>
        <td>${e.laps ?? 0}</td>
        <td>${e.race_pos || '—'}</td>
        <td>${fmt(e.damage, 0)}</td>
      </tr>`;
    }).join('');
    pushSeries(entries);
    lastEntries = entries;
    updateDash(entries);
  } catch (_) {}
}

async function refreshHistory() {
  try {
    const data = await fetch('/history').then(r => r.json());
    if (!data.length) return;
    // Tag each entry with its original index (for deletion) before sorting fastest-first.
    // Blank/zero lap times sink to the bottom.
    document.getElementById('history-body').innerHTML = data
      .map((e, i) => ({ ...e, _idx: i }))
      .sort((a, b) => (a.lap_time || Infinity) - (b.lap_time || Infinity))
      .map(e => {
      const col = colorMap[e.name] || '#0f62fe';
      return `<tr>
        <td class="td-name" style="border-left:3px solid ${col};padding-left:9px">${e.name}</td>
        <td>${e.lap}</td>
        <td class="td-best">${fmtTime(e.lap_time)}</td>
        <td style="color:var(--muted);font-size:11px">${(e.timestamp || '').replace('T', ' ')}</td>
        <td><button type="button" class="btn-sm btn-sm-red" title="Delete entry"
                    onclick="deleteHistoryEntry(${e._idx})">✕</button></td>
      </tr>`;
    }).join('');
  } catch (_) {}
}

// Removes a single leaderboard entry, then refreshes the table
async function deleteHistoryEntry(idx) {
  try {
    await fetch('/history/delete/' + idx, { method: 'POST' });
    refreshHistory();
  } catch (_) {}
}

// Pushes each car's current best lap from the live telemetry onto the leaderboard, then refreshes
async function pushTelemetryToLeaderboard() {
  try {
    await fetch('/history/push', { method: 'POST' });
    refreshHistory();
  } catch (_) {}
}

// Clears the entire leaderboard after confirmation, then refreshes the table
async function clearHistory() {
  if (!confirm('Clear the entire leaderboard?')) return;
  try {
    await fetch('/history/clear', { method: 'POST' });
    document.getElementById('history-body').innerHTML =
      '<tr><td colspan="5" class="no-data">No laps recorded yet.</td></tr>';
  } catch (_) {}
}

// ---------------------------------------------------------------------------
// Live dashboard: a client-side rolling buffer feeds Chart.js graphs + a canvas
// track map. No backend change - we just sample the /telemetry poll over time.
// ---------------------------------------------------------------------------
const SERIES_MAX = 9000;         // keep the whole race (~37 min at 4 Hz) so graphs + map persist
const STALE_LIMIT = 10;          // stop a car's trail only after its data is constant this many ticks
const series = {};               // car name -> [{t, speed, rpm, x, y}]
const staleCount = {};           // per-car run of consecutive identical (frozen) packets
let dashStart = Date.now();
const charts = {};
let activePane = 'pane-table';
let lastEntries = [];
let raceFinished = false;        // set from /race_status; freezes the graphs/map at the finish
let prevRunning = false;

// Track race state: stop plotting when the race is over, and wipe the buffers on a fresh launch
// so two races never overlay on the same graph/map.
async function refreshStatus() {
  try {
    const st = await fetch('/race_status').then(r => r.json());
    raceFinished = !!st.finished;
    if (st.running && !prevRunning) {           // a new race just launched -> start clean
      for (const k in series) delete series[k];
      for (const k in staleCount) delete staleCount[k];
      dashStart = Date.now();
    }
    prevRunning = !!st.running;
  } catch (_) {}
}

// Prefer the real TORCS car colour (injected by the template); fall back to the palette.
function realColor(name) {
  return (window.CAR_COLOR_MAP && window.CAR_COLOR_MAP[name]) || carColor(name);
}

function showDashTab(btn) {
  document.querySelectorAll('.dash-tab').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.dash-pane').forEach(p => p.classList.remove('active'));
  btn.classList.add('active');
  document.getElementById(btn.dataset.pane).classList.add('active');
  activePane = btn.dataset.pane;
  Object.values(charts).forEach(c => c && c.resize());   // canvases sized wrong while hidden
  updateDash(lastEntries);
}

function pushSeries(entries) {
  const t = (Date.now() - dashStart) / 1000;
  entries.forEach(e => {
    const s = series[e.name] || (series[e.name] = []);
    const last = s[s.length - 1];
    const speed = e.speed || 0, rpm = e.rpm || 0, x = e.x || 0, y = e.y || 0;
    // A moving car's x/y change every tick. Only when a car's packet is IDENTICAL for many ticks
    // (it finished / stopped sending) do we stop ITS trail - so the map keeps updating for every
    // car still circulating, and one car finishing never freezes the whole dashboard.
    const same = last && last.speed === speed && last.rpm === rpm && last.x === x && last.y === y;
    if (same) {
      staleCount[e.name] = (staleCount[e.name] || 0) + 1;
      if (staleCount[e.name] > STALE_LIMIT) return;   // constant too long -> this car is done
    } else {
      staleCount[e.name] = 0;
    }
    s.push({ t, speed, rpm, pos: e.race_pos || 0, x, y });
    if (s.length > SERIES_MAX) s.shift();
  });
}

function ensureCharts() {
  if (typeof Chart === 'undefined' || charts.speed) return;
  const grid = 'rgba(255,255,255,0.06)', tick = '#7a93a8', leg = '#cdd9e5';
  const lineOpts = {
    animation: false, responsive: true, maintainAspectRatio: false,
    elements: { point: { radius: 0 } },
    scales: { x: { type: 'linear', ticks: { color: tick, maxTicksLimit: 6 }, grid: { color: grid } },
              y: { ticks: { color: tick }, grid: { color: grid } } },
    plugins: { legend: { labels: { color: leg, boxWidth: 10 } } }
  };
  const barOpts = {
    animation: false, responsive: true, maintainAspectRatio: false, indexAxis: 'y',
    scales: { x: { ticks: { color: tick }, grid: { color: grid } }, y: { ticks: { color: leg } } },
    plugins: { legend: { display: false } }
  };
  // Race position chart: same as a line chart but the y-axis is reversed (P1 on top) with whole steps.
  const posOpts = {
    animation: false, responsive: true, maintainAspectRatio: false,
    elements: { point: { radius: 0 } },
    scales: { x: { type: 'linear', ticks: { color: tick, maxTicksLimit: 6 }, grid: { color: grid } },
              y: { reverse: true, ticks: { color: tick, stepSize: 1, precision: 0 }, grid: { color: grid } } },
    plugins: { legend: { labels: { color: leg, boxWidth: 10 } } }
  };
  charts.speed  = new Chart(document.getElementById('chart-speed'),  { type: 'line', data: { datasets: [] }, options: lineOpts });
  charts.rpm    = new Chart(document.getElementById('chart-rpm'),    { type: 'line', data: { datasets: [] }, options: lineOpts });
  charts.damage = new Chart(document.getElementById('chart-damage'), { type: 'bar', data: { labels: [], datasets: [{ data: [], backgroundColor: [] }] }, options: barOpts });
  charts.pos    = new Chart(document.getElementById('chart-pos'),    { type: 'line', data: { datasets: [] }, options: posOpts });
}

// Down-sample to a fixed number of points for RENDERING so long races stay smooth, while the full
// time span (and the map's full trail) is kept in `series`.
function decimate(arr, max) {
  if (arr.length <= max) return arr;
  const out = [], step = arr.length / max;
  for (let i = 0; i < max; i++) out.push(arr[Math.floor(i * step)]);
  out.push(arr[arr.length - 1]);
  return out;
}

function updateLine(chart, key) {
  if (!chart) return;
  chart.data.datasets = Object.keys(series).map(name => ({
    label: name, borderColor: realColor(name), backgroundColor: realColor(name),
    borderWidth: 2, data: decimate(series[name], 400).map(p => ({ x: p.t, y: p[key] }))
  }));
  chart.update('none');
}

function updateBar(chart, names, values) {
  if (!chart) return;
  chart.data.labels = names;
  chart.data.datasets[0].data = values;
  chart.data.datasets[0].backgroundColor = names.map(realColor);
  chart.update('none');
}

// Top-down track map: each car's (x, y) path as a faded trail with a live dot. Auto-fits the view.
function drawMap() {
  const cv = document.getElementById('track-map');
  if (!cv) return;
  const ctx = cv.getContext('2d');
  ctx.clearRect(0, 0, cv.width, cv.height);
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity, any = false;
  Object.values(series).forEach(s => s.forEach(p => {
    if (p.x || p.y) { any = true; minX = Math.min(minX, p.x); maxX = Math.max(maxX, p.x); minY = Math.min(minY, p.y); maxY = Math.max(maxY, p.y); }
  }));
  if (!any) return;
  const pad = 34;
  const sc = Math.min((cv.width - 2 * pad) / Math.max(1, maxX - minX), (cv.height - 2 * pad) / Math.max(1, maxY - minY));
  const tx = v => pad + (v - minX) * sc;
  const ty = v => cv.height - pad - (v - minY) * sc;   // flip y so it reads like a map
  Object.keys(series).forEach(name => {
    const s = series[name], col = realColor(name);
    ctx.strokeStyle = col; ctx.globalAlpha = 0.35; ctx.lineWidth = 1.5; ctx.beginPath();
    s.forEach((p, i) => { const X = tx(p.x), Y = ty(p.y); i ? ctx.lineTo(X, Y) : ctx.moveTo(X, Y); });
    ctx.stroke(); ctx.globalAlpha = 1;
    const last = s[s.length - 1]; if (!last) return;
    ctx.fillStyle = col; ctx.beginPath(); ctx.arc(tx(last.x), ty(last.y), 6, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = '#cdd9e5'; ctx.font = '11px monospace';
    ctx.fillText(name, tx(last.x) + 9, ty(last.y) + 4);
  });
}

// Only redraw the pane that's actually visible.
function updateDash(entries) {
  ensureCharts();
  if (activePane === 'pane-graphs') {
    updateLine(charts.speed, 'speed');
    updateLine(charts.rpm, 'rpm');
    updateBar(charts.damage, entries.map(e => e.name), entries.map(e => e.damage || 0));
    updateLine(charts.pos, 'pos');
  } else if (activePane === 'pane-map') {
    drawMap();
  }
}

setInterval(refreshTelemetry, 250);   // 4 Hz - smooth graphs/map
setInterval(refreshHistory, 5000);
setInterval(refreshStatus, 500);      // race over / fresh launch
refreshStatus();
refreshTelemetry();
refreshHistory();
